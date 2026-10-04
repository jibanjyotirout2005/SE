
# ============================================================
# HOTEL RESTAURANT MANAGEMENT SYSTEM
# backend/app.py
# ============================================================

from flask import Flask, jsonify, request, send_from_directory
import os
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from db import get_connection


# ============================================================
# FLASK APP CONFIGURATION
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

# app.py:
# E:\HOTEL_MGMT\SE\backend\app.py
#
# BASE_DIR:
# E:\HOTEL_MGMT\SE
#
# FRONTEND_DIR:
# E:\HOTEL_MGMT\SE\frontend

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
# FRONTEND PAGES
# ============================================================

@app.route("/")
@app.route("/index.html")
def home_page():
    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/customer")
@app.route("/customer.html")
def customer_page():
    return send_from_directory(
        FRONTEND_DIR,
        "customer.html"
    )


@app.route("/manager")
@app.route("/manager.html")
def manager_page():
    return send_from_directory(
        FRONTEND_DIR,
        "manager.html"
    )


@app.route("/waiter")
@app.route("/waiter.html")
def waiter_page():
    return send_from_directory(
        FRONTEND_DIR,
        "waiter.html"
    )


# ============================================================
# FRONTEND STATIC FILES
# ============================================================

@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(
        FRONTEND_DIR,
        filename
    )


# ============================================================
# COMMON HELPERS
# ============================================================

def get_json():
    """
    Safely get JSON request data.
    """

    data = request.get_json(
        silent=True
    )

    return data if isinstance(data, dict) else {}


def error(message, status=400):
    """
    Standard API error response.
    """

    return jsonify({
        "success": False,
        "message": message
    }), status


def row_to_dict(cursor, row):
    """
    Convert database row into dictionary.
    """

    columns = [
        column[0]
        for column in cursor.description
    ]

    result = dict(
        zip(columns, row)
    )

    for key, value in result.items():

        if isinstance(value, datetime):

            result[key] = value.isoformat(
                sep=" ",
                timespec="seconds"
            )

    return result


def rows_to_dicts(cursor, rows):
    """
    Convert multiple database rows
    into dictionaries.
    """

    return [
        row_to_dict(cursor, row)
        for row in rows
    ]


def normalize_status(status):
    """
    Normalize order status.
    """

    if status is None:
        return None

    value = str(
        status
    ).strip().lower()

    status_map = {

        "pending": "Pending",

        "preparing": "Preparing",

        "ready": "Ready",

        "completed": "Completed",

        "cancelled": "Cancelled",

        "canceled": "Cancelled",

        "accepted": "Preparing",

        "denied": "Cancelled",

        "rejected": "Cancelled"
    }

    return status_map.get(value)


def close_db(cursor, conn):
    """
    Safely close cursor and connection.
    """

    try:

        if cursor:
            cursor.close()

    finally:

        if conn:
            conn.close()


# ============================================================
# DATABASE TEST
# ============================================================

@app.route("/api/test-db", methods=["GET"])
def test_db():

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT DB_NAME() AS DatabaseName
        """)

        row = cursor.fetchone()

        return jsonify({

            "success": True,

            "message":
                "Database connection successful",

            "database":
                row[0] if row else None
        })

    except Exception as e:

        return error(
            f"Database connection failed: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# ============================================================
# CUSTOMER PART
# ============================================================

# -------------------- CUSTOMER DISHES -------------------------

@app.route("/api/dishes", methods=["GET"])
def get_dishes():

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
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
                UpdatedAt
            FROM Dishes
            ORDER BY DishID ASC
        """)

        dishes = rows_to_dicts(
            cursor,
            cursor.fetchall()
        )

        return jsonify({

            "success": True,

            "count": len(dishes),

            "dishes": dishes
        })

    except Exception as e:

        return error(
            f"Unable to load dishes: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- CUSTOMER PLACE ORDER --------------------

@app.route(
    "/api/customer/place-order",
    methods=["POST"]
)
def customer_place_order():

    data = get_json()

    customer_name = str(
        data.get(
            "customer_name",
            ""
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    table_number = str(
        data.get(
            "table_number",
            ""
        )
    ).strip()

    items = data.get(
        "items",
        []
    )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    if not customer_name:

        return error(
            "Customer name is required."
        )

    if not phone:

        return error(
            "Phone number is required."
        )

    if not table_number:

        return error(
            "Table number is required."
        )

    if not isinstance(
        items,
        list
    ) or not items:

        return error(
            "Please select at least one dish."
        )

    # ---------------------------------------------------------
    # PREPARE REQUESTED ITEMS
    # ---------------------------------------------------------

    requested_items = {}

    for item in items:

        try:

            dish_id = int(
                item.get(
                    "dish_id"
                )
            )

            quantity = int(
                item.get(
                    "quantity"
                )
            )

        except (
            TypeError,
            ValueError,
            AttributeError
        ):

            return error(
                "Invalid order item."
            )

        if quantity <= 0:

            return error(
                "Quantity must be greater than zero."
            )

        requested_items[dish_id] = (
            requested_items.get(
                dish_id,
                0
            ) + quantity
        )

    # ---------------------------------------------------------
    # DATABASE
    # ---------------------------------------------------------

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        verified_items = []

        total_amount = 0.0

        # -----------------------------------------------------
        # VERIFY DISHES AND STOCK
        # -----------------------------------------------------

        for dish_id, quantity in requested_items.items():

            cursor.execute("""
                SELECT
                    DishID,
                    DishName,
                    Price,
                    AvailableQuantity,
                    IsAvailable
                FROM Dishes
                WHERE DishID = ?
            """, (
                dish_id,
            ))

            row = cursor.fetchone()

            if not row:

                raise ValueError(
                    f"Dish ID {dish_id} was not found."
                )

            dish = row_to_dict(
                cursor,
                row
            )

            if not bool(
                dish["IsAvailable"]
            ):

                raise ValueError(
                    f'{dish["DishName"]} '
                    f'is currently unavailable.'
                )

            stock = int(
                dish["AvailableQuantity"] or 0
            )

            if stock < quantity:

                raise ValueError(
                    f'Only {stock} quantity of '
                    f'{dish["DishName"]} is available.'
                )

            price = float(
                dish["Price"]
            )

            line_total = (
                price * quantity
            )

            total_amount += line_total

            verified_items.append({

                "dish_id":
                    dish_id,

                "dish_name":
                    dish["DishName"],

                "quantity":
                    quantity,

                "price":
                    price,

                "line_total":
                    line_total

            })

        # -----------------------------------------------------
        # CREATE ORDER
        #
        # PaymentMode is intentionally NOT required here.
        # Customer only places the order.
        # -----------------------------------------------------

        cursor.execute("""
            INSERT INTO Orders
            (
                CustomerName,
                MobileNumber,
                TableNumber,
                TotalAmount,
                Status,
                OrderDate
            )
            OUTPUT INSERTED.OrderID
            VALUES
            (
                ?, ?, ?, ?, 'Pending', GETDATE()
            )
        """, (
            customer_name,
            phone,
            table_number,
            total_amount
        ))

        order_id = cursor.fetchone()[0]

        # -----------------------------------------------------
        # CREATE ORDER DETAILS + REDUCE STOCK
        # -----------------------------------------------------

        for item in verified_items:

            cursor.execute("""
                INSERT INTO OrderDetails
                (
                    OrderID,
                    DishID,
                    Quantity,
                    UnitPrice,
                    TotalPrice
                )
                VALUES
                (
                    ?, ?, ?, ?, ?
                )
            """, (

                order_id,

                item["dish_id"],

                item["quantity"],

                item["price"],

                item["line_total"]

            ))

            # Reduce stock

            cursor.execute("""
                UPDATE Dishes
                SET
                    AvailableQuantity =
                        AvailableQuantity - ?,
                    UpdatedAt = GETDATE()
                WHERE DishID = ?
            """, (

                item["quantity"],

                item["dish_id"]

            ))

        # -----------------------------------------------------
        # COMMIT
        # -----------------------------------------------------

        conn.commit()

        # -----------------------------------------------------
        # RESPONSE
        # -----------------------------------------------------

        return jsonify({

            "success":
                True,

            "message":
                "Order placed successfully.",

            "order": {

                "order_id":
                    order_id,

                "customer_name":
                    customer_name,

                "phone":
                    phone,

                "table_number":
                    table_number,

                "total_amount":
                    total_amount,

                "status":
                    "Pending"

            }

        }), 201

    # ---------------------------------------------------------
    # VALIDATION / STOCK ERROR
    # ---------------------------------------------------------

    except ValueError as e:

        if conn:

            conn.rollback()

        return error(
            str(e),
            400
        )

    # ---------------------------------------------------------
    # DATABASE ERROR
    # ---------------------------------------------------------

    except Exception as e:

        if conn:

            conn.rollback()

        return error(
            f"Unable to place order: {str(e)}",
            500
        )

    # ---------------------------------------------------------
    # CLOSE DATABASE
    # ---------------------------------------------------------

    finally:

        close_db(
            cursor,
            conn
        )


# ============================================================
# WAITER PART
# ============================================================

# -------------------- WAITER REGISTER -------------------------

@app.route(
    "/api/waiter/register",
    methods=["POST"]
)
def waiter_register():

    data = get_json()

    full_name = str(
        data.get(
            "full_name",
            ""
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    email = str(
        data.get(
            "email",
            ""
        )
    ).strip()

    password = str(
        data.get(
            "password",
            ""
        )
    ).strip()

    if not full_name:

        return error(
            "Full name is required."
        )

    if not phone:

        return error(
            "Phone number is required."
        )

    if not password:

        return error(
            "Password is required."
        )

    if (
        not phone.isdigit()
        or len(phone) != 10
    ):

        return error(
            "Please enter a valid 10-digit phone number."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT UserID
            FROM Users
            WHERE Phone = ?
               OR
              (
                Email IS NOT NULL
                AND Email = ?
              )
        """, (
            phone,
            email
        ))

        if cursor.fetchone():

            return error(
                "A user with this phone or email already exists.",
                409
            )

        password_hash = (
            generate_password_hash(
                password
            )
        )

        cursor.execute("""
            INSERT INTO Users
            (
                FullName,
                Phone,
                Email,
                PasswordHash,
                Role,
                IsActive,
                CreatedAt
            )
            VALUES
            (
                ?, ?, ?, ?, 'WAITER', 0, GETDATE()
            )
        """, (

            full_name,

            phone,

            email or None,

            password_hash
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Registration successful. "
                "Wait for Manager approval."
        }), 201

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to register waiter: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- WAITER LOGIN ----------------------------

@app.route(
    "/api/waiter/login",
    methods=["POST"]
)
def waiter_login():

    data = get_json()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    password = str(
        data.get(
            "password",
            ""
        )
    ).strip()

    if not phone or not password:

        return error(
            "Phone and password are required."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                UserID,
                FullName,
                Phone,
                Email,
                PasswordHash,
                Role,
                IsActive
            FROM Users
            WHERE Phone = ?
              AND Role = 'WAITER'
        """, (
            phone,
        ))

        row = cursor.fetchone()

        if not row:

            return error(
                "Invalid phone or password.",
                401
            )

        user = row_to_dict(
            cursor,
            row
        )

        if not check_password_hash(
            user["PasswordHash"],
            password
        ):

            return error(
                "Invalid phone or password.",
                401
            )

        if not bool(
            user["IsActive"]
        ):

            return error(
                "Your waiter account is still waiting "
                "for Manager approval.",
                403
            )

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

    except Exception as e:

        return error(
            f"Unable to login: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- WAITER STATUS ---------------------------

@app.route(
    "/api/waiter/check-status",
    methods=["GET"]
)
def waiter_check_status():

    phone = str(
        request.args.get(
            "phone",
            ""
        )
    ).strip()

    if not phone:

        return error(
            "Phone number is required."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                UserID,
                FullName,
                Phone,
                Email,
                IsActive
            FROM Users
            WHERE Phone = ?
              AND Role = 'WAITER'
        """, (
            phone,
        ))

        row = cursor.fetchone()

        if not row:

            return error(
                "Waiter account not found.",
                404
            )

        user = row_to_dict(
            cursor,
            row
        )

        return jsonify({

            "success": True,

            "is_active":
                bool(user["IsActive"]),

            "user": user
        })

    except Exception as e:

        return error(
            f"Unable to check waiter status: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- WAITER PLACE ORDER ----------------------

@app.route(
    "/api/waiter/place-order",
    methods=["POST"]
)
def waiter_place_order():

    return customer_place_order()


# ============================================================
# MANAGER PART
# ============================================================

# -------------------- MANAGER / HEAD SIGNUP ------------------

@app.route(
    "/api/auth/signup",
    methods=["POST"]
)
def signup():

    data = get_json()

    full_name = str(
        data.get(
            "full_name",
            ""
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    email = str(
        data.get(
            "email",
            ""
        )
    ).strip()

    password = str(
        data.get(
            "password",
            ""
        )
    ).strip()

    role = str(
        data.get(
            "role",
            ""
        )
    ).strip().upper()

    if not full_name:

        return error(
            "Full name is required."
        )

    if not phone:

        return error(
            "Phone number is required."
        )

    if not password:

        return error(
            "Password is required."
        )

    if role not in (
        "MANAGER",
        "HEAD"
    ):

        return error(
            "Role must be MANAGER or HEAD."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT UserID
            FROM Users
            WHERE Phone = ?
               OR
              (
                Email IS NOT NULL
                AND Email = ?
              )
        """, (
            phone,
            email
        ))

        if cursor.fetchone():

            return error(
                "A user with this phone or email already exists.",
                409
            )

        password_hash = (
            generate_password_hash(
                password
            )
        )

        cursor.execute("""
            INSERT INTO Users
            (
                FullName,
                Phone,
                Email,
                PasswordHash,
                Role,
                IsActive,
                CreatedAt
            )
            VALUES
            (
                ?, ?, ?, ?, ?, 1, GETDATE()
            )
        """, (

            full_name,

            phone,

            email or None,

            password_hash,

            role
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Account created successfully."
        }), 201

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to create account: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- AUTH LOGIN ------------------------------

@app.route(
    "/api/auth/login",
    methods=["POST"]
)
def auth_login():

    data = get_json()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    password = str(
        data.get(
            "password",
            ""
        )
    ).strip()

    role = str(
        data.get(
            "role",
            ""
        )
    ).strip().upper()

    if not phone or not password:

        return error(
            "Phone and password are required."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        if role in (
            "MANAGER",
            "HEAD"
        ):

            cursor.execute("""
                SELECT
                    UserID,
                    FullName,
                    Phone,
                    Email,
                    PasswordHash,
                    Role,
                    IsActive
                FROM Users
                WHERE Phone = ?
                  AND Role = ?
            """, (
                phone,
                role
            ))

        else:

            cursor.execute("""
                SELECT
                    UserID,
                    FullName,
                    Phone,
                    Email,
                    PasswordHash,
                    Role,
                    IsActive
                FROM Users
                WHERE Phone = ?
            """, (
                phone,
            ))

        row = cursor.fetchone()

        if not row:

            return error(
                "Invalid phone or password.",
                401
            )

        user = row_to_dict(
            cursor,
            row
        )

        if not check_password_hash(
            user["PasswordHash"],
            password
        ):

            return error(
                "Invalid phone or password.",
                401
            )

        if not bool(
            user["IsActive"]
        ):

            return error(
                "This account is inactive.",
                403
            )

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

    except Exception as e:

        return error(
            f"Unable to login: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- ADD DISH -------------------------------

@app.route(
    "/api/dishes",
    methods=["POST"]
)
def add_dish():

    data = get_json()

    dish_name = str(
        data.get(
            "dish_name",
            ""
        )
    ).strip()

    category = str(
        data.get(
            "category",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    image_url = str(
        data.get(
            "image_url",
            ""
        )
    ).strip()

    try:

        price = float(
            data.get(
                "price",
                0
            )
        )

        available_quantity = int(
            data.get(
                "available_quantity",
                0
            )
        )

        rating = float(
            data.get(
                "rating",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return error(
            "Price, quantity and rating must be valid numbers."
        )

    is_available = bool(
        data.get(
            "is_available",
            True
        )
    )

    if not dish_name:

        return error(
            "Dish name is required."
        )

    if price < 0:

        return error(
            "Price cannot be negative."
        )

    if available_quantity < 0:

        return error(
            "Available quantity cannot be negative."
        )

    if rating < 0 or rating > 5:

        return error(
            "Rating must be between 0 and 5."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Dishes
            (
                DishName,
                Category,
                Description,
                Price,
                AvailableQuantity,
                Rating,
                ImageURL,
                IsAvailable,
                UpdatedAt
            )
            OUTPUT INSERTED.DishID
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, GETDATE()
            )
        """, (

            dish_name,

            category,

            description,

            price,

            available_quantity,

            rating,

            image_url,

            is_available
        ))

        dish_id = cursor.fetchone()[0]

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Dish added successfully.",

            "dish_id":
                dish_id
        }), 201

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to add dish: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- UPDATE DISH ----------------------------

@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["PUT"]
)
def update_dish(dish_id):

    data = get_json()

    dish_name = str(
        data.get(
            "dish_name",
            ""
        )
    ).strip()

    category = str(
        data.get(
            "category",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    image_url = str(
        data.get(
            "image_url",
            ""
        )
    ).strip()

    try:

        price = float(
            data.get(
                "price",
                0
            )
        )

        available_quantity = int(
            data.get(
                "available_quantity",
                0
            )
        )

        rating = float(
            data.get(
                "rating",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return error(
            "Price, quantity and rating must be valid numbers."
        )

    is_available = bool(
        data.get(
            "is_available",
            True
        )
    )

    if not dish_name:

        return error(
            "Dish name is required."
        )

    if price < 0:

        return error(
            "Price cannot be negative."
        )

    if available_quantity < 0:

        return error(
            "Available quantity cannot be negative."
        )

    if rating < 0 or rating > 5:

        return error(
            "Rating must be between 0 and 5."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT DishID
            FROM Dishes
            WHERE DishID = ?
        """, (
            dish_id,
        ))

        if not cursor.fetchone():

            return error(
                "Dish not found.",
                404
            )

        cursor.execute("""
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
                UpdatedAt = GETDATE()
            WHERE DishID = ?
        """, (

            dish_name,

            category,

            description,

            price,

            available_quantity,

            rating,

            image_url,

            is_available,

            dish_id
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Dish updated successfully."
        })

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to update dish: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- DELETE DISH ----------------------------

@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["DELETE"]
)
def delete_dish(dish_id):

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        # Protect order history
        cursor.execute("""
            SELECT COUNT(*)
            FROM OrderDetails
            WHERE DishID = ?
        """, (
            dish_id,
        ))

        used_count = cursor.fetchone()[0]

        if used_count > 0:

            return error(

                "This dish cannot be deleted because it "
                "already exists in order history. "
                "Edit it or mark it unavailable instead.",

                409
            )

        cursor.execute("""
            DELETE FROM Dishes
            WHERE DishID = ?
        """, (
            dish_id,
        ))

        if cursor.rowcount == 0:

            return error(
                "Dish not found.",
                404
            )

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Dish deleted successfully."
        })

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to delete dish: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )



# -------------------- GET ORDERS ------------------------------

@app.route(
    "/api/orders",
    methods=["GET"]
)
def get_orders():

    selected_date = request.args.get(
        "date",
        ""
    ).strip()

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # -----------------------------------------------------
        # GET ORDERS
        # -----------------------------------------------------

        if selected_date:

            cursor.execute("""
                SELECT
                    o.OrderID,
                    o.CustomerName,
                    o.MobileNumber,
                    o.TableNumber,
                    o.TotalAmount,
                    o.Status,
                    o.OrderDate,
                    o.PaymentMode
                FROM Orders AS o
                WHERE CAST(o.OrderDate AS DATE) = ?
                ORDER BY o.OrderID DESC
            """, (
                selected_date,
            ))

        else:

            cursor.execute("""
                SELECT
                    o.OrderID,
                    o.CustomerName,
                    o.MobileNumber,
                    o.TableNumber,
                    o.TotalAmount,
                    o.Status,
                    o.OrderDate,
                    o.PaymentMode
                FROM Orders AS o
                ORDER BY o.OrderID DESC
            """)

        orders = rows_to_dicts(
            cursor,
            cursor.fetchall()
        )

        # -----------------------------------------------------
        # GET ORDER ITEMS
        # -----------------------------------------------------

        for order in orders:

            cursor.execute("""
                SELECT
                    od.OrderDetailID,
                    od.DishID,
                    d.DishName,
                    od.Quantity,
                    od.UnitPrice,
                    od.TotalPrice
                FROM OrderDetails AS od
                INNER JOIN Dishes AS d
                    ON d.DishID = od.DishID
                WHERE od.OrderID = ?
                ORDER BY od.OrderDetailID ASC
            """, (
                order["OrderID"],
            ))

            order["Items"] = rows_to_dicts(
                cursor,
                cursor.fetchall()
            )

        # -----------------------------------------------------
        # RESPONSE
        # -----------------------------------------------------

        return jsonify({

            "success": True,

            "count": len(orders),

            "orders": orders

        })

    except Exception as e:

        return error(
            f"Unable to load orders: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )

# -------------------- ORDER STATUS ----------------------------
# -------------------- ORDER STATUS ----------------------------

@app.route(
    "/api/orders/<int:order_id>/status",
    methods=["PUT"]
)
def update_order_status(order_id):

    data = get_json()

    new_status = normalize_status(
        data.get("status")
    )

    if not new_status:

        return error(
            "Invalid order status."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Status
            FROM Orders
            WHERE OrderID = ?
        """, (
            order_id,
        ))

        row = cursor.fetchone()

        if not row:

            return error(
                "Order not found.",
                404
            )

        old_status = str(
            row[0] or ""
        ).strip()

        # Restore stock when cancelled
        # for the first time.
        if (
            new_status == "Cancelled"
            and old_status != "Cancelled"
        ):

            cursor.execute("""
                SELECT
                    DishID,
                    Quantity
                FROM OrderDetails
                WHERE OrderID = ?
            """, (
                order_id,
            ))

            details = cursor.fetchall()

            for dish_id, quantity in details:

                cursor.execute("""
                    UPDATE Dishes
                    SET
                        AvailableQuantity =
                            AvailableQuantity + ?,
                        UpdatedAt = GETDATE()
                    WHERE DishID = ?
                """, (
                    quantity,
                    dish_id
                ))

        cursor.execute("""
            UPDATE Orders
            SET Status = ?
            WHERE OrderID = ?
        """, (
            new_status,
            order_id
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Order status updated successfully.",

            "order_id":
                order_id,

            "status":
                new_status
        })

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to update order: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )
# -------------------- ORDER PAYMENT --------------------------

# -------------------- ORDER PAYMENT --------------------------

@app.route(
    "/api/orders/<int:order_id>/payment",
    methods=["PUT"]
)
def update_order_payment(order_id):

    data = get_json()

    # Accept all common frontend field names
    raw_payment_method = (
        data.get("payment_method")
        or data.get("paymentMethod")
        or data.get("payment_mode")
        or data.get("paymentMode")
        or ""
    )

    payment_method = str(
        raw_payment_method
    ).strip().upper()

    # Normalize possible frontend values
    payment_map = {
        "CASH": "CASH",
        "CARD": "CARD",
        "UPI": "UPI"
    }

    payment_method = payment_map.get(
        payment_method
    )

    if not payment_method:

        return error(
            "Payment method must be CASH, UPI or CARD."
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # -----------------------------------------------------
        # CHECK ORDER
        # -----------------------------------------------------

        cursor.execute("""
            SELECT
                OrderID,
                TotalAmount,
                Status,
                PaymentMode
            FROM Orders
            WHERE OrderID = ?
        """, (
            order_id,
        ))

        order = cursor.fetchone()

        if not order:

            return error(
                "Order not found.",
                404
            )

        total_amount = float(
            order[1] or 0
        )

        current_status = str(
            order[2] or ""
        ).strip()

        # -----------------------------------------------------
        # ONLY COMPLETED ORDERS CAN BE MARKED PAID
        # -----------------------------------------------------

        if current_status != "Completed":

            return error(
                "Order must be completed before payment can be marked as paid."
            )

        # -----------------------------------------------------
        # CHECK PAYMENT MODE COLUMN
        # -----------------------------------------------------

        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Orders'
              AND COLUMN_NAME = 'PaymentMode'
        """)

        if not cursor.fetchone():

            return error(
                "PaymentMode column is missing from Orders table.",
                500
            )

        # -----------------------------------------------------
        # PREVENT DUPLICATE PAYMENT
        # -----------------------------------------------------

        existing_payment = order[3]

        if existing_payment:

            existing_payment = str(
                existing_payment
            ).strip()

            if existing_payment.upper() in (
                "CASH",
                "UPI",
                "CARD"
            ):

                return error(
                    "Payment has already been recorded for this order.",
                    409
                )

        # -----------------------------------------------------
        # SAVE PAYMENT METHOD
        # -----------------------------------------------------

        cursor.execute("""
            UPDATE Orders
            SET
                PaymentMode = ?
            WHERE OrderID = ?
        """, (
            payment_method,
            order_id
        ))

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Payment marked as paid successfully.",

            "order_id":
                order_id,

            "payment_mode":
                payment_method,

            "payment_status":
                "Paid",

            "total_amount":
                total_amount

        })

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to update payment: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )
# -------------------- MANAGER KPI -----------------------------

@app.route(
    "/api/manager/kpi",
    methods=["GET"]
)
def manager_kpi():

    selected_date = request.args.get(
        "date",
        ""
    ).strip()

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        if selected_date:

            cursor.execute("""
                SELECT
                    COUNT(*) AS TotalOrders,

                    ISNULL(
                        SUM(
                            CASE
                                WHEN Status = 'Completed'
                                     AND PaymentMode IS NOT NULL
                                THEN TotalAmount
                                ELSE 0
                            END
                        ),
                        0
                    ) AS TotalRevenue,

                    ISNULL(
                        SUM(
                            CASE
                                WHEN Status = 'Completed'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS CompletedOrders,

                    ISNULL(
                        SUM(
                            CASE
                                WHEN Status = 'Pending'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS PendingOrders

                FROM Orders

                WHERE CAST(OrderDate AS DATE) = ?
            """, (
                selected_date,
            ))

        else:

            cursor.execute("""
                SELECT
                    COUNT(*) AS TotalOrders,

                    ISNULL(
                        SUM(
                            CASE
                                WHEN Status = 'Completed'
                                     AND PaymentMode IS NOT NULL
                                THEN TotalAmount
                                ELSE 0
                            END
                        ),
                        0
                    ) AS TotalRevenue,

                    ISNULL(
                        SUM(
                            CASE
                                WHEN Status = 'Completed'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS CompletedOrders,

                    ISNULL(
                        SUM(
                            CASE
                                WHEN Status = 'Pending'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS PendingOrders

                FROM Orders
            """)

        row = cursor.fetchone()

        return jsonify({

            "success": True,

            "date":
                selected_date
                if selected_date
                else None,

            "kpi": {

                "total_orders":
                    int(row[0] or 0),

                "total_revenue":
                    float(row[1] or 0),

                "completed_orders":
                    int(row[2] or 0),

                "pending_orders":
                    int(row[3] or 0)
            }
        })

    except Exception as e:

        return error(
            f"Unable to load manager KPI: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )
# -------------------- MANAGER WAITERS -------------------------

@app.route(
    "/api/manager/waiters",
    methods=["GET"]
)
def manager_waiters():

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                UserID,
                FullName,
                Phone,
                Email,
                IsActive,
                CreatedAt
            FROM Users
            WHERE Role = 'WAITER'
            ORDER BY UserID DESC
        """)

        waiters = rows_to_dicts(
            cursor,
            cursor.fetchall()
        )

        return jsonify({

            "success": True,

            "waiters":
                waiters
        })

    except Exception as e:

        return error(
            f"Unable to load waiters: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- MANAGER WAITER STATUS -------------------

@app.route(
    "/api/manager/waiters/<int:user_id>/status",
    methods=["PUT"]
)
def manager_waiter_status(user_id):

    data = get_json()

    is_active = bool(
        data.get(
            "is_active",
            False
        )
    )

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Users
            SET IsActive = ?
            WHERE UserID = ?
              AND Role = 'WAITER'
        """, (

            is_active,

            user_id
        ))

        if cursor.rowcount == 0:

            return error(
                "Waiter not found.",
                404
            )

        conn.commit()

        return jsonify({

            "success": True,

            "message":
                "Waiter status updated successfully."
        })

    except Exception as e:

        if conn:
            conn.rollback()

        return error(
            f"Unable to update waiter: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )


# -------------------- MANAGER CUSTOMERS -----------------------

@app.route(
    "/api/manager/customers",
    methods=["GET"]
)
def manager_customers():

    conn = None
    cursor = None

    try:

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                MIN(OrderID) AS FirstOrderID,
                CustomerName,
                MobileNumber,
                COUNT(*) AS TotalOrders,
                MAX(OrderDate) AS LastOrderDate
            FROM Orders
            GROUP BY
                CustomerName,
                MobileNumber
            ORDER BY
                MAX(OrderDate) DESC
        """)

        customers = rows_to_dicts(
            cursor,
            cursor.fetchall()
        )

        return jsonify({

            "success": True,

            "customers":
                customers
        })

    except Exception as e:

        return error(
            f"Unable to load customers: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )

# ============================================================
# GENERATE / GET BILL
# ============================================================

@app.route(
    "/api/orders/<int:order_id>/bill",
    methods=["GET", "POST"]
)
def generate_order_bill(order_id):

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # ----------------------------------------------------
        # GET ORDER
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                OrderID,
                CustomerName,
                MobileNumber,
                TableNumber,
                TotalAmount,
                Status,
                OrderDate,
                PaymentMode
            FROM Orders
            WHERE OrderID = ?
        """, (
            order_id,
        ))

        order_row = cursor.fetchone()

        if not order_row:

            return error(
                "Order not found.",
                404
            )

        order = row_to_dict(
            cursor,
            order_row
        )

        # ----------------------------------------------------
        # GET ORDER ITEMS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                od.OrderDetailID,
                od.DishID,
                d.DishName,
                od.Quantity,
                od.UnitPrice,
                od.TotalPrice
            FROM OrderDetails AS od
            INNER JOIN Dishes AS d
                ON d.DishID = od.DishID
            WHERE od.OrderID = ?
            ORDER BY od.OrderDetailID ASC
        """, (
            order_id,
        ))

        items = rows_to_dicts(
            cursor,
            cursor.fetchall()
        )

        # ----------------------------------------------------
        # BILL DATA
        # ----------------------------------------------------

        subtotal = sum(
            float(
                item["TotalPrice"] or 0
            )
            for item in items
        )

        total_amount = float(
            order["TotalAmount"] or 0
        )

        payment_mode = (
            order.get("PaymentMode")
            or None
        )

        payment_status = (
            "Paid"
            if payment_mode
            else "Pending"
        )

        bill = {

            "bill_number":
                f"BILL-{order_id}",

            "order_id":
                order_id,

            "customer_name":
                order["CustomerName"],

            "phone":
                order["MobileNumber"],

            "table_number":
                order["TableNumber"],

            "order_date":
                order["OrderDate"],

            "status":
                order["Status"],

            "items":
                items,

            "subtotal":
                subtotal,

            "tax_amount":
                0.0,

            "discount_amount":
                0.0,

            "final_amount":
                total_amount,

            "payment_mode":
                payment_mode,

            "payment_status":
                payment_status
        }

        return jsonify({

            "success": True,

            "message":
                "Bill generated successfully.",

            "bill":
                bill
        })

    except Exception as e:

        return error(
            f"Unable to generate bill: {str(e)}",
            500
        )

    finally:

        close_db(
            cursor,
            conn
        )
# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("HOTEL RESTAURANT MANAGEMENT SYSTEM")
    print("=" * 60)
    print("Frontend : http://127.0.0.1:5000/")
    print("Customer : http://127.0.0.1:5000/customer")
    print("Manager  : http://127.0.0.1:5000/manager")
    print("Waiter   : http://127.0.0.1:5000/waiter")
    print("DB Test  : http://127.0.0.1:5000/api/test-db")
    print("=" * 60)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )


if __name__ == "__main__":
    main()