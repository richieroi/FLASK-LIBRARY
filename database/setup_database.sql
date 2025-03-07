-- Library Management System Database Setup
-- ========================================

-- Create Database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'library_system')
BEGIN
    CREATE DATABASE library_system;
END
GO

USE library_system;
GO

-- Create Tables
-- =============

-- Roles Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[roles]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[roles] (
        [RoleID] INT IDENTITY(1,1) PRIMARY KEY,
        [RoleName] NVARCHAR(50) NOT NULL UNIQUE,
        [Description] NVARCHAR(255) NULL,
        [CreatedAt] DATETIME DEFAULT GETDATE(),
        [UpdatedAt] DATETIME DEFAULT GETDATE()
    );
END
GO

-- Users Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[users] (
        [UserID] INT IDENTITY(1,1) PRIMARY KEY,
        [Username] NVARCHAR(50) NOT NULL UNIQUE,
        [PasswordHash] NVARCHAR(255) NOT NULL,
        [Email] NVARCHAR(100) NOT NULL UNIQUE,
        [FirstName] NVARCHAR(50) NULL,
        [LastName] NVARCHAR(50) NULL,
        [IsActive] BIT DEFAULT 1,
        [LastLogin] DATETIME NULL,
        [CreatedAt] DATETIME DEFAULT GETDATE(),
        [UpdatedAt] DATETIME DEFAULT GETDATE()
    );
END
GO

-- User_Roles (Association Table)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[user_roles]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[user_roles] (
        [user_id] INT NOT NULL,
        [role_id] INT NOT NULL,
        PRIMARY KEY ([user_id], [role_id]),
        FOREIGN KEY ([user_id]) REFERENCES [users]([UserID]) ON DELETE CASCADE,
        FOREIGN KEY ([role_id]) REFERENCES [roles]([RoleID]) ON DELETE CASCADE
    );
END
GO

-- Categories Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[categories]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[categories] (
        [CategoryID] INT IDENTITY(1,1) PRIMARY KEY,
        [CategoryName] NVARCHAR(100) NOT NULL,
        [Description] NVARCHAR(255) NULL,
        [CreatedAt] DATETIME DEFAULT GETDATE(),
        [UpdatedAt] DATETIME DEFAULT GETDATE()
    );
END
GO

-- Books Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[books]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[books] (
        [BookID] INT IDENTITY(1,1) PRIMARY KEY,
        [Title] NVARCHAR(255) NOT NULL,
        [Author] NVARCHAR(255) NOT NULL,
        [ISBN] NVARCHAR(20) NULL UNIQUE,
        [PublicationYear] INT NULL,
        [Publisher] NVARCHAR(255) NULL,
        [CategoryID] INT NULL,
        [Status] NVARCHAR(50) DEFAULT 'Available',
        [Description] NVARCHAR(MAX) NULL,
        [CoverImage] NVARCHAR(255) NULL,
        [CreatedAt] DATETIME DEFAULT GETDATE(),
        [UpdatedAt] DATETIME DEFAULT GETDATE(),
        FOREIGN KEY ([CategoryID]) REFERENCES [categories]([CategoryID])
    );
END
GO

-- Members Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[members]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[members] (
        [MemberID] INT IDENTITY(1,1) PRIMARY KEY,
        [FirstName] NVARCHAR(50) NOT NULL,
        [LastName] NVARCHAR(50) NOT NULL,
        [Email] NVARCHAR(100) NOT NULL UNIQUE,
        [Phone] NVARCHAR(20) NULL,
        [Address] NVARCHAR(255) NULL,
        [MembershipDate] DATETIME DEFAULT GETDATE(),
        [MembershipExpiry] DATETIME NULL,
        [Status] NVARCHAR(50) DEFAULT 'Active',
        [UserID] INT NULL,
        [CreatedAt] DATETIME DEFAULT GETDATE(),
        [UpdatedAt] DATETIME DEFAULT GETDATE(),
        FOREIGN KEY ([UserID]) REFERENCES [users]([UserID])
    );
END
GO

-- Loans Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[loans]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[loans] (
        [LoanID] INT IDENTITY(1,1) PRIMARY KEY,
        [BookID] INT NOT NULL,
        [MemberID] INT NOT NULL,
        [LoanDate] DATETIME DEFAULT GETDATE() NOT NULL,
        [DueDate] DATETIME NOT NULL,
        [ReturnDate] DATETIME NULL,
        [Status] NVARCHAR(50) DEFAULT 'Borrowed',
        [FineAmount] FLOAT DEFAULT 0.0,
        [Notes] NVARCHAR(MAX) NULL,
        [CreatedAt] DATETIME DEFAULT GETDATE(),
        [UpdatedAt] DATETIME DEFAULT GETDATE(),
        FOREIGN KEY ([BookID]) REFERENCES [books]([BookID]),
        FOREIGN KEY ([MemberID]) REFERENCES [members]([MemberID])
    );
END
GO

-- Activity Logs Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[activity_logs]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[activity_logs] (
        [LogID] INT IDENTITY(1,1) PRIMARY KEY,
        [UserID] INT NULL,
        [Action] NVARCHAR(50) NOT NULL,
        [TableName] NVARCHAR(50) NULL,
        [RecordID] INT NULL,
        [OldValues] NVARCHAR(MAX) NULL,
        [NewValues] NVARCHAR(MAX) NULL,
        [IPAddress] NVARCHAR(50) NULL,
        [ChangedAt] DATETIME DEFAULT GETDATE(),
        FOREIGN KEY ([UserID]) REFERENCES [users]([UserID]) ON DELETE SET NULL
    );
END
GO
