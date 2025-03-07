-- Library Management System Triggers, Functions, and Stored Procedures
-- ==================================================================

USE library_system;
GO

-- =============================================
-- TRIGGERS
-- =============================================

-- Trigger to update book status when loaned
IF OBJECT_ID('trg_BookLoanStatus', 'TR') IS NOT NULL
    DROP TRIGGER trg_BookLoanStatus;
GO

CREATE TRIGGER trg_BookLoanStatus
ON loans
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE books
    SET Status = 'Borrowed', UpdatedAt = GETDATE()
    FROM books
    INNER JOIN inserted ON books.BookID = inserted.BookID
    WHERE inserted.Status = 'Borrowed';
END;
GO

-- Trigger to update book status when returned
IF OBJECT_ID('trg_BookReturnStatus', 'TR') IS NOT NULL
    DROP TRIGGER trg_BookReturnStatus;
GO

CREATE TRIGGER trg_BookReturnStatus
ON loans
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    IF UPDATE(Status)
    BEGIN
        UPDATE books
        SET Status = 'Available', UpdatedAt = GETDATE()
        FROM books
        INNER JOIN inserted ON books.BookID = inserted.BookID
        WHERE inserted.Status = 'Returned';
    END
END;
GO

-- Trigger to check for overdue books daily
IF OBJECT_ID('trg_CheckOverdueBooks', 'TR') IS NOT NULL
    DROP TRIGGER trg_CheckOverdueBooks;
GO

CREATE TRIGGER trg_CheckOverdueBooks
ON loans
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Update loan status to 'Overdue' if due date has passed
    UPDATE loans
    SET Status = 'Overdue', UpdatedAt = GETDATE()
    WHERE Status = 'Borrowed' 
    AND DueDate < GETDATE();
END;
GO

-- Trigger to log changes in books table
IF OBJECT_ID('trg_LogBookChanges', 'TR') IS NOT NULL
    DROP TRIGGER trg_LogBookChanges;
GO

CREATE TRIGGER trg_LogBookChanges
ON books
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @Action NVARCHAR(10);
    DECLARE @UserID INT;
    
    -- Get current user ID from session context if available
    SET @UserID = CONVERT(INT, SESSION_CONTEXT(N'UserID'));
    
    -- Determine the action
    IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted)
    BEGIN
        SET @Action = 'UPDATE';
        
        INSERT INTO activity_logs (UserID, Action, TableName, RecordID, OldValues, NewValues)
        SELECT @UserID, @Action, 'books', i.BookID,
               (SELECT d.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
               (SELECT i.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
        FROM inserted i
        JOIN deleted d ON i.BookID = d.BookID;
    END
    ELSE IF EXISTS (SELECT * FROM inserted)
    BEGIN
        SET @Action = 'INSERT';
        
        INSERT INTO activity_logs (UserID, Action, TableName, RecordID, NewValues)
        SELECT @UserID, @Action, 'books', BookID, 
               (SELECT * FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
        FROM inserted;
    END
    ELSE IF EXISTS (SELECT * FROM deleted)
    BEGIN
        SET @Action = 'DELETE';
        
        INSERT INTO activity_logs (UserID, Action, TableName, RecordID, OldValues)
        SELECT @UserID, @Action, 'books', BookID,
               (SELECT * FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
        FROM deleted;
    END
END;
GO

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function to calculate overdue days
IF OBJECT_ID('fn_CalculateOverdueDays', 'FN') IS NOT NULL
    DROP FUNCTION fn_CalculateOverdueDays;
GO

CREATE FUNCTION fn_CalculateOverdueDays (@LoanID INT)
RETURNS INT
AS
BEGIN
    DECLARE @OverdueDays INT;
    DECLARE @DueDate DATETIME;
    DECLARE @ReturnDate DATETIME;
    DECLARE @CurrentDate DATETIME;
    
    SELECT @DueDate = DueDate, @ReturnDate = ReturnDate
    FROM loans
    WHERE LoanID = @LoanID;
    
    SET @CurrentDate = GETDATE();
    
    -- If book has been returned, calculate overdue days until return date
    IF @ReturnDate IS NOT NULL
    BEGIN
        IF @ReturnDate > @DueDate
            SET @OverdueDays = DATEDIFF(DAY, @DueDate, @ReturnDate);
        ELSE
            SET @OverdueDays = 0;
    END
    -- If book not returned and past due date, calculate overdue days until now
    ELSE IF @CurrentDate > @DueDate
    BEGIN
        SET @OverdueDays = DATEDIFF(DAY, @DueDate, @CurrentDate);
    END
    -- Not overdue
    ELSE
    BEGIN
        SET @OverdueDays = 0;
    END
    
    RETURN @OverdueDays;
END;
GO

-- Function to calculate fine based on overdue days
IF OBJECT_ID('fn_CalculateFine', 'FN') IS NOT NULL
    DROP FUNCTION fn_CalculateFine;
GO

CREATE FUNCTION fn_CalculateFine (@LoanID INT)
RETURNS DECIMAL(10,2)
AS
BEGIN
    DECLARE @OverdueDays INT;
    DECLARE @FineAmount DECIMAL(10,2);
    DECLARE @DailyRate DECIMAL(10,2);
    
    -- Default daily fine rate
    SET @DailyRate = 0.50; -- 50 cents per day
    
    -- Get overdue days
    SET @OverdueDays = dbo.fn_CalculateOverdueDays(@LoanID);
    
    -- Calculate fine
    IF @OverdueDays > 0
    BEGIN
        -- Progressive fine calculation
        IF @OverdueDays <= 7
            SET @FineAmount = @OverdueDays * @DailyRate;
        ELSE IF @OverdueDays <= 14
            SET @FineAmount = 7 * @DailyRate + (@OverdueDays - 7) * @DailyRate * 1.5;
        ELSE
            SET @FineAmount = 7 * @DailyRate + 7 * @DailyRate * 1.5 + (@OverdueDays - 14) * @DailyRate * 2;
            
        -- Cap fine at maximum of $30
        IF @FineAmount > 30.00
            SET @FineAmount = 30.00;
    END
    ELSE
    BEGIN
        SET @FineAmount = 0.00;
    END
    
    RETURN @FineAmount;
END;
GO

-- Function to check member eligibility for new loans
IF OBJECT_ID('fn_CheckMemberEligibility', 'FN') IS NOT NULL
    DROP FUNCTION fn_CheckMemberEligibility;
GO

CREATE FUNCTION fn_CheckMemberEligibility (@MemberID INT)
RETURNS BIT
AS
BEGIN
    DECLARE @IsEligible BIT = 1;  -- Default to eligible
    DECLARE @CurrentLoans INT;
    DECLARE @OverdueLoans INT;
    DECLARE @MembershipExpired BIT;
    DECLARE @MembershipExpiry DATETIME;
    DECLARE @CurrentDate DATETIME = GETDATE();
    DECLARE @UnpaidFines DECIMAL(10,2);
    
    -- Check member status
    SELECT @MembershipExpiry = MembershipExpiry
    FROM members
    WHERE MemberID = @MemberID;
    
    IF @MembershipExpiry IS NOT NULL AND @MembershipExpiry < @CurrentDate
    BEGIN
        SET @MembershipExpired = 1;
    END
    ELSE
    BEGIN
        SET @MembershipExpired = 0;
    END
    
    -- Count current loans
    SELECT @CurrentLoans = COUNT(*)
    FROM loans
    WHERE MemberID = @MemberID AND Status = 'Borrowed';
    
    -- Count overdue loans
    SELECT @OverdueLoans = COUNT(*)
    FROM loans
    WHERE MemberID = @MemberID AND Status = 'Overdue';
    
    -- Calculate unpaid fines
    SELECT @UnpaidFines = SUM(FineAmount)
    FROM loans
    WHERE MemberID = @MemberID AND FineAmount > 0 AND Status != 'Returned';
    
    -- Set to 0 if null
    SET @UnpaidFines = ISNULL(@UnpaidFines, 0);
    
    -- Check eligibility
    IF @MembershipExpired = 1 OR @CurrentLoans >= 5 OR @OverdueLoans > 0 OR @UnpaidFines >= 10.00
    BEGIN
        SET @IsEligible = 0;
    END
    
    RETURN @IsEligible;
END;
GO

-- =============================================
-- STORED PROCEDURES
-- =============================================

-- Procedure to issue a book to a member
IF OBJECT_ID('sp_IssueBook', 'P') IS NOT NULL
    DROP PROCEDURE sp_IssueBook;
GO

CREATE PROCEDURE sp_IssueBook
    @BookID INT,
    @MemberID INT,
    @DueDate DATETIME,
    @UserID INT,
    @Success BIT OUTPUT,
    @Message NVARCHAR(255) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @BookAvailable BIT;
    DECLARE @MemberEligible BIT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Check if book is available
        SELECT @BookAvailable = CASE WHEN Status = 'Available' THEN 1 ELSE 0 END
        FROM books
        WHERE BookID = @BookID;
        
        IF @BookAvailable = 0
        BEGIN
            SET @Success = 0;
            SET @Message = 'Book is not available for loan';
            ROLLBACK;
            RETURN;
        END
        
        -- Check if member is eligible
        SET @MemberEligible = dbo.fn_CheckMemberEligibility(@MemberID);
        
        IF @MemberEligible = 0
        BEGIN
            SET @Success = 0;
            SET @Message = 'Member is not eligible for new loans';
            ROLLBACK;
            RETURN;
        END
        
        -- Create loan record
        INSERT INTO loans (BookID, MemberID, LoanDate, DueDate, Status)
        VALUES (@BookID, @MemberID, GETDATE(), @DueDate, 'Borrowed');
        
        -- Book status will be updated by trigger
        
        -- Log the action
        INSERT INTO activity_logs (UserID, Action, TableName, RecordID, NewValues)
        VALUES (@UserID, 'LOAN', 'loans', SCOPE_IDENTITY(), 
                (SELECT TOP 1 * FROM loans WHERE LoanID = SCOPE_IDENTITY() FOR JSON PATH, WITHOUT_ARRAY_WRAPPER));
        
        COMMIT;
        SET @Success = 1;
        SET @Message = 'Book issued successfully';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK;
        
        SET @Success = 0;
        SET @Message = ERROR_MESSAGE();
        
        -- Log the error
        INSERT INTO activity_logs (UserID, Action, TableName, NewValues)
        VALUES (@UserID, 'ERROR', 'loans', 
                JSON_MODIFY('{}', '$.Error', ERROR_MESSAGE()));
    END CATCH
END;
GO

-- Procedure to return a book
IF OBJECT_ID('sp_ReturnBook', 'P') IS NOT NULL
    DROP PROCEDURE sp_ReturnBook;
GO

CREATE PROCEDURE sp_ReturnBook
    @BookID INT,
    @FineAmount DECIMAL(10,2) = NULL,
    @Notes NVARCHAR(MAX) = NULL,
    @UserID INT,
    @Success BIT OUTPUT,
    @Message NVARCHAR(255) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @LoanID INT;
    DECLARE @ActualFine DECIMAL(10,2);
    DECLARE @CurrentStatus NVARCHAR(50);
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Find the active loan record for this book
        SELECT TOP 1 @LoanID = LoanID, @CurrentStatus = Status
        FROM loans
        WHERE BookID = @BookID AND (Status = 'Borrowed' OR Status = 'Overdue')
        ORDER BY LoanDate DESC;
        
        IF @LoanID IS NULL
        BEGIN
            SET @Success = 0;
            SET @Message = 'No active loan found for this book';
            ROLLBACK;
            RETURN;
        END
        
        -- Calculate fine if not provided
        IF @FineAmount IS NULL
        BEGIN
            SET @ActualFine = dbo.fn_CalculateFine(@LoanID);
        END
        ELSE
        BEGIN
            SET @ActualFine = @FineAmount;
        END
        
        -- Update loan record
        UPDATE loans
        SET ReturnDate = GETDATE(),
            Status = 'Returned',
            FineAmount = @ActualFine,
            Notes = @Notes,
            UpdatedAt = GETDATE()
        WHERE LoanID = @LoanID;
        
        -- Book status will be updated by trigger
        
        -- Log the action
        INSERT INTO activity_logs (UserID, Action, TableName, RecordID, NewValues)
        VALUES (@UserID, 'RETURN', 'loans', @LoanID, 
                (SELECT * FROM loans WHERE LoanID = @LoanID FOR JSON PATH, WITHOUT_ARRAY_WRAPPER));
        
        COMMIT;
        SET @Success = 1;
        SET @Message = 'Book returned successfully';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK;
        
        SET @Success = 0;
        SET @Message = ERROR_MESSAGE();
        
        -- Log the error
        INSERT INTO activity_logs (UserID, Action, TableName, NewValues)
        VALUES (@UserID, 'ERROR', 'loans', 
                JSON_MODIFY('{}', '$.Error', ERROR_MESSAGE()));
    END CATCH
END;
GO

-- Procedure to update member status based on membership expiry
IF OBJECT_ID('sp_UpdateMemberStatus', 'P') IS NOT NULL
    DROP PROCEDURE sp_UpdateMemberStatus;
GO

CREATE PROCEDURE sp_UpdateMemberStatus
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        UPDATE members
        SET Status = 'Expired', UpdatedAt = GETDATE()
        WHERE Status = 'Active' 
        AND MembershipExpiry < GETDATE();
        
        INSERT INTO activity_logs (Action, TableName, NewValues)
        VALUES ('SYSTEM', 'members', 
                JSON_MODIFY('{}', '$.Action', 'Updated expired memberships'));
    END TRY
    BEGIN CATCH
        -- Log the error
        INSERT INTO activity_logs (Action, TableName, NewValues)
        VALUES ('ERROR', 'members', 
                JSON_MODIFY('{}', '$.Error', ERROR_MESSAGE()));
    END CATCH
END;
GO

-- Procedure to generate reports
IF OBJECT_ID('sp_GenerateReport', 'P') IS NOT NULL
    DROP PROCEDURE sp_GenerateReport;
GO

CREATE PROCEDURE sp_GenerateReport
    @ReportType NVARCHAR(50),
    @StartDate DATETIME = NULL,
    @EndDate DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Set default date range if not specified
    IF @StartDate IS NULL
        SET @StartDate = DATEADD(month, -1, GETDATE());
    
    IF @EndDate IS NULL
        SET @EndDate = GETDATE();
    
    -- Popular Books Report
    IF @ReportType = 'PopularBooks'
    BEGIN
        SELECT 
            b.BookID,
            b.Title,
            b.Author,
            COUNT(l.LoanID) AS TimesLoaned,
            c.CategoryName
        FROM books b
        LEFT JOIN loans l ON b.BookID = l.BookID AND l.LoanDate BETWEEN @StartDate AND @EndDate
        LEFT JOIN categories c ON b.CategoryID = c.CategoryID
        GROUP BY b.BookID, b.Title, b.Author, c.CategoryName
        ORDER BY TimesLoaned DESC;
    END
    
    -- Overdue Books Report
    ELSE IF @ReportType = 'OverdueBooks'
    BEGIN
        SELECT 
            b.BookID,
            b.Title,
            b.Author,
            m.MemberID,
            m.FirstName + ' ' + m.LastName AS MemberName,
            m.Email,
            m.Phone,
            l.LoanDate,
            l.DueDate,
            DATEDIFF(day, l.DueDate, GETDATE()) AS DaysOverdue,
            dbo.fn_CalculateFine(l.LoanID) AS EstimatedFine
        FROM loans l
        JOIN books b ON l.BookID = b.BookID
        JOIN members m ON l.MemberID = m.MemberID
        WHERE (l.Status = 'Borrowed' OR l.Status = 'Overdue')
        AND l.DueDate < GETDATE()
        ORDER BY DaysOverdue DESC;
    END
    
    -- Member Activity Report
    ELSE IF @ReportType = 'MemberActivity'
    BEGIN
        SELECT 
            m.MemberID,
            m.FirstName + ' ' + m.LastName AS MemberName,
            m.Email,
            COUNT(l.LoanID) AS TotalLoans,
            SUM(CASE WHEN l.Status = 'Overdue' OR (l.ReturnDate > l.DueDate) THEN 1 ELSE 0 END) AS OverdueCount,
            SUM(l.FineAmount) AS TotalFines,
            m.MembershipDate,
            m.MembershipExpiry,
            m.Status
        FROM members m
        LEFT JOIN loans l ON m.MemberID = l.MemberID AND l.LoanDate BETWEEN @StartDate AND @EndDate
        GROUP BY 
            m.MemberID, m.FirstName, m.LastName, m.Email, 
            m.MembershipDate, m.MembershipExpiry, m.Status
        ORDER BY TotalLoans DESC;
    END
    
    -- Category Distribution Report
    ELSE IF @ReportType = 'CategoryDistribution'
    BEGIN
        SELECT 
            c.CategoryID,
            c.CategoryName,
            COUNT(b.BookID) AS BookCount,
            COUNT(l.LoanID) AS LoanCount
        FROM categories c
        LEFT JOIN books b ON c.CategoryID = b.CategoryID
        LEFT JOIN loans l ON b.BookID = l.BookID AND l.LoanDate BETWEEN @StartDate AND @EndDate
        GROUP BY c.CategoryID, c.CategoryName
        ORDER BY LoanCount DESC;
    END
    
    -- Fine Collection Report
    ELSE IF @ReportType = 'FineCollection'
    BEGIN
        SELECT 
            CONVERT(DATE, l.ReturnDate) AS CollectionDate,
            SUM(l.FineAmount) AS TotalCollected,
            COUNT(l.LoanID) AS ReturnCount
        FROM loans l
        WHERE l.Status = 'Returned'
        AND l.FineAmount > 0
        AND l.ReturnDate BETWEEN @StartDate AND @EndDate
        GROUP BY CONVERT(DATE, l.ReturnDate)
        ORDER BY CollectionDate;
    END
END;
GO
