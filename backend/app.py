from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_connection, test_connection

import os


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)

CORS(
    app,
    supports_credentials=True
)


# Frontend directory
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "frontend"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def row_to_dict(cursor, row):
    """
    Convert a pyodbc row into a dictionary.
    """

    columns = [
        column[0]
        for column in cursor.description
    ]

    return dict(
        zip(columns, row)
    )


def rows_to_dict(cursor, rows):
    """
    Convert multiple pyodbc rows into dictionaries.
    """

    return [
        row_to_dict(cursor, row)
        for row in rows
    ]


def get_json_data():
    """
    Safely get JSON request body.
    """

    data = request.get_json(
        silent=True
    )

    if not data:
        return {}

    return data


def normalize_role(role):
    if role is None:
        return None

    return str(role).strip().upper()


def user_exists(cursor, user_id):
    cursor.execute(
        """
        SELECT UserID
        FROM Users
        WHERE UserID = ?
        """,
        user_id
    )

    return cursor.fetchone() is not None


# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.route("/")
def home():
    """
    Main frontend entry.
    """

    index_path = os.path.join(
        FRONTEND_DIR,
        "index.html"
    )

    if os.path.exists(index_path):
        return send_from_directory(
            FRONTEND_DIR,
            "index.html"
        )

    return jsonify({
        "success": True,
        "message":
            "Hotel Restaurant Management System API is running"
    })


@app.route("/head.html")
def head_page():
    """
    Serve Head dashboard.
    """

    return send_from_directory(
        FRONTEND_DIR,
        "head.html"
    )


@app.route("/customer.html")
def customer_page():
    return send_from_directory(
        FRONTEND_DIR,
        "customer.html"
    )


@app.route("/manager.html")
def manager_page():
    return send_from_directory(
        FRONTEND_DIR,
        "manager.html"
    )


@app.route("/waiter.html")
def waiter_page():
    return send_from_directory(
        FRONTEND_DIR,
        "waiter.html"
    )


# ============================================================
# API ROOT
# ============================================================

@app.route("/api", methods=["GET"])
def api_home():

    return jsonify({
        "success": True,
        "message":
            "Hotel Restaurant Management System API is running"
    })


# ============================================================
# DATABASE TEST
# ============================================================

@app.route("/api/test-db", methods=["GET"])
def api_test_database():

    try:

        result = test_connection()

        return jsonify(result)

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Database connection failed",
            "error": str(error)
        }), 500


# ============================================================
# AUTHENTICATION - SIGNUP
# ============================================================

@app.route(
    "/api/auth/signup",
    methods=["POST"]
)
def signup():

    data = get_json_data()

    full_name = data.get("full_name")
    phone = data.get("phone")
    email = data.get("email")
    password = data.get("password")
    role = normalize_role(
        data.get("role")
    )

    if not full_name:
        return jsonify({
            "success": False,
            "message":
                "Full name is required."
        }), 400

    if not phone:
        return jsonify({
            "success": False,
            "message":
                "Phone is required."
        }), 400

    if not email:
        return jsonify({
            "success": False,
            "message":
                "Email is required."
        }), 400

    if not password:
        return jsonify({
            "success": False,
            "message":
                "Password is required."
        }), 400

    if role not in (
        "MANAGER",
        "HEAD",
        "WAITER"
    ):
        return jsonify({
            "success": False,
            "message":
                "Invalid role."
        }), 400

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        # Check phone
        cursor.execute(
            """
            SELECT UserID
            FROM Users
            WHERE Phone = ?
            """,
            phone
        )

        if cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Phone number already exists."
            }), 409

        # Check email
        cursor.execute(
            """
            SELECT UserID
            FROM Users
            WHERE Email = ?
            """,
            email
        )

        if cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Email already exists."
            }), 409

        password_hash = generate_password_hash(
            password
        )

        cursor.execute(
            """
            INSERT INTO Users
            (
                FullName,
                Phone,
                Email,
                PasswordHash,
                Role,
                IsActive
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                1
            )
            """,
            (
                full_name,
                phone,
                email,
                password_hash,
                role
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Account created successfully."
        }), 201

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Signup failed.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# AUTHENTICATION - LOGIN
# ============================================================

@app.route(
    "/api/auth/login",
    methods=["POST"]
)
def login():

    data = get_json_data()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:

        return jsonify({
            "success": False,
            "message":
                "Email and password are required."
        }), 400

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                UserID,
                FullName,
                Phone,
                Email,
                PasswordHash,
                Role,
                IsActive,
                CreatedAt
            FROM Users
            WHERE Email = ?
            """,
            email
        )

        row = cursor.fetchone()

        if not row:

            return jsonify({
                "success": False,
                "message":
                    "Invalid email or password."
            }), 401

        user = row_to_dict(
            cursor,
            row
        )

        if not user["IsActive"]:

            return jsonify({
                "success": False,
                "message":
                    "Your account is inactive."
            }), 403

        stored_password = (
            user["PasswordHash"]
        )

        password_valid = False

        # Normal hashed password
        try:

            password_valid = check_password_hash(
                stored_password,
                password
            )

        except Exception:

            password_valid = False

        # Compatibility with current seed users
        # whose PasswordHash currently contains
        # plain text "123456".
        if not password_valid:

            password_valid = (
                stored_password == password
            )

        if not password_valid:

            return jsonify({
                "success": False,
                "message":
                    "Invalid email or password."
            }), 401

        user.pop(
            "PasswordHash",
            None
        )

        return jsonify({
            "success": True,
            "message":
                "Login successful.",
            "user": user
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Login failed.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DISHES - GET ALL
# ============================================================

@app.route(
    "/api/dishes",
    methods=["GET"]
)
def get_dishes():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                DishID,
                DishName,
                Category,
                Description,
                Price,
                AvailableQuantity,
                Rating,
                ImageURL,
                IsAvailable,
                CreatedAt,
                UpdatedAt
            FROM Dishes
            ORDER BY DishID
            """
        )

        rows = cursor.fetchall()

        dishes = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(dishes),
            "dishes": dishes
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load dishes.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DISHES - GET ONE
# ============================================================

@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["GET"]
)
def get_dish(dish_id):

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                DishID,
                DishName,
                Category,
                Description,
                Price,
                AvailableQuantity,
                Rating,
                ImageURL,
                IsAvailable,
                CreatedAt,
                UpdatedAt
            FROM Dishes
            WHERE DishID = ?
            """,
            dish_id
        )

        row = cursor.fetchone()

        if not row:

            return jsonify({
                "success": False,
                "message":
                    "Dish not found."
            }), 404

        dish = row_to_dict(
            cursor,
            row
        )

        return jsonify({
            "success": True,
            "dish": dish
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load dish.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DISHES - CREATE
# ============================================================

@app.route(
    "/api/dishes",
    methods=["POST"]
)
def create_dish():

    data = get_json_data()

    dish_name = data.get("DishName")
    category = data.get("Category")
    description = data.get("Description")
    price = data.get("Price")
    quantity = data.get(
        "AvailableQuantity",
        0
    )
    rating = data.get(
        "Rating",
        0
    )
    image_url = data.get("ImageURL")
    is_available = data.get(
        "IsAvailable",
        True
    )

    if not dish_name:

        return jsonify({
            "success": False,
            "message":
                "Dish name is required."
        }), 400

    if not category:

        return jsonify({
            "success": False,
            "message":
                "Category is required."
        }), 400

    try:

        price = float(price)
        quantity = int(quantity)
        rating = float(rating)

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid price, quantity or rating."
        }), 400

    if price < 0:

        return jsonify({
            "success": False,
            "message":
                "Price cannot be negative."
        }), 400

    if quantity < 0:

        return jsonify({
            "success": False,
            "message":
                "Quantity cannot be negative."
        }), 400

    if rating < 0 or rating > 5:

        return jsonify({
            "success": False,
            "message":
                "Rating must be between 0 and 5."
        }), 400

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO Dishes
            (
                DishName,
                Category,
                Description,
                Price,
                AvailableQuantity,
                Rating,
                ImageURL,
                IsAvailable
            )
            OUTPUT INSERTED.DishID
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                dish_name,
                category,
                description,
                price,
                quantity,
                rating,
                image_url,
                1 if is_available else 0
            )
        )

        new_id = cursor.fetchone()[0]

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Dish created successfully.",
            "dish_id": new_id
        }), 201

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Unable to create dish.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DISHES - UPDATE
# ============================================================

@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["PUT"]
)
def update_dish(dish_id):

    data = get_json_data()

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT DishID
            FROM Dishes
            WHERE DishID = ?
            """,
            dish_id
        )

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Dish not found."
            }), 404

        dish_name = data.get("DishName")
        category = data.get("Category")
        description = data.get("Description")
        price = data.get("Price")
        quantity = data.get(
            "AvailableQuantity"
        )
        rating = data.get("Rating")
        image_url = data.get("ImageURL")
        is_available = data.get(
            "IsAvailable"
        )

        if dish_name is None:
            return jsonify({
                "success": False,
                "message":
                    "DishName is required."
            }), 400

        if category is None:
            return jsonify({
                "success": False,
                "message":
                    "Category is required."
            }), 400

        if price is None:
            return jsonify({
                "success": False,
                "message":
                    "Price is required."
            }), 400

        if quantity is None:
            return jsonify({
                "success": False,
                "message":
                    "AvailableQuantity is required."
            }), 400

        if rating is None:
            return jsonify({
                "success": False,
                "message":
                    "Rating is required."
            }), 400

        price = float(price)
        quantity = int(quantity)
        rating = float(rating)

        if price < 0:
            raise ValueError(
                "Price cannot be negative."
            )

        if quantity < 0:
            raise ValueError(
                "Quantity cannot be negative."
            )

        if rating < 0 or rating > 5:
            raise ValueError(
                "Rating must be between 0 and 5."
            )

        cursor.execute(
            """
            UPDATE Dishes
            SET
                DishName = ?,
                Category = ?,
                Description = ?,
                Price = ?,
                AvailableQuantity = ?,
                Rating = ?,
                ImageURL = ?,
                IsAvailable = ?,
                UpdatedAt = SYSDATETIME()
            WHERE DishID = ?
            """,
            (
                dish_name,
                category,
                description,
                price,
                quantity,
                rating,
                image_url,
                1 if is_available else 0,
                dish_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Dish updated successfully."
        })

    except ValueError as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Unable to update dish.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DISHES - DELETE
# ============================================================

@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["DELETE"]
)
def delete_dish(dish_id):

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT DishID
            FROM Dishes
            WHERE DishID = ?
            """,
            dish_id
        )

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Dish not found."
            }), 404

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM OrderDetails
            WHERE DishID = ?
            """,
            dish_id
        )

        order_count = cursor.fetchone()[0]

        if order_count > 0:

            return jsonify({
                "success": False,
                "message":
                    "This dish cannot be deleted because it is already used in an order."
            }), 409

        cursor.execute(
            """
            DELETE FROM Dishes
            WHERE DishID = ?
            """,
            dish_id
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Dish deleted successfully."
        })

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Unable to delete dish.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# HEAD DASHBOARD SUMMARY
# ============================================================

@app.route(
    "/api/head/overview",
    methods=["GET"]
)
def head_overview():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*)
                 FROM Dishes) AS TotalDishes,

                (SELECT COUNT(*)
                 FROM Dishes
                 WHERE IsAvailable = 1)
                 AS AvailableDishes,

                (SELECT COUNT(*)
                 FROM Orders)
                 AS TotalOrders,

                (SELECT COUNT(DISTINCT CustomerID)
                 FROM Orders)
                 AS TotalCustomers,

                (SELECT COUNT(*)
                 FROM Users)
                 AS TotalUsers
            """
        )

        row = cursor.fetchone()

        summary = row_to_dict(
            cursor,
            row
        )

        return jsonify({
            "success": True,
            "overview": summary
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load Head dashboard summary.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ORDERS - GET ALL
# ============================================================

@app.route(
    "/api/orders",
    methods=["GET"]
)
def get_orders():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                o.OrderID,
                o.CustomerID,
                c.CustomerName,
                c.Phone AS MobileNumber,
                o.TableNumber,
                o.TotalAmount,
                o.Status,
                o.OrderDate
            FROM Orders o
            INNER JOIN Customers c
                ON o.CustomerID = c.CustomerID
            ORDER BY
                o.OrderID DESC
            """
        )

        rows = cursor.fetchall()

        orders = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(orders),
            "orders": orders
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load orders.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ORDER DETAILS
# ============================================================

@app.route(
    "/api/orders/<int:order_id>",
    methods=["GET"]
)
def get_order(order_id):

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        # Order
        cursor.execute(
            """
            SELECT
                o.OrderID,
                o.CustomerID,
                c.CustomerName,
                c.Phone AS MobileNumber,
                o.TableNumber,
                o.TotalAmount,
                o.Status,
                o.OrderDate
            FROM Orders o
            INNER JOIN Customers c
                ON o.CustomerID = c.CustomerID
            WHERE o.OrderID = ?
            """,
            order_id
        )

        order_row = cursor.fetchone()

        if not order_row:

            return jsonify({
                "success": False,
                "message":
                    "Order not found."
            }), 404

        order = row_to_dict(
            cursor,
            order_row
        )

        # Details
        cursor.execute(
            """
            SELECT
                od.OrderDetailID,
                od.OrderID,
                od.DishID,
                d.DishName,
                od.Quantity,
                od.UnitPrice,
                od.SubTotal
            FROM OrderDetails od
            INNER JOIN Dishes d
                ON od.DishID = d.DishID
            WHERE od.OrderID = ?
            ORDER BY od.OrderDetailID
            """,
            order_id
        )

        detail_rows = cursor.fetchall()

        details = rows_to_dict(
            cursor,
            detail_rows
        )

        return jsonify({
            "success": True,
            "order": order,
            "details": details
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load order.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ORDER STATUS UPDATE
# ============================================================

@app.route(
    "/api/orders/<int:order_id>/status",
    methods=["PUT"]
)
def update_order_status(order_id):

    data = get_json_data()

    new_status = normalize_role(
        data.get("status")
    )

    allowed_statuses = {
        "PENDING",
        "CONFIRMED",
        "PREPARING",
        "READY",
        "COMPLETED",
        "CANCELLED"
    }

    if new_status not in allowed_statuses:

        return jsonify({
            "success": False,
            "message":
                "Invalid order status."
        }), 400

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT Status
            FROM Orders
            WHERE OrderID = ?
            """,
            order_id
        )

        row = cursor.fetchone()

        if not row:

            return jsonify({
                "success": False,
                "message":
                    "Order not found."
            }), 404

        old_status = row[0]

        cursor.execute(
            """
            UPDATE Orders
            SET Status = ?
            WHERE OrderID = ?
            """,
            (
                new_status,
                order_id
            )
        )

        cursor.execute(
            """
            INSERT INTO OrderStatusHistory
            (
                OrderID,
                OldStatus,
                NewStatus,
                ChangedBy
            )
            VALUES
            (
                ?,
                ?,
                ?,
                NULL
            )
            """,
            (
                order_id,
                old_status,
                new_status
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Order status updated successfully."
        })

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Unable to update order status.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMERS - GET SUMMARY
# ============================================================

@app.route(
    "/api/customers",
    methods=["GET"]
)
def get_customers():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                c.CustomerID,
                c.CustomerName,
                c.Phone,
                COUNT(o.OrderID) AS TotalOrders,
                ISNULL(
                    SUM(o.TotalAmount),
                    0
                ) AS TotalSpent,
                c.CreatedAt
            FROM Customers c
            LEFT JOIN Orders o
                ON c.CustomerID = o.CustomerID
            GROUP BY
                c.CustomerID,
                c.CustomerName,
                c.Phone,
                c.CreatedAt
            ORDER BY
                c.CustomerID
            """
        )

        rows = cursor.fetchall()

        customers = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(customers),
            "customers": customers
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load customers.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# BOOKINGS - GET ALL
# ============================================================

@app.route(
    "/api/bookings",
    methods=["GET"]
)
def get_bookings():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                b.BookingID,
                b.CustomerID,
                c.CustomerName,
                c.Phone AS MobileNumber,
                b.BookingDate,
                b.BookingTime,
                b.NumberOfGuests,
                b.TableNumber,
                b.Status,
                b.CreatedAt
            FROM Bookings b
            INNER JOIN Customers c
                ON b.CustomerID = c.CustomerID
            ORDER BY
                b.BookingID DESC
            """
        )

        rows = cursor.fetchall()

        bookings = rows_to_dict(
            cursor,
            rows
        )

        for booking in bookings:

            if booking.get("BookingDate") is not None:
                booking["BookingDate"] = str(
                    booking["BookingDate"]
                )

            if booking.get("BookingTime") is not None:
                booking["BookingTime"] = str(
                    booking["BookingTime"]
                )

            if booking.get("CreatedAt") is not None:
                booking["CreatedAt"] = str(
                    booking["CreatedAt"]
                )

        return jsonify({
            "success": True,
            "count": len(bookings),
            "bookings": bookings
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load bookings.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()
# ============================================================
# BOOKING STATUS UPDATE
# ============================================================

@app.route(
    "/api/bookings/<int:booking_id>/status",
    methods=["PUT"]
)
def update_booking_status(booking_id):

    data = get_json_data()

    status = normalize_role(
        data.get("status")
    )

    allowed_statuses = {
        "PENDING",
        "CONFIRMED",
        "COMPLETED",
        "CANCELLED"
    }

    if status not in allowed_statuses:

        return jsonify({
            "success": False,
            "message":
                "Invalid booking status."
        }), 400

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT BookingID
            FROM Bookings
            WHERE BookingID = ?
            """,
            booking_id
        )

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "Booking not found."
            }), 404

        cursor.execute(
            """
            UPDATE Bookings
            SET Status = ?
            WHERE BookingID = ?
            """,
            (
                status,
                booking_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Booking status updated successfully."
        })

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Unable to update booking status.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# USERS - GET ALL
# ============================================================

@app.route(
    "/api/users",
    methods=["GET"]
)
def get_users():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                UserID,
                FullName,
                Phone,
                Email,
                Role,
                IsActive,
                CreatedAt
            FROM Users
            ORDER BY UserID
            """
        )

        rows = cursor.fetchall()

        users = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(users),
            "users": users
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load users.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# USER - GET ONE
# ============================================================

@app.route(
    "/api/users/<int:user_id>",
    methods=["GET"]
)
def get_user(user_id):

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                UserID,
                FullName,
                Phone,
                Email,
                Role,
                IsActive,
                CreatedAt
            FROM Users
            WHERE UserID = ?
            """,
            user_id
        )

        row = cursor.fetchone()

        if not row:

            return jsonify({
                "success": False,
                "message":
                    "User not found."
            }), 404

        user = row_to_dict(
            cursor,
            row
        )

        return jsonify({
            "success": True,
            "user": user
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load user.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# USERS - UPDATE ACTIVE STATUS
# ============================================================

@app.route(
    "/api/users/<int:user_id>/status",
    methods=["PUT"]
)
def update_user_status(user_id):

    data = get_json_data()

    is_active = data.get(
        "is_active"
    )

    if is_active is None:

        return jsonify({
            "success": False,
            "message":
                "is_active is required."
        }), 400

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT UserID
            FROM Users
            WHERE UserID = ?
            """,
            user_id
        )

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message":
                    "User not found."
            }), 404

        cursor.execute(
            """
            UPDATE Users
            SET IsActive = ?
            WHERE UserID = ?
            """,
            (
                1 if is_active else 0,
                user_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "User status updated successfully."
        })

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message":
                "Unable to update user status.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ORDER DETAILS - GET
# ============================================================

@app.route(
    "/api/order-details",
    methods=["GET"]
)
def get_order_details():

    order_id = request.args.get(
        "order_id"
    )

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        if order_id:

            cursor.execute(
                """
                SELECT
                    od.OrderDetailID,
                    od.OrderID,
                    od.DishID,
                    d.DishName,
                    od.Quantity,
                    od.UnitPrice,
                    od.SubTotal
                FROM OrderDetails od
                INNER JOIN Dishes d
                    ON od.DishID = d.DishID
                WHERE od.OrderID = ?
                ORDER BY od.OrderDetailID
                """,
                int(order_id)
            )

        else:

            cursor.execute(
                """
                SELECT
                    od.OrderDetailID,
                    od.OrderID,
                    od.DishID,
                    d.DishName,
                    od.Quantity,
                    od.UnitPrice,
                    od.SubTotal
                FROM OrderDetails od
                INNER JOIN Dishes d
                    ON od.DishID = d.DishID
                ORDER BY
                    od.OrderDetailID DESC
                """
            )

        rows = cursor.fetchall()

        details = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(details),
            "order_details": details
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load order details.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ORDER STATUS HISTORY
# ============================================================

@app.route(
    "/api/order-status-history",
    methods=["GET"]
)
def get_order_status_history():

    order_id = request.args.get(
        "order_id"
    )

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        if order_id:

            cursor.execute(
                """
                SELECT
                    h.HistoryID,
                    h.OrderID,
                    h.OldStatus,
                    h.NewStatus,
                    h.ChangedBy,
                    u.FullName AS ChangedByName,
                    h.ChangedAt
                FROM OrderStatusHistory h
                LEFT JOIN Users u
                    ON h.ChangedBy = u.UserID
                WHERE h.OrderID = ?
                ORDER BY h.HistoryID
                """,
                int(order_id)
            )

        else:

            cursor.execute(
                """
                SELECT
                    h.HistoryID,
                    h.OrderID,
                    h.OldStatus,
                    h.NewStatus,
                    h.ChangedBy,
                    u.FullName AS ChangedByName,
                    h.ChangedAt
                FROM OrderStatusHistory h
                LEFT JOIN Users u
                    ON h.ChangedBy = u.UserID
                ORDER BY h.HistoryID DESC
                """
            )

        rows = cursor.fetchall()

        history = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load order status history.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# PAYMENTS
# ============================================================

@app.route(
    "/api/payments",
    methods=["GET"]
)
def get_payments():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                p.PaymentID,
                p.OrderID,
                p.Amount,
                p.PaymentMethod,
                p.PaymentStatus,
                p.TransactionReference,
                p.PaidAt,
                p.CreatedAt
            FROM Payments p
            ORDER BY p.PaymentID DESC
            """
        )

        rows = cursor.fetchall()

        payments = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(payments),
            "payments": payments
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load payments.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DISH RATINGS
# ============================================================

@app.route(
    "/api/dish-ratings",
    methods=["GET"]
)
def get_dish_ratings():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        # Use DishRatings because this table exists
        # in the current database.
        cursor.execute(
            """
            SELECT
                dr.RatingID,
                dr.DishID,
                d.DishName,
                dr.CustomerID,
                c.CustomerName,
                dr.Rating,
                dr.Review,
                dr.CreatedAt
            FROM DishRatings dr
            INNER JOIN Dishes d
                ON dr.DishID = d.DishID
            LEFT JOIN Customers c
                ON dr.CustomerID = c.CustomerID
            ORDER BY dr.RatingID DESC
            """
        )

        rows = cursor.fetchall()

        ratings = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(ratings),
            "ratings": ratings
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load dish ratings.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ORDER ASSIGNMENTS
# ============================================================

@app.route(
    "/api/order-assignments",
    methods=["GET"]
)
def get_order_assignments():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                oa.AssignmentID,
                oa.OrderID,
                oa.UserID,
                u.FullName AS AssignedUser,
                u.Role,
                oa.AssignedAt,
                oa.CompletedAt,
                oa.Status
            FROM OrderAssignments oa
            INNER JOIN Users u
                ON oa.UserID = u.UserID
            ORDER BY oa.AssignmentID DESC
            """
        )

        rows = cursor.fetchall()

        assignments = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(assignments),
            "assignments": assignments
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load order assignments.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# SYSTEM SETTINGS
# ============================================================

@app.route(
    "/api/settings",
    methods=["GET"]
)
def get_settings():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                SettingID,
                SettingName,
                SettingValue,
                Description,
                UpdatedBy,
                UpdatedAt
            FROM SystemSettings
            ORDER BY SettingID
            """
        )

        rows = cursor.fetchall()

        settings = rows_to_dict(
            cursor,
            rows
        )

        return jsonify({
            "success": True,
            "count": len(settings),
            "settings": settings
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to load system settings.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# DATABASE TABLE CHECK
# ============================================================

@app.route(
    "/api/database/tables",
    methods=["GET"]
)
def database_tables():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """
        )

        rows = cursor.fetchall()

        tables = [
            row[0]
            for row in rows
        ]

        return jsonify({
            "success": True,
            "count": len(tables),
            "tables": tables
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message":
                "Unable to check database tables.",
            "error": str(error)
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "message":
            "Route not found.",
        "path":
            request.path
    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "success": False,
        "message":
            "Internal server error."
    }), 500


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    print(
        "============================================="
    )

    print(
        "HOTEL RESTAURANT MANAGEMENT SYSTEM"
    )

    print(
        "============================================="
    )

    print(
        "Database test:"
    )

    try:

        print(
            test_connection()
        )

    except Exception as error:

        print(
            {
                "success": False,
                "error": str(error)
            }
        )

    print(
        "============================================="
    )

    print(
        "Frontend:"
    )

    print(
        "http://127.0.0.1:5000/"
    )

    print(
        "Head:"
    )

    print(
        "http://127.0.0.1:5000/head.html"
    )

    print(
        "============================================="
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )