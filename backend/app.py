from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    session
)

from flask_cors import CORS

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import get_connection

from decimal import Decimal

from datetime import (
    datetime,
    date,
    time
)

import os
import traceback


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = "HOTEL_RESTAURANT_SECRET_KEY_2026"

CORS(
    app,
    supports_credentials=True
)


# ============================================================
# PROJECT PATHS
# ============================================================

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
# SYSTEM CONSTANTS
# ============================================================

# Only this Manager can access the Manager dashboard.
MANAGER_PHONE = "8260611800"


ORDER_STATUSES = {
    "PLACED",
    "ACCEPTED",
    "PREPARING",
    "READY",
    "SERVED",
    "COMPLETED",
    "CANCELLED"
}


PAYMENT_METHODS = {
    "CASH",
    "CARD",
    "UPI",
    "OTHER"
}


PAYMENT_STATUSES = {
    "PENDING",
    "SUCCESS",
    "FAILED",
    "REFUNDED"
}


BOOKING_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "CANCELLED",
    "COMPLETED"
}


# ============================================================
# COMMON HELPER FUNCTIONS START
# ============================================================

def get_json_data():

    data = request.get_json(
        silent=True
    )

    if isinstance(data, dict):
        return data

    return {}


def serialize_value(value):

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(
        value,
        (
            datetime,
            date,
            time
        )
    ):
        return value.isoformat()

    if isinstance(value, list):

        return [
            serialize_value(item)
            for item in value
        ]

    if isinstance(value, dict):

        return {
            key: serialize_value(val)
            for key, val in value.items()
        }

    return value


def serialize(data):

    return serialize_value(data)


def row_to_dict(
    cursor,
    row
):

    if row is None:
        return None

    columns = [
        column[0]
        for column in cursor.description
    ]

    return dict(
        zip(
            columns,
            row
        )
    )


def success_response(
    message,
    status=200,
    **kwargs
):

    response = {
        "success": True,
        "message": message
    }

    response.update(kwargs)

    return jsonify(
        serialize(response)
    ), status


def error_response(
    message,
    status=400,
    **kwargs
):

    response = {
        "success": False,
        "message": message
    }

    response.update(kwargs)

    return jsonify(
        serialize(response)
    ), status


def close_db(
    connection,
    cursor
):

    try:

        if cursor:
            cursor.close()

    except Exception:
        pass

    try:

        if connection:
            connection.close()

    except Exception:
        pass


def valid_phone(phone):

    phone = str(
        phone or ""
    ).strip()

    return (
        len(phone) == 10
        and phone.isdigit()
    )


def valid_email(email):

    email = str(
        email or ""
    ).strip()

    return (
        "@" in email
        and "." in email
        and len(email) <= 150
    )


# ============================================================
# COMMON HELPER FUNCTIONS END
# ============================================================


# ============================================================
# AUTHORIZATION HELPERS START
# ============================================================

def current_user():

    return session.get(
        "user"
    )


def require_login():

    user = current_user()

    if not user:

        return (
            None,
            error_response(
                "Please login first.",
                401
            )
        )

    return (
        user,
        None
    )


def require_manager():

    user = current_user()

    if not user:

        return (
            None,
            error_response(
                "Manager login is required.",
                401
            )
        )

    role = str(
        user.get("role", "")
    ).upper()

    if role != "MANAGER":

        return (
            None,
            error_response(
                "Manager access required.",
                403
            )
        )

    return (
        user,
        None
    )


def public_user(row):

    if not row:
        return None

    return {
        "UserID": row.get("UserID"),
        "FullName": row.get("FullName"),
        "Phone": row.get("Phone"),
        "Email": row.get("Email"),
        "Role": row.get("Role"),
        "IsActive": bool(
            row.get("IsActive")
        ),

        # Lowercase compatibility
        "user_id": row.get("UserID"),
        "full_name": row.get("FullName"),
        "phone": row.get("Phone"),
        "email": row.get("Email"),
        "role": row.get("Role"),
        "is_active": bool(
            row.get("IsActive")
        )
    }


# ============================================================
# AUTHORIZATION HELPERS END
# ============================================================


# ============================================================
# FRONTEND ROUTES START
# ============================================================

@app.route("/")
def index():

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/index.html")
def index_html():

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/customer.html")
def customer_html():

    return send_from_directory(
        FRONTEND_DIR,
        "customer.html"
    )


@app.route("/waiter.html")
def waiter_html():

    return send_from_directory(
        FRONTEND_DIR,
        "waiter.html"
    )


@app.route("/manager.html")
def manager_html():

    return send_from_directory(
        FRONTEND_DIR,
        "manager.html"
    )


# Compatibility routes
@app.route("/customer")
@app.route("/customer/")
def customer_page():

    return send_from_directory(
        FRONTEND_DIR,
        "customer.html"
    )


@app.route("/waiter")
@app.route("/waiter/")
def waiter_page():

    return send_from_directory(
        FRONTEND_DIR,
        "waiter.html"
    )


@app.route("/manager")
@app.route("/manager/")
@app.route("/manager/login")
@app.route("/manager/dashboard")
def manager_page():

    return send_from_directory(
        FRONTEND_DIR,
        "manager.html"
    )


# ============================================================
# FRONTEND ROUTES END
# ============================================================


# ============================================================
# SYSTEM / DATABASE TEST START
# ============================================================

@app.route(
    "/api",
    methods=["GET"]
)
def api_status():

    return success_response(
        "Hotel Restaurant Management System API is running"
    )


@app.route(
    "/api/health",
    methods=["GET"]
)
def health():

    return success_response(
        "API is healthy."
    )


@app.route(
    "/api/test-db",
    methods=["GET"]
)
def test_database():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT DB_NAME()"
        )

        row = cursor.fetchone()

        database_name = (
            row[0]
            if row
            else None
        )

        return success_response(
            "Database connection successful.",
            database=database_name
        )

    except Exception as error:

        traceback.print_exc()

        return error_response(
            "Database connection failed.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# SYSTEM / DATABASE TEST END
# ============================================================


# ============================================================
# AUTHENTICATION START
# ============================================================

@app.route(
    "/api/auth/login",
    methods=["POST"]
)
def auth_login():

    connection = None
    cursor = None

    try:

        data = get_json_data()

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
        )

        if not valid_phone(phone):

            return error_response(
                "Please enter a valid 10-digit phone number.",
                400
            )

        if not password:

            return error_response(
                "Password is required.",
                400
            )

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
                IsActive
            FROM Users
            WHERE Phone = ?
            """,
            (
                phone,
            )
        )

        row = cursor.fetchone()

        if not row:

            return error_response(
                "Invalid phone number or password.",
                401
            )

        user = row_to_dict(
            cursor,
            row
        )

        role = str(
            user.get("Role", "")
        ).upper()

        # ----------------------------------------------------
        # ONLY MANAGER / WAITER CAN LOGIN THROUGH THIS API
        # ----------------------------------------------------

        if role not in (
            "MANAGER",
            "WAITER"
        ):

            return error_response(
                "This account is not allowed to login here.",
                403
            )

        # ----------------------------------------------------
        # ONLY ONE MANAGER
        # ----------------------------------------------------

        if role == "MANAGER":

            if phone != MANAGER_PHONE:

                return error_response(
                    "Manager access is restricted.",
                    403
                )

        # ----------------------------------------------------
        # ACTIVE CHECK
        # ----------------------------------------------------

        if not bool(
            user.get("IsActive")
        ):

            if role == "WAITER":

                return error_response(
                    "Your waiter account is waiting for Manager approval.",
                    403
                )

            return error_response(
                "This account is inactive.",
                403
            )

        # ----------------------------------------------------
        # PASSWORD CHECK
        # ----------------------------------------------------

        if not check_password_hash(
            user["PasswordHash"],
            password
        ):

            return error_response(
                "Invalid phone number or password.",
                401
            )

        safe_user = public_user(
            user
        )

        session["user"] = safe_user

        return success_response(
            "Login successful.",
            user=safe_user
        )

    except Exception as error:

        traceback.print_exc()

        return error_response(
            "Unable to login.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ------------------------------------------------------------
# WAITER LOGIN
# ------------------------------------------------------------

@app.route(
    "/api/waiter/login",
    methods=["POST"]
)
def waiter_login():

    connection = None
    cursor = None

    try:

        data = get_json_data()

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
        )

        if not valid_phone(phone):

            return error_response(
                "Please enter a valid 10-digit phone number.",
                400
            )

        if not password:

            return error_response(
                "Password is required.",
                400
            )

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
                IsActive
            FROM Users
            WHERE Phone = ?
            AND Role = 'WAITER'
            """,
            (
                phone,
            )
        )

        row = cursor.fetchone()

        if not row:

            return error_response(
                "Invalid waiter phone number or password.",
                401
            )

        user = row_to_dict(
            cursor,
            row
        )

        if not bool(
            user["IsActive"]
        ):

            return error_response(
                "Your waiter account is waiting for Manager approval.",
                403
            )

        if not check_password_hash(
            user["PasswordHash"],
            password
        ):

            return error_response(
                "Invalid waiter phone number or password.",
                401
            )

        safe_user = public_user(
            user
        )

        session["user"] = safe_user

        return success_response(
            "Waiter login successful.",
            user=safe_user
        )

    except Exception as error:

        traceback.print_exc()

        return error_response(
            "Unable to login waiter.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ------------------------------------------------------------
# WAITER REGISTER
# ------------------------------------------------------------

@app.route(
    "/api/waiter/register",
    methods=["POST"]
)
def waiter_register():

    connection = None
    cursor = None

    try:

        data = get_json_data()

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
        ).strip().lower()

        password = str(
            data.get(
                "password",
                ""
            )
        )

        if not full_name:

            return error_response(
                "Full name is required.",
                400
            )

        if not valid_phone(phone):

            return error_response(
                "Phone number must contain exactly 10 digits.",
                400
            )

        if not valid_email(email):

            return error_response(
                "Please enter a valid email address.",
                400
            )

        if len(password) < 6:

            return error_response(
                "Password must contain at least 6 characters.",
                400
            )

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                UserID
            FROM Users
            WHERE Phone = ?
            OR Email = ?
            """,
            (
                phone,
                email
            )
        )

        if cursor.fetchone():

            return error_response(
                "A user with this phone number or email already exists.",
                409
            )

        password_hash = generate_password_hash(
            password
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # WAITER IS CREATED INACTIVE.
        # MANAGER MUST APPROVE IT.
        # ----------------------------------------------------

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
                'WAITER',
                0
            )
            """,
            (
                full_name,
                phone,
                email,
                password_hash
            )
        )

        connection.commit()

        return success_response(
            "Waiter registration successful. Waiting for Manager approval.",
            201
        )

    except Exception as error:

        if connection:

            connection.rollback()

        traceback.print_exc()

        return error_response(
            "Unable to register waiter.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ------------------------------------------------------------
# WAITER APPROVAL STATUS
# ------------------------------------------------------------

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

    if not valid_phone(phone):

        return error_response(
            "A valid 10-digit phone number is required.",
            400
        )

    connection = None
    cursor = None

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
                IsActive
            FROM Users
            WHERE Phone = ?
            AND Role = 'WAITER'
            """,
            (
                phone,
            )
        )

        row = cursor.fetchone()

        if not row:

            return error_response(
                "Waiter account not found.",
                404
            )

        user = row_to_dict(
            cursor,
            row
        )

        is_active = bool(
            user["IsActive"]
        )

        return success_response(
            "Waiter approval status loaded.",
            is_active=is_active,
            approved=is_active,
            user=public_user(user)
        )

    except Exception as error:

        return error_response(
            "Unable to check waiter status.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ------------------------------------------------------------
# CURRENT SESSION
# ------------------------------------------------------------

@app.route(
    "/api/auth/me",
    methods=["GET"]
)
def auth_me():

    user = current_user()

    if not user:

        return error_response(
            "Not logged in.",
            401
        )

    return success_response(
        "Current user loaded.",
        user=user
    )


# ------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------

@app.route(
    "/api/auth/logout",
    methods=["POST"]
)
def auth_logout():

    session.clear()

    return success_response(
        "Logout successful."
    )


# ============================================================
# AUTHENTICATION END
# ============================================================


# ============================================================
# CUSTOMER PART START
# ============================================================

@app.route(
    "/api/customer/place-order",
    methods=["POST"]
)
def customer_place_order():

    return create_order(
        "CUSTOMER"
    )


# Customer order history
@app.route(
    "/api/orders/customer",
    methods=["GET"]
)
def customer_order_history():

    phone = str(
        request.args.get(
            "phone",
            ""
        )
    ).strip()

    if not valid_phone(phone):

        return error_response(
            "A valid 10-digit phone number is required.",
            400
        )

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                OrderID,
                CustomerName,
                MobileNumber,
                TableNumber,
                TotalAmount,
                OrderStatus,
                PaymentStatus,
                CreatedAt,
                UpdatedAt
            FROM Orders
            WHERE MobileNumber = ?
            ORDER BY CreatedAt DESC
            """,
            (
                phone,
            )
        )

        orders = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Customer order history loaded.",
            orders=orders
        )

    except Exception as error:

        return error_response(
            "Unable to load customer order history.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ------------------------------------------------------------
# CUSTOMER BOOKING
# ------------------------------------------------------------

@app.route(
    "/api/bookings",
    methods=["POST"]
)
def create_booking():

    connection = None
    cursor = None

    try:

        data = get_json_data()

        customer_name = str(
            data.get(
                "customer_name",
                data.get(
                    "CustomerName",
                    ""
                )
            )
        ).strip()

        phone = str(
            data.get(
                "phone",
                data.get(
                    "Phone",
                    ""
                )
            )
        ).strip()

        booking_date = data.get(
            "booking_date",
            data.get(
                "BookingDate"
            )
        )

        booking_time = data.get(
            "booking_time",
            data.get(
                "BookingTime"
            )
        )

        guests = data.get(
            "guests",
            data.get(
                "NumberOfGuests"
            )
        )

        table_number = data.get(
            "table_number",
            data.get(
                "TableNumber"
            )
        )

        if not customer_name:

            return error_response(
                "Customer name is required."
            )

        if not valid_phone(phone):

            return error_response(
                "A valid 10-digit phone number is required."
            )

        if not booking_date or not booking_time:

            return error_response(
                "Booking date and time are required."
            )

        try:

            guests = int(
                guests
            )

        except Exception:

            return error_response(
                "Number of guests must be valid."
            )

        if guests <= 0:

            return error_response(
                "Number of guests must be greater than zero."
            )

        if table_number in (
            "",
            None
        ):

            table_number = None

        else:

            try:

                table_number = int(
                    table_number
                )

            except Exception:

                return error_response(
                    "Table number must be a number."
                )

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO Bookings
            (
                CustomerName,
                Phone,
                BookingDate,
                BookingTime,
                NumberOfGuests,
                TableNumber,
                Status,
                CreatedAt
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                'PENDING',
                SYSDATETIME()
            )
            """,
            (
                customer_name,
                phone,
                booking_date,
                booking_time,
                guests,
                table_number
            )
        )

        cursor.execute(
            """
            SELECT
                CAST(
                    SCOPE_IDENTITY()
                    AS INT
                )
            """
        )

        booking_id = cursor.fetchone()[0]

        connection.commit()

        return success_response(
            "Booking created successfully.",
            201,
            booking_id=booking_id
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to create booking.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# CUSTOMER PART END
# ============================================================


# ============================================================
# WAITER PART START
# ============================================================

@app.route(
    "/api/orders/waiter",
    methods=["POST"]
)
def waiter_order():

    user, error = require_login()

    if error:

        return error

    if str(
        user.get("role", "")
    ).upper() != "WAITER":

        return error_response(
            "Waiter access required.",
            403
        )

    return create_order(
        "WAITER"
    )


# ============================================================
# WAITER PART END
# ============================================================


# ============================================================
# DISHES PART START
# ============================================================

@app.route(
    "/api/dishes",
    methods=["GET"]
)
def get_dishes():

    connection = None
    cursor = None

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
                UpdatedAt
            FROM Dishes
            ORDER BY DishID ASC
            """
        )

        dishes = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Dishes loaded successfully.",
            dishes=dishes,
            count=len(dishes)
        )

    except Exception as error:

        return error_response(
            "Unable to load dishes.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["GET"]
)
def get_single_dish(
    dish_id
):

    connection = None
    cursor = None

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
                UpdatedAt
            FROM Dishes
            WHERE DishID = ?
            """,
            (
                dish_id,
            )
        )

        row = cursor.fetchone()

        if not row:

            return error_response(
                "Dish not found.",
                404
            )

        dish = row_to_dict(
            cursor,
            row
        )

        return success_response(
            "Dish loaded successfully.",
            dish=dish
        )

    except Exception as error:

        return error_response(
            "Unable to load dish.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/dishes",
    methods=["POST"]
)
def add_dish():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        data = get_json_data()

        name = str(
            data.get(
                "name",
                data.get(
                    "DishName",
                    ""
                )
            )
        ).strip()

        category = str(
            data.get(
                "category",
                data.get(
                    "Category",
                    ""
                )
            )
        ).strip()

        description = str(
            data.get(
                "description",
                data.get(
                    "Description",
                    ""
                )
            )
        ).strip()

        price = float(
            data.get(
                "price",
                data.get(
                    "Price",
                    0
                )
            )
        )

        quantity = int(
            data.get(
                "available_quantity",
                data.get(
                    "AvailableQuantity",
                    0
                )
            )
        )

        rating = float(
            data.get(
                "rating",
                data.get(
                    "Rating",
                    0
                )
            )
        )

        image_url = str(
            data.get(
                "image_url",
                data.get(
                    "ImageURL",
                    ""
                )
            )
        ).strip()

        is_available = data.get(
            "is_available",
            data.get(
                "IsAvailable",
                quantity > 0
            )
        )

        if not name:

            return error_response(
                "Dish name is required."
            )

        if not category:

            return error_response(
                "Category is required."
            )

        if price < 0:

            return error_response(
                "Price cannot be negative."
            )

        if quantity < 0:

            return error_response(
                "Quantity cannot be negative."
            )

        if rating < 0 or rating > 5:

            return error_response(
                "Rating must be between 0 and 5."
            )

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
                IsAvailable,
                UpdatedAt
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                SYSDATETIME()
            )
            """,
            (
                name,
                category,
                description or None,
                price,
                quantity,
                rating,
                image_url or None,
                1 if bool(is_available)
                and quantity > 0
                else 0
            )
        )

        cursor.execute(
            """
            SELECT
                CAST(
                    SCOPE_IDENTITY()
                    AS INT
                )
            """
        )

        dish_id = cursor.fetchone()[0]

        connection.commit()

        return success_response(
            "Dish added successfully.",
            201,
            dish_id=dish_id
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to add dish.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["PUT"]
)
def update_dish(
    dish_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        data = get_json_data()

        name = str(
            data.get(
                "name",
                data.get(
                    "DishName",
                    ""
                )
            )
        ).strip()

        category = str(
            data.get(
                "category",
                data.get(
                    "Category",
                    ""
                )
            )
        ).strip()

        description = str(
            data.get(
                "description",
                data.get(
                    "Description",
                    ""
                )
            )
        ).strip()

        price = float(
            data.get(
                "price",
                data.get(
                    "Price",
                    0
                )
            )
        )

        quantity = int(
            data.get(
                "available_quantity",
                data.get(
                    "AvailableQuantity",
                    0
                )
            )
        )

        rating = float(
            data.get(
                "rating",
                data.get(
                    "Rating",
                    0
                )
            )
        )

        image_url = str(
            data.get(
                "image_url",
                data.get(
                    "ImageURL",
                    ""
                )
            )
        ).strip()

        if not name:

            return error_response(
                "Dish name is required."
            )

        if not category:

            return error_response(
                "Category is required."
            )

        if price < 0:

            return error_response(
                "Price cannot be negative."
            )

        if quantity < 0:

            return error_response(
                "Quantity cannot be negative."
            )

        if rating < 0 or rating > 5:

            return error_response(
                "Rating must be between 0 and 5."
            )

        connection = get_connection()

        cursor = connection.cursor()

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
                name,
                category,
                description or None,
                price,
                quantity,
                rating,
                image_url or None,
                1 if quantity > 0 else 0,
                dish_id
            )
        )

        if cursor.rowcount == 0:

            return error_response(
                "Dish not found.",
                404
            )

        connection.commit()

        return success_response(
            "Dish updated successfully."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to update dish.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/dishes/<int:dish_id>",
    methods=["DELETE"]
)
def delete_dish(
    dish_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM OrderDetails
            WHERE DishID = ?
            """,
            (
                dish_id,
            )
        )

        order_count = cursor.fetchone()[0]

        if order_count > 0:

            return error_response(
                "This dish cannot be deleted because it exists in order history.",
                409
            )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM DishRatings
            WHERE DishID = ?
            """,
            (
                dish_id,
            )
        )

        rating_count = cursor.fetchone()[0]

        if rating_count > 0:

            return error_response(
                "This dish cannot be deleted because it has ratings.",
                409
            )

        cursor.execute(
            """
            DELETE FROM Dishes
            WHERE DishID = ?
            """,
            (
                dish_id,
            )
        )

        if cursor.rowcount == 0:

            return error_response(
                "Dish not found.",
                404
            )

        connection.commit()

        return success_response(
            "Dish deleted successfully."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to delete dish.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# DISHES PART END
# ============================================================


# ============================================================
# ORDER CREATION PART START
# ============================================================

def create_order(
    source
):

    connection = None
    cursor = None

    try:

        data = get_json_data()

        customer_name = str(
            data.get(
                "customer_name",
                data.get(
                    "CustomerName",
                    ""
                )
            )
        ).strip()

        phone = str(
            data.get(
                "phone",
                data.get(
                    "mobile_number",
                    data.get(
                        "MobileNumber",
                        ""
                    )
                )
            )
        ).strip()

        table_number = data.get(
            "table_number",
            data.get(
                "TableNumber"
            )
        )

        items = data.get(
            "items",
            data.get(
                "Items",
                []
            )
        )

        if not customer_name:

            return error_response(
                "Customer name is required."
            )

        if not valid_phone(phone):

            return error_response(
                "Mobile number must contain exactly 10 digits."
            )

        try:

            table_number = int(
                table_number
            )

        except Exception:

            return error_response(
                "Table number must be a number."
            )

        if table_number <= 0:

            return error_response(
                "Table number must be greater than zero."
            )

        if not isinstance(
            items,
            list
        ) or not items:

            return error_response(
                "At least one dish must be selected."
            )

        connection = get_connection()

        cursor = connection.cursor()

        validated_items = []

        total_amount = Decimal(
            "0.00"
        )

        # ----------------------------------------------------
        # VALIDATE EVERY DISH
        # ----------------------------------------------------

        for item in items:

            dish_id = item.get(
                "dish_id",
                item.get(
                    "DishID"
                )
            )

            quantity = item.get(
                "quantity",
                item.get(
                    "Quantity"
                )
            )

            try:

                dish_id = int(
                    dish_id
                )

                quantity = int(
                    quantity
                )

            except Exception:

                connection.rollback()

                return error_response(
                    "Invalid dish or quantity."
                )

            if quantity <= 0:

                connection.rollback()

                return error_response(
                    "Quantity must be greater than zero."
                )

            cursor.execute(
                """
                SELECT
                    DishID,
                    DishName,
                    Price,
                    AvailableQuantity,
                    IsAvailable
                FROM Dishes
                WHERE DishID = ?
                """,
                (
                    dish_id,
                )
            )

            dish_row = cursor.fetchone()

            if not dish_row:

                connection.rollback()

                return error_response(
                    "Dish not found.",
                    404
                )

            dish = row_to_dict(
                cursor,
                dish_row
            )

            if not bool(
                dish["IsAvailable"]
            ):

                connection.rollback()

                return error_response(
                    f'{dish["DishName"]} is currently unavailable.'
                )

            available_quantity = int(
                dish["AvailableQuantity"]
            )

            if available_quantity < quantity:

                connection.rollback()

                return error_response(
                    f'Only {available_quantity} quantity of {dish["DishName"]} is available.'
                )

            price = Decimal(
                str(
                    dish["Price"]
                )
            )

            subtotal = (
                price *
                quantity
            )

            total_amount += subtotal

            validated_items.append({

                "DishID":
                    dish["DishID"],

                "DishName":
                    dish["DishName"],

                "Quantity":
                    quantity,

                "Price":
                    price,

                "SubTotal":
                    subtotal,

                "AvailableQuantity":
                    available_quantity
            })

        # ----------------------------------------------------
        # INSERT ORDER
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO Orders
            (
                CustomerName,
                MobileNumber,
                TableNumber,
                TotalAmount,
                OrderStatus,
                PaymentStatus,
                CreatedAt,
                UpdatedAt
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                'PLACED',
                'PENDING',
                SYSDATETIME(),
                SYSDATETIME()
            )
            """,
            (
                customer_name,
                phone,
                table_number,
                total_amount
            )
        )

        cursor.execute(
            """
            SELECT
                CAST(
                    SCOPE_IDENTITY()
                    AS INT
                )
            """
        )

        order_id = cursor.fetchone()[0]

        # ----------------------------------------------------
        # INSERT ORDER DETAILS
        # ----------------------------------------------------

        for item in validated_items:

            cursor.execute(
                """
                INSERT INTO OrderDetails
                (
                    OrderID,
                    DishID,
                    Quantity,
                    Price,
                    CreatedAt
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    SYSDATETIME()
                )
                """,
                (
                    order_id,
                    item["DishID"],
                    item["Quantity"],
                    item["Price"]
                )
            )

            # ------------------------------------------------
            # REDUCE STOCK
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE Dishes
                SET
                    AvailableQuantity =
                        AvailableQuantity - ?,

                    IsAvailable =
                        CASE
                            WHEN
                                AvailableQuantity - ? <= 0
                            THEN 0
                            ELSE IsAvailable
                        END,

                    UpdatedAt =
                        SYSDATETIME()

                WHERE
                    DishID = ?

                    AND AvailableQuantity >= ?
                """,
                (
                    item["Quantity"],
                    item["Quantity"],
                    item["DishID"],
                    item["Quantity"]
                )
            )

            if cursor.rowcount == 0:

                connection.rollback()

                return error_response(
                    "Stock changed while placing the order. Please try again.",
                    409
                )

        connection.commit()

        response_order = {

            "order_id":
                int(order_id),

            "OrderID":
                int(order_id),

            "customer_name":
                customer_name,

            "CustomerName":
                customer_name,

            "phone":
                phone,

            "MobileNumber":
                phone,

            "table_number":
                table_number,

            "TableNumber":
                table_number,

            "total_amount":
                float(total_amount),

            "TotalAmount":
                float(total_amount),

            "order_status":
                "PLACED",

            "OrderStatus":
                "PLACED",

            "payment_status":
                "PENDING",

            "PaymentStatus":
                "PENDING",

            "source":
                source,

            "OrderSource":
                source,

            "items": [
                {
                    "DishID":
                        item["DishID"],

                    "DishName":
                        item["DishName"],

                    "Quantity":
                        item["Quantity"],

                    "Price":
                        float(item["Price"]),

                    "SubTotal":
                        float(item["SubTotal"])
                }
                for item in validated_items
            ]
        }

        return success_response(
            "Order placed successfully.",
            201,
            order=response_order,
            order_id=int(order_id),
            OrderID=int(order_id)
        )

    except Exception as error:

        if connection:

            connection.rollback()

        traceback.print_exc()

        return error_response(
            "Unable to place order.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# ORDER CREATION PART END
# ============================================================


# ============================================================
# ORDER MANAGEMENT PART START
# ============================================================

@app.route(
    "/api/orders",
    methods=["GET"]
)
def get_orders():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        date_value = request.args.get(
            "date"
        )

        query = """
            SELECT
                OrderID,
                CustomerName,
                MobileNumber,
                TableNumber,
                TotalAmount,
                OrderStatus,
                PaymentStatus,
                CreatedAt,
                UpdatedAt
            FROM Orders
        """

        parameters = []

        if date_value:

            query += """
                WHERE
                    CAST(
                        CreatedAt
                        AS DATE
                    ) = ?
            """

            parameters.append(
                date_value
            )

        query += """
            ORDER BY
                CreatedAt DESC
        """

        cursor.execute(
            query,
            parameters
        )

        orders = []

        for row in cursor.fetchall():

            order = row_to_dict(
                cursor,
                row
            )

            # Compatibility fields
            order["Status"] = (
                order["OrderStatus"]
            )

            order["order_id"] = (
                order["OrderID"]
            )

            order["customer_name"] = (
                order["CustomerName"]
            )

            order["mobile_number"] = (
                order["MobileNumber"]
            )

            order["table_number"] = (
                order["TableNumber"]
            )

            order["total_amount"] = (
                float(
                    order["TotalAmount"]
                )
                if order["TotalAmount"]
                is not None
                else 0
            )

            order["order_status"] = (
                order["OrderStatus"]
            )

            order["payment_status"] = (
                order["PaymentStatus"]
            )

            order["created_at"] = (
                order["CreatedAt"]
            )

            orders.append(
                order
            )

        return success_response(
            "Orders loaded successfully.",
            orders=orders,
            count=len(orders)
        )

    except Exception as error:

        return error_response(
            "Unable to load orders.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/orders/<int:order_id>",
    methods=["GET"]
)
def get_order(
    order_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                OrderID,
                CustomerName,
                MobileNumber,
                TableNumber,
                TotalAmount,
                OrderStatus,
                PaymentStatus,
                CreatedAt,
                UpdatedAt
            FROM Orders
            WHERE OrderID = ?
            """,
            (
                order_id,
            )
        )

        row = cursor.fetchone()

        if not row:

            return error_response(
                "Order not found.",
                404
            )

        order = row_to_dict(
            cursor,
            row
        )

        cursor.execute(
            """
            SELECT
                od.OrderDetailID,
                od.OrderID,
                od.DishID,
                d.DishName,
                od.Quantity,
                od.Price,
                od.SubTotal,
                od.CreatedAt
            FROM OrderDetails od
            INNER JOIN Dishes d
                ON od.DishID = d.DishID
            WHERE od.OrderID = ?
            ORDER BY od.OrderDetailID ASC
            """,
            (
                order_id,
            )
        )

        details = [
            row_to_dict(
                cursor,
                detail
            )
            for detail
            in cursor.fetchall()
        ]

        order["Items"] = details

        order["items"] = details

        order["order_id"] = (
            order["OrderID"]
        )

        order["customer_name"] = (
            order["CustomerName"]
        )

        order["phone"] = (
            order["MobileNumber"]
        )

        order["table_number"] = (
            order["TableNumber"]
        )

        order["total_amount"] = float(
            order["TotalAmount"]
        )

        return success_response(
            "Order loaded successfully.",
            order=order,
            details=details,
            items=details
        )

    except Exception as error:

        return error_response(
            "Unable to load order.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/orders/<int:order_id>/status",
    methods=["PUT"]
)
def update_order_status(
    order_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        data = get_json_data()

        status = str(
            data.get(
                "status",
                data.get(
                    "OrderStatus",
                    ""
                )
            )
        ).strip().upper()

        if status not in ORDER_STATUSES:

            return error_response(
                "Invalid order status.",
                400
            )

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE Orders
            SET
                OrderStatus = ?,
                UpdatedAt = SYSDATETIME()
            WHERE OrderID = ?
            """,
            (
                status,
                order_id
            )
        )

        if cursor.rowcount == 0:

            return error_response(
                "Order not found.",
                404
            )

        connection.commit()

        return success_response(
            "Order status updated successfully.",
            order_id=order_id,
            order_status=status
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to update order status.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# ORDER MANAGEMENT PART END
# ============================================================


# ============================================================
# MANAGER DASHBOARD PART START
# ============================================================

@app.route(
    "/api/dashboard/summary",
    methods=["GET"]
)
def dashboard_summary():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        # ----------------------------------------------------
        # TOTAL DISHES
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                IsAvailable = 1
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )
            FROM Dishes
            """
        )

        dish_summary = cursor.fetchone()

        # ----------------------------------------------------
        # TOTAL ORDERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*),

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                OrderStatus IN
                                (
                                    'PLACED',
                                    'ACCEPTED',
                                    'PREPARING'
                                )
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                OrderStatus =
                                'COMPLETED'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                OrderStatus =
                                'COMPLETED'
                            THEN TotalAmount
                            ELSE 0
                        END
                    ),
                    0
                )
            FROM Orders
            """
        )

        order_summary = cursor.fetchone()

        # ----------------------------------------------------
        # UNIQUE CUSTOMERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*)
            FROM
            (
                SELECT
                    MobileNumber
                FROM Orders
                GROUP BY
                    MobileNumber
            ) AS CustomerList
            """
        )

        customer_count = (
            cursor.fetchone()[0]
        )

        # ----------------------------------------------------
        # PAYMENTS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*),

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                PaymentStatus =
                                'SUCCESS'
                            THEN Amount
                            ELSE 0
                        END
                    ),
                    0
                )
            FROM Payments
            """
        )

        payment_summary = (
            cursor.fetchone()
        )

        return success_response(
            "Dashboard summary loaded successfully.",

            summary={

                "total_dishes":
                    dish_summary[0] or 0,

                "available_dishes":
                    dish_summary[1] or 0,

                "total_orders":
                    order_summary[0] or 0,

                "pending_orders":
                    order_summary[1] or 0,

                "completed_orders":
                    order_summary[2] or 0,

                "total_customers":
                    customer_count or 0,

                "total_transactions":
                    payment_summary[0] or 0,

                "total_revenue":
                    float(
                        payment_summary[1] or 0
                    ),

                "daily_order_revenue":
                    float(
                        order_summary[3] or 0
                    )
            }
        )

    except Exception as error:

        return error_response(
            "Unable to load dashboard summary.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# MANAGER DASHBOARD PART END
# ============================================================


# ============================================================
# PAYMENT / TRANSACTION PART START
# ============================================================

@app.route(
    "/api/transactions",
    methods=["GET"]
)
def get_transactions():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                p.PaymentID AS TransactionID,
                p.OrderID,
                o.CustomerName,
                p.Amount,
                p.PaymentMethod,
                p.PaymentStatus,
                p.TransactionReference,
                p.PaymentDate AS TransactionDate
            FROM Payments p
            INNER JOIN Orders o
                ON p.OrderID = o.OrderID
            ORDER BY
                p.PaymentDate DESC
            """
        )

        transactions = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Transactions loaded successfully.",
            transactions=transactions
        )

    except Exception as error:

        return error_response(
            "Unable to load transactions.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/payments",
    methods=["GET"]
)
def get_payments():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                PaymentID,
                OrderID,
                Amount,
                PaymentMethod,
                PaymentStatus,
                TransactionReference,
                PaymentDate
            FROM Payments
            ORDER BY PaymentDate DESC
            """
        )

        payments = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Payments loaded successfully.",
            payments=payments
        )

    except Exception as error:

        return error_response(
            "Unable to load payments.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/payments",
    methods=["POST"]
)
def record_payment():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        data = get_json_data()

        order_id = int(
            data.get(
                "order_id",
                data.get(
                    "OrderID"
                )
            )
        )

        amount = float(
            data.get(
                "amount",
                data.get(
                    "Amount",
                    0
                )
            )
        )

        payment_method = str(
            data.get(
                "payment_method",
                data.get(
                    "PaymentMethod",
                    ""
                )
            )
        ).strip().upper()

        payment_status = str(
            data.get(
                "payment_status",
                data.get(
                    "PaymentStatus",
                    "SUCCESS"
                )
            )
        ).strip().upper()

        transaction_reference = str(
            data.get(
                "transaction_reference",
                data.get(
                    "TransactionReference",
                    ""
                )
            )
        ).strip()

        if amount < 0:

            return error_response(
                "Payment amount cannot be negative."
            )

        if payment_method not in PAYMENT_METHODS:

            return error_response(
                "Invalid payment method."
            )

        if payment_status not in PAYMENT_STATUSES:

            return error_response(
                "Invalid payment status."
            )

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                OrderID
            FROM Orders
            WHERE OrderID = ?
            """,
            (
                order_id,
            )
        )

        if not cursor.fetchone():

            return error_response(
                "Order not found.",
                404
            )

        cursor.execute(
            """
            INSERT INTO Payments
            (
                OrderID,
                Amount,
                PaymentMethod,
                PaymentStatus,
                TransactionReference,
                PaymentDate
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                SYSDATETIME()
            )
            """,
            (
                order_id,
                amount,
                payment_method,
                payment_status,
                transaction_reference
                or None
            )
        )

        cursor.execute(
            """
            SELECT
                CAST(
                    SCOPE_IDENTITY()
                    AS INT
                )
            """
        )

        payment_id = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE Orders
            SET
                PaymentStatus = ?,
                UpdatedAt = SYSDATETIME()
            WHERE OrderID = ?
            """,
            (
                payment_status,
                order_id
            )
        )

        connection.commit()

        return success_response(
            "Payment recorded successfully.",
            201,
            payment_id=payment_id
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to record payment.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# PAYMENT / TRANSACTION PART END
# ============================================================


# ============================================================
# DISH RATINGS PART START
# ============================================================

@app.route(
    "/api/ratings",
    methods=["POST"]
)
def create_rating():

    connection = None
    cursor = None

    try:

        data = get_json_data()

        dish_id = data.get(
            "DishID",
            data.get(
                "dish_id"
            )
        )

        customer_name = str(
            data.get(
                "CustomerName",
                data.get(
                    "customer_name",
                    ""
                )
            )
        ).strip()

        rating = data.get(
            "Rating",
            data.get(
                "rating"
            )
        )

        review = str(
            data.get(
                "Review",
                data.get(
                    "review",
                    ""
                )
            )
            or ""
        ).strip()

        try:

            dish_id = int(
                dish_id
            )

            rating = float(
                rating
            )

        except Exception:

            return error_response(
                "Dish ID and rating must be valid."
            )

        if not customer_name:

            return error_response(
                "Customer name is required."
            )

        if rating < 1 or rating > 5:

            return error_response(
                "Rating must be between 1 and 5."
            )

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                DishID
            FROM Dishes
            WHERE DishID = ?
            """,
            (
                dish_id,
            )
        )

        if not cursor.fetchone():

            return error_response(
                "Dish not found.",
                404
            )

        cursor.execute(
            """
            INSERT INTO DishRatings
            (
                DishID,
                CustomerName,
                Rating,
                Review,
                CreatedAt
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                SYSDATETIME()
            )
            """,
            (
                dish_id,
                customer_name,
                rating,
                review or None
            )
        )

        # ----------------------------------------------------
        # UPDATE AVERAGE DISH RATING
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                AVG(Rating)
            FROM DishRatings
            WHERE DishID = ?
            """,
            (
                dish_id,
            )
        )

        average_rating = (
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            UPDATE Dishes
            SET
                Rating = ?,
                UpdatedAt = SYSDATETIME()
            WHERE DishID = ?
            """,
            (
                average_rating or 0,
                dish_id
            )
        )

        connection.commit()

        return success_response(
            "Rating submitted successfully."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to submit rating.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/ratings/<int:dish_id>",
    methods=["GET"]
)
def get_ratings(
    dish_id
):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                RatingID,
                DishID,
                CustomerName,
                Rating,
                Review,
                CreatedAt
            FROM DishRatings
            WHERE DishID = ?
            ORDER BY CreatedAt DESC
            """,
            (
                dish_id,
            )
        )

        ratings = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Ratings loaded successfully.",
            ratings=ratings
        )

    except Exception as error:

        return error_response(
            "Unable to load ratings.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/ratings",
    methods=["GET"]
)
def get_all_ratings():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                r.RatingID,
                r.DishID,
                d.DishName,
                r.CustomerName,
                r.Rating,
                r.Review,
                r.CreatedAt
            FROM DishRatings r
            INNER JOIN Dishes d
                ON r.DishID = d.DishID
            ORDER BY
                r.CreatedAt DESC
            """
        )

        ratings = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Ratings loaded successfully.",
            ratings=ratings
        )

    except Exception as error:

        return error_response(
            "Unable to load ratings.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# DISH RATINGS PART END
# ============================================================


# ============================================================
# BOOKINGS MANAGEMENT PART START
# ============================================================

@app.route(
    "/api/bookings",
    methods=["GET"]
)
def get_bookings():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                BookingID,
                CustomerName,
                Phone,
                BookingDate,
                BookingTime,
                NumberOfGuests,
                TableNumber,
                Status,
                CreatedAt
            FROM Bookings
            ORDER BY
                BookingDate DESC,
                BookingTime DESC
            """
        )

        bookings = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Bookings loaded successfully.",
            bookings=bookings
        )

    except Exception as error:

        return error_response(
            "Unable to load bookings.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/bookings/<int:booking_id>/status",
    methods=["PUT"]
)
def update_booking_status(
    booking_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        data = get_json_data()

        status = str(
            data.get(
                "status",
                data.get(
                    "Status",
                    ""
                )
            )
        ).strip().upper()

        if status not in BOOKING_STATUSES:

            return error_response(
                "Invalid booking status."
            )

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE Bookings
            SET
                Status = ?
            WHERE BookingID = ?
            """,
            (
                status,
                booking_id
            )
        )

        if cursor.rowcount == 0:

            return error_response(
                "Booking not found.",
                404
            )

        connection.commit()

        return success_response(
            "Booking status updated successfully."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to update booking.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# BOOKINGS MANAGEMENT PART END
# ============================================================


# ============================================================
# WAITER MANAGEMENT PART START
# ============================================================

@app.route(
    "/api/manager/waiters",
    methods=["GET"]
)
def get_waiters():

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

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
            WHERE Role = 'WAITER'
            ORDER BY
                IsActive ASC,
                CreatedAt DESC
            """
        )

        waiters = [
            row_to_dict(
                cursor,
                row
            )
            for row in cursor.fetchall()
        ]

        return success_response(
            "Waiters loaded successfully.",
            waiters=waiters
        )

    except Exception as error:

        return error_response(
            "Unable to load waiters.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/manager/waiters/<int:user_id>/approve",
    methods=["POST"]
)
def approve_waiter(
    user_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE Users
            SET
                IsActive = 1
            WHERE
                UserID = ?
                AND Role = 'WAITER'
            """,
            (
                user_id,
            )
        )

        if cursor.rowcount == 0:

            return error_response(
                "Waiter not found.",
                404
            )

        connection.commit()

        return success_response(
            "Waiter approved successfully."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to approve waiter.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


@app.route(
    "/api/manager/waiters/<int:user_id>/reject",
    methods=["POST"]
)
def reject_waiter(
    user_id
):

    user, error = require_manager()

    if error:

        return error

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE Users
            SET
                IsActive = 0
            WHERE
                UserID = ?
                AND Role = 'WAITER'
            """,
            (
                user_id,
            )
        )

        if cursor.rowcount == 0:

            return error_response(
                "Waiter not found.",
                404
            )

        connection.commit()

        return success_response(
            "Waiter deactivated successfully."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        return error_response(
            "Unable to deactivate waiter.",
            500,
            error=str(error)
        )

    finally:

        close_db(
            connection,
            cursor
        )


# ============================================================
# WAITER MANAGEMENT PART END
# ============================================================


# ============================================================
# ERROR HANDLERS START
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return error_response(
        "Requested resource was not found.",
        404
    )


@app.errorhandler(500)
def internal_server_error(error):

    return error_response(
        "Internal server error.",
        500
    )


# ============================================================
# ERROR HANDLERS END
# ============================================================


# ============================================================
# RUN FLASK APPLICATION START
# ============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "HOTEL RESTAURANT MANAGEMENT SYSTEM"
    )

    print(
        "Flask Backend Server"
    )

    print("=" * 70)

    print(
        "Main:"
    )

    print(
        "http://127.0.0.1:5000/"
    )

    print()

    print(
        "Customer:"
    )

    print(
        "http://127.0.0.1:5000/customer.html"
    )

    print()

    print(
        "Waiter:"
    )

    print(
        "http://127.0.0.1:5000/waiter.html"
    )

    print()

    print(
        "Manager:"
    )

    print(
        "http://127.0.0.1:5000/manager.html"
    )

    print()

    print(
        "Manager phone:"
    )

    print(
        MANAGER_PHONE
    )

    print()

    print(
        "Database test:"
    )

    print(
        "http://127.0.0.1:5000/api/test-db"
    )

    print("=" * 70)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )


# ============================================================
# RUN FLASK APPLICATION END
# ============================================================