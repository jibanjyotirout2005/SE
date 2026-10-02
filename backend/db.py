import pyodbc


# =============================================
# DATABASE CONFIGURATION
# =============================================

DB_SERVER = r"JIBANJYOTI\SQLEXPRESS"
DB_DATABASE = "HotelRestaurantDB"
DB_DRIVER = "ODBC Driver 18 for SQL Server"

DB_TRUSTED_CONNECTION = True


# =============================================
# DATABASE CONNECTION
# =============================================

def get_connection():
    """
    Create and return a connection to
    HotelRestaurantDB.
    """

    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        f"Trusted_Connection={'yes' if DB_TRUSTED_CONNECTION else 'no'};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


# =============================================
# DATABASE TEST
# =============================================

def test_connection():
    """
    Test whether the database connection works.
    """

    connection = None

    try:
        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT DB_NAME() AS CurrentDatabase"
        )

        row = cursor.fetchone()

        return {
            "success": True,
            "database": row.CurrentDatabase
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error)
        }

    finally:

        if connection:
            connection.close()