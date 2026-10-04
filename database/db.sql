/* ============================================================
   HOTEL RESTAURANT MANAGEMENT SYSTEM
   COMPLETE DATABASE SCRIPT
   SQL SERVER
   ============================================================ */


/* ============================================================
   1. DELETE OLD DATABASE IF IT EXISTS
   ============================================================ */

USE master;
GO

IF DB_ID(N'HotelRestaurantDB') IS NOT NULL
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
   Roles:
      MANAGER
      HEAD
      WAITER
   ============================================================ */

CREATE TABLE Users
(
    UserID INT IDENTITY(1,1) NOT NULL,

    FullName NVARCHAR(100) NOT NULL,

    Phone VARCHAR(15) NOT NULL,

    Email VARCHAR(150) NULL,

    PasswordHash NVARCHAR(255) NOT NULL,

    Role VARCHAR(20) NOT NULL,

    IsActive BIT NOT NULL
        CONSTRAINT DF_Users_IsActive DEFAULT (1),

    CreatedAt DATETIME NOT NULL
        CONSTRAINT DF_Users_CreatedAt DEFAULT (GETDATE()),


    CONSTRAINT PK_Users
        PRIMARY KEY (UserID),

    CONSTRAINT UQ_Users_Phone
        UNIQUE (Phone),

    CONSTRAINT CK_Users_Role
        CHECK
        (
            Role IN
            (
                'MANAGER',
                'HEAD',
                'WAITER'
            )
        )
);
GO


/* ============================================================
   4. DISHES TABLE
   ============================================================ */

CREATE TABLE Dishes
(
    DishID INT IDENTITY(1,1) NOT NULL,

    DishName NVARCHAR(150) NOT NULL,

    Category NVARCHAR(100) NULL,

    Description NVARCHAR(500) NULL,

    Price DECIMAL(10,2) NOT NULL,

    AvailableQuantity INT NOT NULL
        CONSTRAINT DF_Dishes_AvailableQuantity
        DEFAULT (0),

    Rating DECIMAL(2,1) NOT NULL
        CONSTRAINT DF_Dishes_Rating
        DEFAULT (0),

    ImageURL NVARCHAR(1000) NULL,

    IsAvailable BIT NOT NULL
        CONSTRAINT DF_Dishes_IsAvailable
        DEFAULT (1),

    UpdatedAt DATETIME NOT NULL
        CONSTRAINT DF_Dishes_UpdatedAt
        DEFAULT (GETDATE()),


    CONSTRAINT PK_Dishes
        PRIMARY KEY (DishID),

    CONSTRAINT CK_Dishes_Price
        CHECK (Price >= 0),

    CONSTRAINT CK_Dishes_AvailableQuantity
        CHECK (AvailableQuantity >= 0),

    CONSTRAINT CK_Dishes_Rating
        CHECK
        (
            Rating >= 0
            AND Rating <= 5
        )
);
GO


/* ============================================================
   5. ORDERS TABLE
   ============================================================ */

CREATE TABLE Orders
(
    OrderID INT IDENTITY(1,1) NOT NULL,

    CustomerName NVARCHAR(100) NOT NULL,

    MobileNumber VARCHAR(15) NOT NULL,

    TableNumber NVARCHAR(30) NOT NULL,

    TotalAmount DECIMAL(12,2) NOT NULL
        CONSTRAINT DF_Orders_TotalAmount
        DEFAULT (0),

    Status VARCHAR(20) NOT NULL
        CONSTRAINT DF_Orders_Status
        DEFAULT ('Pending'),

    OrderDate DATETIME NOT NULL
        CONSTRAINT DF_Orders_OrderDate
        DEFAULT (GETDATE()),


    CONSTRAINT PK_Orders
        PRIMARY KEY (OrderID),

    CONSTRAINT CK_Orders_TotalAmount
        CHECK (TotalAmount >= 0),

    CONSTRAINT CK_Orders_Status
        CHECK
        (
            Status IN
            (
                'Pending',
                'Preparing',
                'Ready',
                'Completed',
                'Cancelled'
            )
        )
);
GO


/* ============================================================
   6. ORDER DETAILS TABLE
   ============================================================ */

CREATE TABLE OrderDetails
(
    OrderDetailID INT IDENTITY(1,1) NOT NULL,

    OrderID INT NOT NULL,

    DishID INT NOT NULL,

    Quantity INT NOT NULL,

    UnitPrice DECIMAL(10,2) NOT NULL,

    TotalPrice DECIMAL(12,2) NOT NULL,


    CONSTRAINT PK_OrderDetails
        PRIMARY KEY (OrderDetailID),


    CONSTRAINT CK_OrderDetails_Quantity
        CHECK (Quantity > 0),


    CONSTRAINT CK_OrderDetails_UnitPrice
        CHECK (UnitPrice >= 0),


    CONSTRAINT CK_OrderDetails_TotalPrice
        CHECK (TotalPrice >= 0),


    CONSTRAINT FK_OrderDetails_Orders
        FOREIGN KEY (OrderID)
        REFERENCES Orders(OrderID),


    CONSTRAINT FK_OrderDetails_Dishes
        FOREIGN KEY (DishID)
        REFERENCES Dishes(DishID)
);
GO


/* ============================================================
   7. INDEXES
   ============================================================ */

CREATE INDEX IX_Dishes_IsAvailable
ON Dishes
(
    IsAvailable,
    AvailableQuantity
);
GO


CREATE INDEX IX_Dishes_Category
ON Dishes
(
    Category
);
GO


CREATE INDEX IX_Orders_Status
ON Orders
(
    Status
);
GO


CREATE INDEX IX_Orders_OrderDate
ON Orders
(
    OrderDate
);
GO


CREATE INDEX IX_OrderDetails_OrderID
ON OrderDetails
(
    OrderID
);
GO


CREATE INDEX IX_OrderDetails_DishID
ON OrderDetails
(
    DishID
);
GO


/* ============================================================
   8. INITIAL DISH DATA
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
    N'Chicken Biryani',
    N'Main Course',
    N'Aromatic chicken biryani',
    250.00,
    20,
    4.5,
    N'',
    1
),
(
    N'Paneer Butter Masala',
    N'Main Course',
    N'Creamy paneer curry',
    220.00,
    15,
    4.3,
    N'',
    1
),
(
    N'Veg Fried Rice',
    N'Rice',
    N'Fried rice with fresh vegetables',
    180.00,
    20,
    4.2,
    N'',
    1
),
(
    N'Butter Naan',
    N'Bread',
    N'Soft naan with butter',
    60.00,
    30,
    4.4,
    N'',
    1
);
GO


/* ============================================================
   9. VERIFY TABLES
   ============================================================ */

SELECT
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
GO


/* ============================================================
   10. VERIFY DISHES
   ============================================================ */

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
ORDER BY DishID;
GO


/* ============================================================
   11. VERIFY USERS
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
ORDER BY UserID;
GO


/* ============================================================
   12. VERIFY ORDERS
   ============================================================ */

SELECT
    OrderID,
    CustomerName,
    MobileNumber,
    TableNumber,
    TotalAmount,
    Status,
    OrderDate
FROM Orders
ORDER BY OrderID DESC;
GO


/* ============================================================
   13. VERIFY ORDER DETAILS
   ============================================================ */

SELECT
    OrderDetailID,
    OrderID,
    DishID,
    Quantity,
    UnitPrice,
    TotalPrice
FROM OrderDetails
ORDER BY OrderDetailID DESC;
GO