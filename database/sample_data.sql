-- Library Management System Sample Data
-- ====================================

USE library_system;
GO

-- Clear existing data if needed
--DELETE FROM activity_logs;
--DELETE FROM loans;
--DELETE FROM books;
--DELETE FROM members;
--DELETE FROM user_roles;
--DELETE FROM users;
--DELETE FROM roles;
--DELETE FROM categories;

-- Insert Roles
INSERT INTO roles (RoleName, Description) 
VALUES 
    ('Admin', 'Full access to all system features'),
    ('Staff', 'Can manage books, members, and loans'),
    ('Member', 'Regular library member'),
    ('Guest', 'Limited access'),
    ('Librarian', 'Specialized book management role'),
    ('Cataloger', 'Can categorize and organize books'),
    ('Director', 'Library management oversight'),
    ('IT', 'System maintenance and support'),
    ('Volunteer', 'Limited assistance role'),
    ('Researcher', 'Academic access role');
GO

-- Insert Users with hashed passwords
-- Note: In a real application, use werkzeug.security.generate_password_hash in Python
-- Here we're just inserting dummy hashed values
INSERT INTO users (Username, PasswordHash, Email, FirstName, LastName, IsActive) 
VALUES 
    ('admin', 'pbkdf2:sha256:150000$TmplXrQA$cabf8f3c48608f8e0fec5a36508c205a6f781a3bdd28c0ad8ceb442529f688bc', 'admin@library.com', 'Admin', 'User', 1),
    ('jsmith', 'pbkdf2:sha256:150000$E3kioylV$6b1c0d4e25af31e7b725e739cc07f8b7de197177a774b6c743cfa66ec9f96864', 'john.smith@example.com', 'John', 'Smith', 1),
    ('mjones', 'pbkdf2:sha256:150000$YhvQ0hGt$c84dbbb405e4e6a126cc963bd4b0f324c18ebe5831f2aa49a741cba4f1e07cc7', 'mary.jones@example.com', 'Mary', 'Jones', 1),
    ('dlee', 'pbkdf2:sha256:150000$AzbbjOU3$c7fafaca43837a78769b88bbf16eb4752dd41fd978daa640ba2f187ac368a8e8', 'david.lee@example.com', 'David', 'Lee', 1),
    ('swilson', 'pbkdf2:sha256:150000$ytP4sx9J$3db5e937003891ad56bdcf31d73ec09b99c0e1202cdf2d40e3bfea8441213eb0', 'sarah.wilson@example.com', 'Sarah', 'Wilson', 1),
    ('mjohnson', 'pbkdf2:sha256:150000$6nd3wDRm$7055593485eb48cea1e0945d5c9fc9887a9c0776c83ab9723c202ead583af5cc', 'michael.johnson@example.com', 'Michael', 'Johnson', 1),
    ('rbrown', 'pbkdf2:sha256:150000$JGlyKLs3$e8eaa0a2af50c1ab677d8ec2fb5318c6ab478bd5d13d287069f58c19e42d053f', 'robert.brown@example.com', 'Robert', 'Brown', 1),
    ('pwilliams', 'pbkdf2:sha256:150000$UGnklX9v$79d502778dd76dd83cb4d234d262caa5d9dd1b308bca093ca73fce5fc4d78cea', 'patricia.williams@example.com', 'Patricia', 'Williams', 1),
    ('jgarcia', 'pbkdf2:sha256:150000$rlUGZmmQ$d02533e5d31a9acb694ca37c756ef8d5c58e267bbaf836df6f19b2698cbad4bd', 'james.garcia@example.com', 'James', 'Garcia', 1),
    ('lmartinez', 'pbkdf2:sha256:150000$2eO5I0Jt$43bef7c8b2d9953b47f8acdc900d23f02c689f990184c8448ca8c4802d0e7f3b', 'linda.martinez@example.com', 'Linda', 'Martinez', 1),
    ('rthomas', 'pbkdf2:sha256:150000$7fkCZ95E$20251c170d7208da7e92343c656d7537c796e824a4d06b998d3a1a3d69f73f76', 'richard.thomas@example.com', 'Richard', 'Thomas', 1),
    ('etaylor', 'pbkdf2:sha256:150000$rTUfXYcZ$3c2f38d18eaeee9c9a9f60a267dbbc3b78a4ebe57663eec9f5f03a8935254fc7', 'elizabeth.taylor@example.com', 'Elizabeth', 'Taylor', 1);
GO

-- Assign roles to users
INSERT INTO user_roles (user_id, role_id)
VALUES
    (1, 1), -- Admin -> Admin
    (2, 2), -- jsmith -> Staff
    (3, 2), -- mjones -> Staff
    (4, 3), -- dlee -> Member
    (5, 3), -- swilson -> Member
    (6, 3), -- mjohnson -> Member
    (7, 4), -- rbrown -> Guest
    (8, 5), -- pwilliams -> Librarian
    (9, 6), -- jgarcia -> Cataloger
    (10, 3), -- lmartinez -> Member
    (11, 4), -- rthomas -> Guest
    (12, 3); -- etaylor -> Member
GO

-- Insert Categories
INSERT INTO categories (CategoryName, Description)
VALUES
    ('Fiction', 'Novels, short stories, and other fictional works'),
    ('Non-Fiction', 'Factual and informative books on various subjects'),
    ('Science Fiction', 'Fiction dealing with futuristic concepts, space, time travel, etc.'),
    ('Mystery', 'Fiction dealing with the solution of a crime or the unraveling of secrets'),
    ('Biography', 'Accounts of people''s lives written by someone else'),
    ('History', 'Books about historical events and periods'),
    ('Children', 'Books intended for children'),
    ('Science', 'Books about scientific principles and discoveries'),
    ('Technology', 'Books about technology and its applications'),
    ('Arts', 'Books about visual arts, music, etc.'),
    ('Philosophy', 'Books about philosophical concepts and thinkers'),
    ('Religion', 'Books about religious beliefs, practices, and history'),
    ('Business', 'Books about business practices, management, finance, etc.'),
    ('Travel', 'Books about travel destinations and experiences');
GO

-- Insert Books
INSERT INTO books (Title, Author, ISBN, PublicationYear, Publisher, CategoryID, Status, Description, CoverImage)
VALUES
    ('To Kill a Mockingbird', 'Harper Lee', '9780446310789', 1960, 'J. B. Lippincott & Co.', 1, 'Available', 
     'The story of young Scout Finch, her brother Jem, and their father Atticus, as they navigate through issues of race and ethics in the Depression-era South.', 
     'https://images-na.ssl-images-amazon.com/images/I/71FxgtFKcQL.jpg'),
    
    ('1984', 'George Orwell', '9780451524935', 1949, 'Secker & Warburg', 3, 'Available', 
     'The story of Winston Smith, a citizen of a dystopian society ruled by the omnipresent Big Brother, where daily life consists of poverty, hate, and fear.', 
     'https://images-na.ssl-images-amazon.com/images/I/71kxa1-0mfL.jpg'),
    
    ('The Catcher in the Rye', 'J.D. Salinger', '9780316769488', 1951, 'Little, Brown and Company', 1, 'Available', 
     'The story of Holden Caulfield, a teenager from New York who is expelled from his prep school and then takes a journey around New York City.', 
     'https://images-na.ssl-images-amazon.com/images/I/81OthjkJBuL.jpg'),
    
    ('Pride and Prejudice', 'Jane Austen', '9780141439518', 1813, 'T. Egerton, Whitehall', 1, 'Borrowed', 
     'The story of Elizabeth Bennet, who learns about the repercussions of hasty judgments and eventually comes to appreciate the difference between superficial goodness and actual goodness.', 
     'https://images-na.ssl-images-amazon.com/images/I/71Ui-NwYUmL.jpg'),
    
    ('The Diary of a Young Girl', 'Anne Frank', '9780553296983', 1947, 'Contact Publishing', 5, 'Available', 
     'The writings from the Dutch-language diary kept by Anne Frank while she was in hiding for two years with her family during the Nazi occupation of the Netherlands.', 
     'https://images-na.ssl-images-amazon.com/images/I/81xPFVVGesL.jpg'),
    
    ('The Hobbit', 'J.R.R. Tolkien', '9780547928227', 1937, 'George Allen & Unwin', 3, 'Available', 
     'The story of hobbit Bilbo Baggins, who is convinced by the wizard Gandalf to accompany thirteen dwarves on a quest to reclaim the Lonely Mountain from the dragon Smaug.', 
     'https://images-na.ssl-images-amazon.com/images/I/710+HcoP38L.jpg'),
    
    ('Brave New World', 'Aldous Huxley', '9780060850524', 1932, 'Chatto & Windus', 3, 'Borrowed', 
     'The story of a futuristic World State where citizens are environmentally engineered into a severe intelligence-based social hierarchy.', 
     'https://images-na.ssl-images-amazon.com/images/I/81zE42gT3xL.jpg'),
    
    ('The Great Gatsby', 'F. Scott Fitzgerald', '9780743273565', 1925, 'Charles Scribner''s Sons', 1, 'Available', 
     'The story of the mysteriously wealthy Jay Gatsby and his love for the beautiful Daisy Buchanan, set during the Roaring Twenties.', 
     'https://images-na.ssl-images-amazon.com/images/I/71FTb9X6wsL.jpg'),
    
    ('The Alchemist', 'Paulo Coelho', '9780062315007', 1988, 'HarperOne', 1, 'Available', 
     'The story of Santiago, an Andalusian shepherd boy who yearns to travel in search of a worldly treasure as extravagant as any ever found.', 
     'https://images-na.ssl-images-amazon.com/images/I/71aFt4+OTOL.jpg'),
    
    ('The Lord of the Rings', 'J.R.R. Tolkien', '9780618640157', 1954, 'George Allen & Unwin', 3, 'Borrowed', 
     'The story of the hobbit Frodo Baggins, who embarks on a perilous quest to destroy the One Ring and ensure the downfall of the Dark Lord Sauron.', 
     'https://images-na.ssl-images-amazon.com/images/I/71RTC9I9VTL.jpg'),
    
    ('Sapiens: A Brief History of Humankind', 'Yuval Noah Harari', '9780062316097', 2011, 'Harper', 2, 'Available', 
     'A book that explores the history of the human species, from the emergence of Homo sapiens in Africa to the political and technological revolutions of the 21st century.', 
     'https://images-na.ssl-images-amazon.com/images/I/71l9WWa-rXL.jpg'),
    
    ('Thinking, Fast and Slow', 'Daniel Kahneman', '9780374533557', 2011, 'Farrar, Straus and Giroux', 2, 'Available', 
     'A book that summarizes research that Kahneman performed over decades, often in collaboration with Amos Tversky, on cognitive biases, prospect theory, and happiness.', 
     'https://images-na.ssl-images-amazon.com/images/I/71wvKXWfUUL.jpg'),
    
    ('Dune', 'Frank Herbert', '9780441172719', 1965, 'Chilton Books', 3, 'Available', 
     'The story of Paul Atreides, whose family accepts the stewardship of the planet Arrakis, the only source of the "spice" melange, the most important and valuable substance in the universe.', 
     'https://images-na.ssl-images-amazon.com/images/I/81ym3QUd3KL.jpg'),
    
    ('The Art of War', 'Sun Tzu', '9781590302255', -500, 'Shambhala Publications', 2, 'Borrowed', 
     'An ancient Chinese military treatise dating from the Spring and Autumn Period. It contains a detailed explanation and analysis of the Chinese military, from weapons and strategy to rank and discipline.', 
     'https://images-na.ssl-images-amazon.com/images/I/71IbQR2dcoL.jpg'),
    
    ('A Brief History of Time', 'Stephen Hawking', '9780553380163', 1988, 'Bantam Books', 8, 'Available', 
     'A book on theoretical cosmology by English physicist Stephen Hawking that explores the history and theories of the universe.', 
     'https://images-na.ssl-images-amazon.com/images/I/51+GySc8ExL.jpg');
GO

-- Insert Members
INSERT INTO members (FirstName, LastName, Email, Phone, Address, MembershipDate, MembershipExpiry, Status, UserID)
VALUES
    ('John', 'Smith', 'john.smith@example.com', '555-123-4567', '123 Main St, Anytown, USA', DATEADD(month, -6, GETDATE()), DATEADD(month, 6, GETDATE()), 'Active', 2),
    
    ('Mary', 'Jones', 'mary.jones@example.com', '555-234-5678', '456 Oak St, Anytown, USA', DATEADD(month, -3, GETDATE()), DATEADD(month, 9, GETDATE()), 'Active', 3),
    
    ('David', 'Lee', 'david.lee@example.com', '555-345-6789', '789 Pine St, Anytown, USA', DATEADD(month, -2, GETDATE()), DATEADD(month, 10, GETDATE()), 'Active', 4),
    
    ('Sarah', 'Wilson', 'sarah.wilson@example.com', '555-456-7890', '101 Elm St, Anytown, USA', DATEADD(month, -12, GETDATE()), DATEADD(month, -1, GETDATE()), 'Expired', 5),
    
    ('Michael', 'Johnson', 'michael.johnson@example.com', '555-567-8901', '202 Maple St, Anytown, USA', DATEADD(month, -1, GETDATE()), DATEADD(month, 11, GETDATE()), 'Active', 6),
    
    ('Linda', 'Martinez', 'linda.martinez@example.com', '555-678-9012', '303 Cedar St, Anytown, USA', DATEADD(month, -8, GETDATE()), DATEADD(month, 4, GETDATE()), 'Active', 10),
    
    ('Elizabeth', 'Taylor', 'elizabeth.taylor@example.com', '555-789-0123', '404 Birch St, Anytown, USA', DATEADD(month, -4, GETDATE()), DATEADD(month, 8, GETDATE()), 'Active', 12),
    
    ('William', 'Anderson', 'william.anderson@example.com', '555-890-1234', '505 Walnut St, Anytown, USA', DATEADD(month, -9, GETDATE()), DATEADD(month, 3, GETDATE()), 'Active', NULL),
    
    ('Jennifer', 'Thomas', 'jennifer.thomas@example.com', '555-901-2345', '606 Chestnut St, Anytown, USA', DATEADD(month, -5, GETDATE()), DATEADD(month, 7, GETDATE()), 'Active', NULL),
    
    ('Charles', 'Jackson', 'charles.jackson@example.com', '555-012-3456', '707 Spruce St, Anytown, USA', DATEADD(month, -7, GETDATE()), DATEADD(month, 5, GETDATE()), 'Active', NULL),
    
    ('Barbara', 'White', 'barbara.white@example.com', '555-123-4567', '808 Ash St, Anytown, USA', DATEADD(month, -10, GETDATE()), DATEADD(month, 2, GETDATE()), 'Active', NULL),
    
    ('Richard', 'Harris', 'richard.harris@example.com', '555-234-5678', '909 Beech St, Anytown, USA', DATEADD(month, -11, GETDATE()), DATEADD(month, 1, GETDATE()), 'Active', NULL);
GO

-- Insert Loans
INSERT INTO loans (BookID, MemberID, LoanDate, DueDate, ReturnDate, Status, FineAmount)
VALUES
    -- Current loans
    (4, 1, DATEADD(day, -14, GETDATE()), DATEADD(day, 7, GETDATE()), NULL, 'Borrowed', 0.00),
    (7, 2, DATEADD(day, -10, GETDATE()), DATEADD(day, 11, GETDATE()), NULL, 'Borrowed', 0.00),
    (10, 3, DATEADD(day, -7, GETDATE()), DATEADD(day, 14, GETDATE()), NULL, 'Borrowed', 0.00),
    (14, 5, DATEADD(day, -21, GETDATE()), DATEADD(day, -7, GETDATE()), NULL, 'Overdue', 3.50),
    
    -- Past loans
    (1, 2, DATEADD(day, -60, GETDATE()), DATEADD(day, -39, GETDATE()), DATEADD(day, -42, GETDATE()), 'Returned', 0.00),
    (2, 3, DATEADD(day, -50, GETDATE()), DATEADD(day, -29, GETDATE()), DATEADD(day, -30, GETDATE()), 'Returned', 0.00),
    (3, 4, DATEADD(day, -45, GETDATE()), DATEADD(day, -24, GETDATE()), DATEADD(day, -20, GETDATE()), 'Returned', 2.00),
    (5, 6, DATEADD(day, -40, GETDATE()), DATEADD(day, -19, GETDATE()), DATEADD(day, -22, GETDATE()), 'Returned', 0.00),
    (6, 7, DATEADD(day, -35, GETDATE()), DATEADD(day, -14, GETDATE()), DATEADD(day, -15, GETDATE()), 'Returned', 0.00),
    (8, 8, DATEADD(day, -30, GETDATE()), DATEADD(day, -9, GETDATE()), DATEADD(day, -5, GETDATE()), 'Returned', 2.00),
    (9, 9, DATEADD(day, -25, GETDATE()), DATEADD(day, -4, GETDATE()), DATEADD(day, -6, GETDATE()), 'Returned', 0.00),
    (11, 10, DATEADD(day, -20, GETDATE()), DATEADD(day, 1, GETDATE()), DATEADD(day, -2, GETDATE()), 'Returned', 0.00),
    (12, 11, DATEADD(day, -15, GETDATE()), DATEADD(day, 6, GETDATE()), DATEADD(day, -1, GETDATE()), 'Returned', 0.00),
    (13, 12, DATEADD(day, -55, GETDATE()), DATEADD(day, -34, GETDATE()), DATEADD(day, -25, GETDATE()), 'Returned', 4.50);
GO

-- Insert Activity Logs
INSERT INTO activity_logs (UserID, Action, TableName, RecordID, OldValues, NewValues, IPAddress, ChangedAt)
VALUES
    (1, 'LOGIN', NULL, NULL, NULL, NULL, '192.168.1.101', DATEADD(day, -30, GETDATE())),
    (1, 'INSERT', 'books', 1, NULL, '{"Title": "To Kill a Mockingbird", "Author": "Harper Lee"}', '192.168.1.101', DATEADD(day, -29, GETDATE())),
    (1, 'INSERT', 'members', 1, NULL, '{"FirstName": "John", "LastName": "Smith"}', '192.168.1.101', DATEADD(day, -28, GETDATE())),
    (2, 'LOGIN', NULL, NULL, NULL, NULL, '192.168.1.102', DATEADD(day, -27, GETDATE())),
    (2, 'LOAN', 'loans', 1, NULL, '{"BookID": 4, "MemberID": 1}', '192.168.1.102', DATEADD(day, -14, GETDATE())),
    (3, 'LOGIN', NULL, NULL, NULL, NULL, '192.168.1.103', DATEADD(day, -26, GETDATE())),
    (3, 'RETURN', 'loans', 5, '{"Status": "Borrowed"}', '{"Status": "Returned", "ReturnDate": "2023-10-01"}', '192.168.1.103', DATEADD(day, -25, GETDATE())),
    (1, 'UPDATE', 'books', 2, '{"Status": "Borrowed"}', '{"Status": "Available"}', '192.168.1.101', DATEADD(day, -24, GETDATE())),
    (2, 'INSERT', 'members', 8, NULL, '{"FirstName": "William", "LastName": "Anderson"}', '192.168.1.102', DATEADD(day, -23, GETDATE())),
    (3, 'LOAN', 'loans', 2, NULL, '{"BookID": 7, "MemberID": 2}', '192.168.1.103', DATEADD(day, -10, GETDATE())),
    (1, 'LOGOUT', NULL, NULL, NULL, NULL, '192.168.1.101', DATEADD(day, -22, GETDATE())),
    (1, 'BACKUP', 'DATABASE', NULL, NULL, '{"BackupType": "FULL", "FileName": "FULL_backup_20231015_120000.bak"}', '192.168.1.101', DATEADD(day, -15, GETDATE())),
    (1, 'RESTORE', 'DATABASE', NULL, NULL, '{"FileName": "FULL_backup_20231015_120000.bak"}', '192.168.1.101', DATEADD(day, -14, GETDATE())),
    (2, 'UPDATE', 'members', 4, '{"Status": "Active", "MembershipExpiry": "2023-10-01"}', '{"Status": "Expired", "MembershipExpiry": "2023-10-01"}', '192.168.1.102', DATEADD(day, -7, GETDATE()));
GO
