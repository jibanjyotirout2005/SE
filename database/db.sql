CREATE DATABASE HotelRestaurantDB;
GO

USE HotelRestaurantDB;
GO

SELECT DB_NAME() AS CurrentDatabase;

-- =============================================
-- STEP 4: USERS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE Users
(
    UserID INT IDENTITY(1,1) PRIMARY KEY,

    FullName NVARCHAR(100) NOT NULL,

    Phone VARCHAR(15) NOT NULL UNIQUE,

    Email NVARCHAR(150) NOT NULL UNIQUE,

    PasswordHash NVARCHAR(255) NOT NULL,

    Role VARCHAR(20) NOT NULL,

    IsActive BIT NOT NULL DEFAULT 1,

    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT CK_Users_Role
    CHECK (Role IN ('MANAGER', 'HEAD', 'WAITER'))
);
GO

-- =============================================
-- STEP 5: DISHES TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE Dishes
(
    DishID INT IDENTITY(1,1) PRIMARY KEY,

    DishName NVARCHAR(100) NOT NULL,

    Category NVARCHAR(50) NOT NULL,

    Description NVARCHAR(500),

    Price DECIMAL(10,2) NOT NULL,

    AvailableQuantity INT NOT NULL DEFAULT 0,

    Rating DECIMAL(2,1) NOT NULL DEFAULT 0.0,

    ImageURL NVARCHAR(500),

    IsAvailable BIT NOT NULL DEFAULT 1,

    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT CK_Dishes_Price
    CHECK (Price >= 0),

    CONSTRAINT CK_Dishes_Quantity
    CHECK (AvailableQuantity >= 0),

    CONSTRAINT CK_Dishes_Rating
    CHECK (Rating >= 0 AND Rating <= 5)
);
GO

-- =============================================
-- STEP 6: CUSTOMERS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE Customers
(
    CustomerID INT IDENTITY(1,1) PRIMARY KEY,

    CustomerName NVARCHAR(100) NOT NULL,

    Phone VARCHAR(15) NOT NULL,

    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO
-- =============================================
-- STEP 7: ORDERS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE Orders
(
    OrderID INT IDENTITY(1,1) PRIMARY KEY,

    CustomerID INT NOT NULL,

    TableNumber INT NULL,

    TotalAmount DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    Status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    OrderDate DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_Orders_Customers
    FOREIGN KEY (CustomerID)
    REFERENCES Customers(CustomerID),

    CONSTRAINT CK_Orders_TotalAmount
    CHECK (TotalAmount >= 0),

    CONSTRAINT CK_Orders_Status
    CHECK
    (
        Status IN
        (
            'PENDING',
            'CONFIRMED',
            'PREPARING',
            'READY',
            'COMPLETED',
            'CANCELLED'
        )
    )
);
GO
-- =============================================
-- STEP 8: ORDER DETAILS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE OrderDetails
(
    OrderDetailID INT IDENTITY(1,1) PRIMARY KEY,

    OrderID INT NOT NULL,

    DishID INT NOT NULL,

    Quantity INT NOT NULL,

    UnitPrice DECIMAL(10,2) NOT NULL,

    SubTotal AS (Quantity * UnitPrice) PERSISTED,

    CONSTRAINT FK_OrderDetails_Orders
    FOREIGN KEY (OrderID)
    REFERENCES Orders(OrderID),

    CONSTRAINT FK_OrderDetails_Dishes
    FOREIGN KEY (DishID)
    REFERENCES Dishes(DishID),

    CONSTRAINT CK_OrderDetails_Quantity
    CHECK (Quantity > 0),

    CONSTRAINT CK_OrderDetails_UnitPrice
    CHECK (UnitPrice >= 0)
);
GO
-- =============================================
-- STEP 9: ORDER STATUS HISTORY TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE OrderStatusHistory
(
    HistoryID INT IDENTITY(1,1) PRIMARY KEY,

    OrderID INT NOT NULL,

    OldStatus VARCHAR(20) NULL,

    NewStatus VARCHAR(20) NOT NULL,

    ChangedBy INT NULL,

    ChangedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_OrderStatusHistory_Orders
    FOREIGN KEY (OrderID)
    REFERENCES Orders(OrderID),

    CONSTRAINT FK_OrderStatusHistory_Users
    FOREIGN KEY (ChangedBy)
    REFERENCES Users(UserID),

    CONSTRAINT CK_OrderStatusHistory_NewStatus
    CHECK
    (
        NewStatus IN
        (
            'PENDING',
            'CONFIRMED',
            'PREPARING',
            'READY',
            'COMPLETED',
            'CANCELLED'
        )
    )
);
GO
-- =============================================
-- STEP 10: PAYMENTS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE Payments
(
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,

    OrderID INT NOT NULL,

    Amount DECIMAL(10,2) NOT NULL,

    PaymentMethod VARCHAR(20) NOT NULL DEFAULT 'CASH',

    PaymentStatus VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    TransactionReference VARCHAR(100) NULL,

    PaidAt DATETIME2 NULL,

    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_Payments_Orders
    FOREIGN KEY (OrderID)
    REFERENCES Orders(OrderID),

    CONSTRAINT CK_Payments_Amount
    CHECK (Amount >= 0),

    CONSTRAINT CK_Payments_Method
    CHECK
    (
        PaymentMethod IN
        (
            'CASH',
            'UPI',
            'CARD'
        )
    ),

    CONSTRAINT CK_Payments_Status
    CHECK
    (
        PaymentStatus IN
        (
            'PENDING',
            'PAID',
            'FAILED',
            'REFUNDED'
        )
    )
);
GO
-- =============================================
-- STEP 11: DISH RATING HISTORY TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE DishRatingHistory
(
    RatingID INT IDENTITY(1,1) PRIMARY KEY,

    DishID INT NOT NULL,

    CustomerID INT NULL,

    Rating DECIMAL(2,1) NOT NULL,

    Review NVARCHAR(500) NULL,

    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_DishRatingHistory_Dishes
    FOREIGN KEY (DishID)
    REFERENCES Dishes(DishID),

    CONSTRAINT FK_DishRatingHistory_Customers
    FOREIGN KEY (CustomerID)
    REFERENCES Customers(CustomerID),

    CONSTRAINT CK_DishRatingHistory_Rating
    CHECK (Rating >= 1 AND Rating <= 5)
);
GO
-- =============================================
-- STEP 12: BOOKINGS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE Bookings
(
    BookingID INT IDENTITY(1,1) PRIMARY KEY,

    CustomerID INT NOT NULL,

    BookingDate DATE NOT NULL,

    BookingTime TIME NOT NULL,

    NumberOfGuests INT NOT NULL,

    TableNumber INT NULL,

    Status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_Bookings_Customers
    FOREIGN KEY (CustomerID)
    REFERENCES Customers(CustomerID),

    CONSTRAINT CK_Bookings_Guests
    CHECK (NumberOfGuests > 0),

    CONSTRAINT CK_Bookings_Status
    CHECK
    (
        Status IN
        (
            'PENDING',
            'CONFIRMED',
            'COMPLETED',
            'CANCELLED'
        )
    )
);
GO
-- =============================================
-- STEP 13: ORDER ASSIGNMENTS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE OrderAssignments
(
    AssignmentID INT IDENTITY(1,1) PRIMARY KEY,

    OrderID INT NOT NULL,

    UserID INT NOT NULL,

    AssignedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CompletedAt DATETIME2 NULL,

    Status VARCHAR(20) NOT NULL DEFAULT 'ASSIGNED',

    CONSTRAINT FK_OrderAssignments_Orders
    FOREIGN KEY (OrderID)
    REFERENCES Orders(OrderID),

    CONSTRAINT FK_OrderAssignments_Users
    FOREIGN KEY (UserID)
    REFERENCES Users(UserID),

    CONSTRAINT CK_OrderAssignments_Status
    CHECK
    (
        Status IN
        (
            'ASSIGNED',
            'ACCEPTED',
            'COMPLETED',
            'CANCELLED'
        )
    )
);
GO
-- =============================================
-- STEP 14: SYSTEM SETTINGS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE SystemSettings
(
    SettingID INT IDENTITY(1,1) PRIMARY KEY,

    SettingName VARCHAR(100) NOT NULL UNIQUE,

    SettingValue NVARCHAR(500) NULL,

    Description NVARCHAR(500) NULL,

    UpdatedBy INT NULL,

    UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_SystemSettings_Users
    FOREIGN KEY (UpdatedBy)
    REFERENCES Users(UserID)
);
GO

-- =============================================
-- STEP 15: DATABASE INDEXES
-- =============================================

USE HotelRestaurantDB;
GO

-- Users
CREATE INDEX IX_Users_Role
ON Users(Role);
GO

CREATE INDEX IX_Users_IsActive
ON Users(IsActive);
GO

-- Dishes
CREATE INDEX IX_Dishes_Category
ON Dishes(Category);
GO

CREATE INDEX IX_Dishes_IsAvailable
ON Dishes(IsAvailable);
GO

-- Customers
CREATE INDEX IX_Customers_Phone
ON Customers(Phone);
GO

-- Orders
CREATE INDEX IX_Orders_CustomerID
ON Orders(CustomerID);
GO

CREATE INDEX IX_Orders_Status
ON Orders(Status);
GO

CREATE INDEX IX_Orders_OrderDate
ON Orders(OrderDate);
GO

-- Order Details
CREATE INDEX IX_OrderDetails_OrderID
ON OrderDetails(OrderID);
GO

CREATE INDEX IX_OrderDetails_DishID
ON OrderDetails(DishID);
GO

-- Order Status History
CREATE INDEX IX_OrderStatusHistory_OrderID
ON OrderStatusHistory(OrderID);
GO

CREATE INDEX IX_OrderStatusHistory_ChangedBy
ON OrderStatusHistory(ChangedBy);
GO

-- Payments
CREATE INDEX IX_Payments_OrderID
ON Payments(OrderID);
GO

CREATE INDEX IX_Payments_PaymentStatus
ON Payments(PaymentStatus);
GO

-- Dish Ratings
CREATE INDEX IX_DishRatingHistory_DishID
ON DishRatingHistory(DishID);
GO

CREATE INDEX IX_DishRatingHistory_CustomerID
ON DishRatingHistory(CustomerID);
GO

-- Bookings
CREATE INDEX IX_Bookings_CustomerID
ON Bookings(CustomerID);
GO

CREATE INDEX IX_Bookings_BookingDate
ON Bookings(BookingDate);
GO

CREATE INDEX IX_Bookings_Status
ON Bookings(Status);
GO

-- Order Assignments
CREATE INDEX IX_OrderAssignments_OrderID
ON OrderAssignments(OrderID);
GO

CREATE INDEX IX_OrderAssignments_UserID
ON OrderAssignments(UserID);
GO

CREATE INDEX IX_OrderAssignments_Status
ON OrderAssignments(Status);
GO

-- =============================================
-- STEP 16: INITIAL SYSTEM USERS
-- =============================================

USE HotelRestaurantDB;
GO

-- HEAD
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
    'Test Head',
    '9000000001',
    'head@test.com',
    '123456',
    'HEAD',
    1
);
GO

-- MANAGER
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
    'Test Manager',
    '9123456780',
    'manager@test.com',
    '123456',
    'MANAGER',
    1
);
GO

-- WAITER
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
    'Test Waiter',
    '9876543210',
    'waiter@test.com',
    '123456',
    'WAITER',
    1
);
GO









-- =============================================
-- STEP 17: INITIAL RESTAURANT DISHES
-- =============================================

USE HotelRestaurantDB;
GO

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
    'Aromatic basmati rice cooked with tender chicken and traditional spices.',
    250.00,
    20,
    4.5,
    NULL,
    1
),
(
    'Paneer Butter Masala',
    'Main Course',
    'Soft paneer cooked in a rich and creamy tomato gravy.',
    220.00,
    15,
    4.3,
    NULL,
    1
),
(
    'Veg Fried Rice',
    'Rice',
    'Fried basmati rice prepared with fresh vegetables and mild spices.',
    180.00,
    25,
    4.2,
    NULL,
    1
),
(
    'Chicken Tikka',
    'Starter',
    'Grilled marinated chicken pieces served with fresh salad.',
    280.00,
    12,
    4.6,
    NULL,
    1
),
(
    'Masala Dosa',
    'South Indian',
    'Crispy dosa served with potato masala, sambar and chutney.',
    120.00,
    30,
    4.4,
    NULL,
    1
),
(
    'Veg Manchurian',
    'Starter',
    'Crispy vegetable balls tossed in a flavorful Manchurian sauce.',
    160.00,
    18,
    4.1,
    NULL,
    1
),
(
    'Butter Naan',
    'Bread',
    'Soft Indian flatbread topped with butter.',
    50.00,
    40,
    4.3,
    NULL,
    1
),
(
    'Gulab Jamun',
    'Dessert',
    'Soft milk-solid dumplings served in warm sugar syrup.',
    90.00,
    20,
    4.5,
    NULL,
    1
);
GO
-- =============================================
-- STEP 18: INITIAL CUSTOMERS
-- =============================================

USE HotelRestaurantDB;
GO

INSERT INTO Customers
(
    CustomerName,
    Phone
)
VALUES
(
    'Rahul Sharma',
    '9000000002'
),
(
    'Priya Das',
    '9000000003'
),
(
    'Amit Kumar',
    '9000000004'
),
(
    'Sneha Patra',
    '9000000005'
);
GO
-- =============================================
-- STEP 19: INITIAL BOOKINGS
-- =============================================

USE HotelRestaurantDB;
GO

INSERT INTO Bookings
(
    CustomerID,
    BookingDate,
    BookingTime,
    NumberOfGuests,
    TableNumber,
    Status
)
VALUES
(
    1,
    CAST(GETDATE() AS DATE),
    '19:00',
    2,
    1,
    'CONFIRMED'
),
(
    2,
    DATEADD(DAY, 1, CAST(GETDATE() AS DATE)),
    '20:00',
    4,
    3,
    'CONFIRMED'
),
(
    3,
    DATEADD(DAY, 2, CAST(GETDATE() AS DATE)),
    '18:30',
    3,
    5,
    'PENDING'
);
GO
-- =============================================
-- STEP 20: INITIAL ORDERS
-- =============================================

USE HotelRestaurantDB;
GO

INSERT INTO Orders
(
    CustomerID,
    TableNumber,
    TotalAmount,
    Status
)
VALUES
(
    1,
    1,
    720.00,
    'CONFIRMED'
),
(
    2,
    3,
    430.00,
    'PREPARING'
),
(
    3,
    5,
    250.00,
    'COMPLETED'
);
GO
-- =============================================
-- STEP 21: INITIAL ORDER DETAILS
-- =============================================

USE HotelRestaurantDB;
GO

-- Order 1
-- Chicken Biryani × 2 = ₹500
-- Paneer Butter Masala × 1 = ₹220
INSERT INTO OrderDetails
(
    OrderID,
    DishID,
    Quantity,
    UnitPrice
)
VALUES
(
    1,
    1,
    2,
    250.00
),
(
    1,
    2,
    1,
    220.00
);
GO


-- Order 2
-- Veg Fried Rice × 1 = ₹180
-- Chicken Tikka × 1 = ₹280
INSERT INTO OrderDetails
(
    OrderID,
    DishID,
    Quantity,
    UnitPrice
)
VALUES
(
    2,
    3,
    1,
    180.00
),
(
    2,
    4,
    1,
    250.00
);
GO


-- Order 3
-- Chicken Biryani × 1 = ₹250
INSERT INTO OrderDetails
(
    OrderID,
    DishID,
    Quantity,
    UnitPrice
)
VALUES
(
    3,
    1,
    1,
    250.00
);
GO
-- =============================================
-- STEP 22: INITIAL ORDER STATUS HISTORY
-- =============================================

USE HotelRestaurantDB;
GO

-- Order 1
INSERT INTO OrderStatusHistory
(
    OrderID,
    OldStatus,
    NewStatus,
    ChangedBy
)
VALUES
(
    1,
    NULL,
    'PENDING',
    2
),
(
    1,
    'PENDING',
    'CONFIRMED',
    2
);
GO


-- Order 2
INSERT INTO OrderStatusHistory
(
    OrderID,
    OldStatus,
    NewStatus,
    ChangedBy
)
VALUES
(
    2,
    NULL,
    'PENDING',
    2
),
(
    2,
    'PENDING',
    'CONFIRMED',
    2
),
(
    2,
    'CONFIRMED',
    'PREPARING',
    2
);
GO


-- Order 3
INSERT INTO OrderStatusHistory
(
    OrderID,
    OldStatus,
    NewStatus,
    ChangedBy
)
VALUES
(
    3,
    NULL,
    'PENDING',
    2
),
(
    3,
    'PENDING',
    'CONFIRMED',
    2
),
(
    3,
    'CONFIRMED',
    'COMPLETED',
    2
);
GO
-- =============================================
-- STEP 23: INITIAL PAYMENTS
-- =============================================

USE HotelRestaurantDB;
GO

INSERT INTO Payments
(
    OrderID,
    Amount,
    PaymentMethod,
    PaymentStatus
)
VALUES
(
    1,
    720.00,
    'CASH',
    'PAID'
),
(
    2,
    430.00,
    'UPI',
    'PENDING'
),
(
    3,
    250.00,
    'CARD',
    'PAID'
);
GO
-- =============================================
-- STEP 24: INITIAL DISH RATINGS
-- =============================================
-- =============================================
-- STEP 24A: CREATE DISH RATINGS TABLE
-- =============================================

USE HotelRestaurantDB;
GO

CREATE TABLE DishRatings
(
    RatingID INT IDENTITY(1,1) PRIMARY KEY,

    DishID INT NOT NULL,

    CustomerID INT NOT NULL,

    Rating INT NOT NULL,

    Review NVARCHAR(500) NULL,

    CreatedAt DATETIME2 DEFAULT SYSDATETIME(),

    CONSTRAINT FK_DishRatings_Dish
        FOREIGN KEY (DishID)
        REFERENCES Dishes(DishID),

    CONSTRAINT FK_DishRatings_Customer
        FOREIGN KEY (CustomerID)
        REFERENCES Customers(CustomerID),

    CONSTRAINT CK_DishRatings_Rating
        CHECK (Rating BETWEEN 1 AND 5)
);
GO
USE HotelRestaurantDB;
GO

INSERT INTO DishRatings
(
    DishID,
    CustomerID,
    Rating,
    Review
)
VALUES
(
    1,
    1,
    5,
    'Very tasty and fresh.'
),
(
    2,
    2,
    4,
    'Good taste and quality.'
),
(
    3,
    3,
    5,
    'Excellent fried rice.'
),
(
    4,
    4,
    4,
    'Good dish and reasonable price.'
);
GO



-- =============================================
-- STEP 25: BOOKING VERIFICATION
-- =============================================

USE HotelRestaurantDB;
GO

SELECT
    b.BookingID,
    c.CustomerName,
    c.Phone,
    b.BookingDate,
    b.BookingTime,
    b.NumberOfGuests,
    b.TableNumber,
    b.Status
FROM Bookings b
INNER JOIN Customers c
    ON b.CustomerID = c.CustomerID
ORDER BY b.BookingID;
GO
-- =============================================
-- STEP 26: DISH INVENTORY VERIFICATION
-- =============================================

USE HotelRestaurantDB;
GO

SELECT
    DishID,
    DishName,
    Category,
    Price,
    AvailableQuantity,
    Rating,
    IsAvailable
FROM Dishes
ORDER BY DishID;
GO
-- =============================================
-- STEP 27: USER AND ROLE VERIFICATION
-- =============================================

USE HotelRestaurantDB;
GO

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

SELECT
    Role,
    COUNT(*) AS TotalUsers
FROM Users
GROUP BY Role
ORDER BY Role;
GO
-- =============================================
-- STEP 28: ORDER TOTAL VERIFICATION
-- =============================================

USE HotelRestaurantDB;
GO

SELECT
    o.OrderID,
    c.CustomerName,
    o.TotalAmount AS StoredTotal,
    SUM(
        od.Quantity * od.UnitPrice
    ) AS CalculatedTotal,
    CASE
        WHEN o.TotalAmount =
             SUM(od.Quantity * od.UnitPrice)
        THEN 'MATCH'
        ELSE 'MISMATCH'
    END AS TotalCheck
FROM Orders o
INNER JOIN Customers c
    ON o.CustomerID = c.CustomerID
INNER JOIN OrderDetails od
    ON o.OrderID = od.OrderID
GROUP BY
    o.OrderID,
    c.CustomerName,
    o.TotalAmount
ORDER BY o.OrderID;
GO
-- =============================================
-- STEP 29: CUSTOMER ORDER SUMMARY
-- =============================================

USE HotelRestaurantDB;
GO

SELECT
    c.CustomerID,
    c.CustomerName,
    c.Phone,
    COUNT(o.OrderID) AS TotalOrders,
    ISNULL(SUM(o.TotalAmount), 0) AS TotalSpent
FROM Customers c
LEFT JOIN Orders o
    ON c.CustomerID = o.CustomerID
GROUP BY
    c.CustomerID,
    c.CustomerName,
    c.Phone
ORDER BY c.CustomerID;
GO
-- =============================================
-- STEP 30: HEAD DASHBOARD SUMMARY
-- =============================================

USE HotelRestaurantDB;
GO

SELECT
    (SELECT COUNT(*)
     FROM Dishes) AS TotalDishes,

    (SELECT COUNT(*)
     FROM Dishes
     WHERE IsAvailable = 1) AS AvailableDishes,

    (SELECT COUNT(*)
     FROM Orders) AS TotalOrders,

    (SELECT COUNT(DISTINCT CustomerID)
     FROM Orders) AS TotalCustomers,

    (SELECT COUNT(*)
     FROM Users) AS TotalUsers;
GO
-- =============================================
-- STEP 31: FINAL DATABASE INTEGRITY CHECK
-- =============================================

USE HotelRestaurantDB;
GO

PRINT '=============================================';
PRINT 'HOTEL RESTAURANT DATABASE CHECK';
PRINT '============================================';

SELECT
    'Users' AS TableName,
    COUNT(*) AS RecordCount
FROM Users

UNION ALL

SELECT
    'Customers',
    COUNT(*)
FROM Customers

UNION ALL

SELECT
    'Dishes',
    COUNT(*)
FROM Dishes

UNION ALL

SELECT
    'Bookings',
    COUNT(*)
FROM Bookings

UNION ALL

SELECT
    'Orders',
    COUNT(*)
FROM Orders

UNION ALL

SELECT
    'OrderDetails',
    COUNT(*)
FROM OrderDetails

UNION ALL

SELECT
    'OrderStatusHistory',
    COUNT(*)
FROM OrderStatusHistory

UNION ALL

SELECT
    'Payments',
    COUNT(*)
FROM Payments

UNION ALL

SELECT
    'DishRatings',
    COUNT(*)
FROM DishRatings;

PRINT '=============================================';
PRINT 'DATABASE CHECK COMPLETED';
PRINT '=============================================';
GO



USE HotelRestaurantDB;
GO

SELECT
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
GO



USE HotelRestaurantDB;
GO

UPDATE OrderDetails
SET UnitPrice = 280.00
WHERE OrderID = 2
  AND DishID = 4;

UPDATE Orders
SET TotalAmount = 460.00
WHERE OrderID = 2;
GO

SELECT
    o.OrderID,
    c.CustomerName,
    o.TotalAmount AS StoredTotal,
    SUM(od.Quantity * od.UnitPrice) AS CalculatedTotal,
    CASE
        WHEN o.TotalAmount = SUM(od.Quantity * od.UnitPrice)
        THEN 'MATCH'
        ELSE 'MISMATCH'
    END AS TotalCheck
FROM Orders o
INNER JOIN Customers c
    ON o.CustomerID = c.CustomerID
INNER JOIN OrderDetails od
    ON o.OrderID = od.OrderID
GROUP BY
    o.OrderID,
    c.CustomerName,
    o.TotalAmount
ORDER BY o.OrderID;
GO