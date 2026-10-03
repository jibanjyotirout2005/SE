/* ============================================================
   HOTEL RESTAURANT MANAGEMENT SYSTEM
   COMPLETE DATABASE
   ROLES:
       CUSTOMER
       WAITER
       MANAGER

   NO HEAD OF HOTEL

   MANAGER PHONE:
       8260611800
   ============================================================ */


USE master;
GO


/* ============================================================
   1. DELETE OLD DATABASE
   ============================================================ */

IF DB_ID('HotelRestaurantDB') IS NOT NULL
BEGIN
    ALTER DATABASE HotelRestaurantDB
    SET SINGLE_USER
    WITH ROLLBACK IMMEDIATE;

    DROP DATABASE HotelRestaurantDB;
END
GO


/* ============================================================
   2. CREATE DATABASE
   ============================================================ */

CREATE DATABASE HotelRestaurantDB;
GO


USE HotelRestaurantDB;
GO


/* ============================================================
   3. USERS TABLE
   ============================================================ */

CREATE TABLE Users
(
    UserID INT IDENTITY(1,1)
        CONSTRAINT PK_Users PRIMARY KEY,

    FullName NVARCHAR(100) NOT NULL,

    Phone VARCHAR(10) NOT NULL
        CONSTRAINT UQ_Users_Phone UNIQUE,

    Email NVARCHAR(150) NULL
        CONSTRAINT UQ_Users_Email UNIQUE,

    PasswordHash NVARCHAR(255) NULL,

    Role VARCHAR(20) NOT NULL
        CONSTRAINT CK_Users_Role
        CHECK
        (
            Role IN
            (
                'CUSTOMER',
                'WAITER',
                'MANAGER'
            )
        ),

    IsActive BIT NOT NULL
        CONSTRAINT DF_Users_IsActive
        DEFAULT 0,

    CreatedAt DATETIME NOT NULL
        CONSTRAINT DF_Users_CreatedAt
        DEFAULT GETDATE(),

    UpdatedAt DATETIME NULL
);
GO


/* ============================================================
   4. MANAGER ACCOUNT
   ============================================================ */

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
    'Jiban Rout',
    '8260611800',
    'manager@hotelrestaurant.com',
    '8260611800',
    'MANAGER',
    1
);
GO


/* ============================================================
   5. CUSTOMERS TABLE
   ============================================================ */

CREATE TABLE Customers
(
    CustomerID INT IDENTITY(1,1)
        CONSTRAINT PK_Customers PRIMARY KEY,

    CustomerName NVARCHAR(100) NOT NULL,

    Phone VARCHAR(10) NOT NULL
        CONSTRAINT UQ_Customers_Phone UNIQUE,

    CreatedAt DATETIME NOT NULL
        CONSTRAINT DF_Customers_CreatedAt
        DEFAULT GETDATE(),

    UpdatedAt DATETIME NULL
);
GO


/* ============================================================
   6. DISHES TABLE
   ============================================================ */

CREATE TABLE Dishes
(
    DishID INT IDENTITY(1,1)
        CONSTRAINT PK_Dishes PRIMARY KEY,

    DishName NVARCHAR(150) NOT NULL,

    Category NVARCHAR(100) NOT NULL,

    Description NVARCHAR(500) NULL,

    Price DECIMAL(10,2) NOT NULL
        CONSTRAINT CK_Dishes_Price
        CHECK (Price >= 0),

    AvailableQuantity INT NOT NULL
        CONSTRAINT CK_Dishes_Quantity
        CHECK (AvailableQuantity >= 0),

    Rating DECIMAL(3,2) NOT NULL
        CONSTRAINT DF_Dishes_Rating
        DEFAULT 0
        CONSTRAINT CK_Dishes_Rating
        CHECK (Rating >= 0 AND Rating <= 5),

    ImageURL NVARCHAR(500) NULL,

    IsAvailable BIT NOT NULL
        CONSTRAINT DF_Dishes_IsAvailable
        DEFAULT 1,

    CreatedAt DATETIME NOT NULL
        CONSTRAINT DF_Dishes_CreatedAt
        DEFAULT GETDATE(),

    UpdatedAt DATETIME NULL
);
GO


/* ============================================================
   7. ORDERS TABLE
   ============================================================ */

CREATE TABLE Orders
(
    OrderID INT IDENTITY(1,1)
        CONSTRAINT PK_Orders PRIMARY KEY,

    CustomerID INT NOT NULL,

    TableNumber INT NOT NULL
        CONSTRAINT CK_Orders_TableNumber
        CHECK (TableNumber > 0),

    TotalAmount DECIMAL(12,2) NOT NULL
        CONSTRAINT CK_Orders_TotalAmount
        CHECK (TotalAmount >= 0),

    OrderStatus VARCHAR(20) NOT NULL
        CONSTRAINT DF_Orders_OrderStatus
        DEFAULT 'Pending',

    OrderSource VARCHAR(20) NOT NULL
        CONSTRAINT DF_Orders_OrderSource
        DEFAULT 'CUSTOMER',

    WaiterID INT NULL,

    OrderDate DATETIME NOT NULL
        CONSTRAINT DF_Orders_OrderDate
        DEFAULT GETDATE(),

    UpdatedAt DATETIME NULL,

    CONSTRAINT CK_Orders_Status
    CHECK
    (
        OrderStatus IN
        (
            'Pending',
            'Preparing',
            'Ready',
            'Completed',
            'Cancelled'
        )
    ),

    CONSTRAINT CK_Orders_Source
    CHECK
    (
        OrderSource IN
        (
            'CUSTOMER',
            'WAITER'
        )
    )
);
GO


/* ============================================================
   8. ORDER DETAILS TABLE
   ============================================================ */

CREATE TABLE OrderDetails
(
    OrderDetailID INT IDENTITY(1,1)
        CONSTRAINT PK_OrderDetails PRIMARY KEY,

    OrderID INT NOT NULL,

    DishID INT NOT NULL,

    Quantity INT NOT NULL
        CONSTRAINT CK_OrderDetails_Quantity
        CHECK (Quantity > 0),

    UnitPrice DECIMAL(10,2) NOT NULL
        CONSTRAINT CK_OrderDetails_UnitPrice
        CHECK (UnitPrice >= 0),

    TotalPrice AS
    (
        Quantity * UnitPrice
    ) PERSISTED
);
GO


/* ============================================================
   9. FOREIGN KEYS
   ============================================================ */

ALTER TABLE Orders
ADD CONSTRAINT FK_Orders_Customers
FOREIGN KEY (CustomerID)
REFERENCES Customers(CustomerID);
GO


ALTER TABLE Orders
ADD CONSTRAINT FK_Orders_Waiter
FOREIGN KEY (WaiterID)
REFERENCES Users(UserID);
GO


ALTER TABLE OrderDetails
ADD CONSTRAINT FK_OrderDetails_Orders
FOREIGN KEY (OrderID)
REFERENCES Orders(OrderID);
GO


ALTER TABLE OrderDetails
ADD CONSTRAINT FK_OrderDetails_Dishes
FOREIGN KEY (DishID)
REFERENCES Dishes(DishID);
GO


/* ============================================================
   10. INDEXES
   ============================================================ */

CREATE INDEX IX_Orders_CustomerID
ON Orders(CustomerID);
GO


CREATE INDEX IX_Orders_WaiterID
ON Orders(WaiterID);
GO


CREATE INDEX IX_Orders_Status
ON Orders(OrderStatus);
GO


CREATE INDEX IX_OrderDetails_OrderID
ON OrderDetails(OrderID);
GO


CREATE INDEX IX_OrderDetails_DishID
ON OrderDetails(DishID);
GO


/* ============================================================
   11. SAMPLE DISHES
   ============================================================ */

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
VALUES

(
    'Chicken Biryani',
    'Main Course',
    'Aromatic basmati rice cooked with chicken and traditional spices.',
    250.00,
    20,
    4.50,
    'https://images.unsplash.com/photo-1563379091339-03246963d51a',
    1
),

(
    'Paneer Butter Masala',
    'Main Course',
    'Soft paneer cooked in a rich and creamy tomato gravy.',
    220.00,
    15,
    4.30,
    'https://images.unsplash.com/photo-1631452180519-c014fe946bc7',
    1
),

(
    'Veg Fried Rice',
    'Rice',
    'Fried rice prepared with fresh vegetables and aromatic seasoning.',
    180.00,
    20,
    4.20,
    'https://images.unsplash.com/photo-1603133872878-684f208fb84b',
    1
),

(
    'Chicken Tikka',
    'Starter',
    'Grilled chicken pieces marinated with Indian spices.',
    280.00,
    12,
    4.60,
    'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0',
    1
),

(
    'Masala Dosa',
    'South Indian',
    'Crispy dosa served with potato masala, sambar and chutney.',
    120.00,
    25,
    4.40,
    'https://images.unsplash.com/photo-1668236543090-82eba5ee5976',
    1
),

(
    'Veg Manchurian',
    'Chinese',
    'Crispy vegetable balls served with spicy Manchurian sauce.',
    160.00,
    18,
    4.10,
    'https://images.unsplash.com/photo-1625398407796-82650a8c135f',
    1
),

(
    'Butter Naan',
    'Bread',
    'Soft Indian naan topped with butter.',
    50.00,
    40,
    4.50,
    'https://images.unsplash.com/photo-1601050690597-df0568f70950',
    1
),

(
    'Gulab Jamun',
    'Dessert',
    'Soft milk-solid dumplings served in sweet sugar syrup.',
    80.00,
    30,
    4.70,
    'https://images.unsplash.com/photo-1666190094765-2c1c5b5e5c8e',
    1
);
GO


/* ============================================================
   12. AUTOMATIC AVAILABILITY TRIGGER
   ============================================================ */

CREATE TRIGGER TR_Dishes_Availability
ON Dishes
AFTER INSERT, UPDATE
AS
BEGIN

    SET NOCOUNT ON;

    UPDATE Dishes
    SET
        IsAvailable =
            CASE
                WHEN AvailableQuantity > 0
                THEN 1
                ELSE 0
            END,

        UpdatedAt = GETDATE()

    WHERE DishID IN
    (
        SELECT DishID
        FROM inserted
    );

END;
GO


/* ============================================================
   13. VERIFY MANAGER
   ============================================================ */

SELECT
    UserID,
    FullName,
    Phone,
    Email,
    Role,
    IsActive,
    CreatedAt
FROM Users
WHERE Phone = '8260611800';
GO


/* ============================================================
   14. VERIFY DISHES
   ============================================================ */

SELECT
    DishID,
    DishName,
    Category,
    Price,
    AvailableQuantity,
    Rating,
    ImageURL,
    IsAvailable
FROM Dishes
ORDER BY DishID;
GO


/* ============================================================
   15. VERIFY TABLES
   ============================================================ */

SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
GO