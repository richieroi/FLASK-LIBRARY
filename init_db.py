import os
import pyodbc
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    return pyodbc.connect(Config.DB_CONNECTION_STRING)

def init_db():
    print("Initializing database...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if users table has been created
        cursor.execute("IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'users') SELECT 1 ELSE SELECT 0")
        if cursor.fetchone()[0] == 0:
            print("Creating users table...")
            cursor.execute("""
                CREATE TABLE users (
                    UserID INT IDENTITY(1,1) PRIMARY KEY,
                    Username VARCHAR(50) NOT NULL UNIQUE,
                    PasswordHash VARCHAR(255) NOT NULL,
                    Email VARCHAR(100) NOT NULL UNIQUE,
                    FirstName VARCHAR(50) NOT NULL,
                    LastName VARCHAR(50) NOT NULL,
                    IsActive BIT NOT NULL DEFAULT 1,
                    CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Check if roles table exists
        cursor.execute("IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'roles') SELECT 1 ELSE SELECT 0")
        if cursor.fetchone()[0] == 0:
            print("Creating roles table...")
            cursor.execute("""
                CREATE TABLE roles (
                    RoleID INT IDENTITY(1,1) PRIMARY KEY,
                    RoleName VARCHAR(50) NOT NULL UNIQUE,
                    Description VARCHAR(255) NULL
                )
            """)
            
            # Insert default roles
            default_roles = [
                ('Admin', 'Full access to all system features'),
                ('Staff', 'Can manage books, members, and loans'),
                ('Member', 'Regular library member'),
                ('Guest', 'Limited access')
            ]
            
            for role in default_roles:
                cursor.execute(
                    "INSERT INTO roles (RoleName, Description) VALUES (?, ?)",
                    role[0], role[1]
                )
        
        # Check if user_roles table exists
        cursor.execute("IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'user_roles') SELECT 1 ELSE SELECT 0")
        if cursor.fetchone()[0] == 0:
            print("Creating user_roles table...")
            cursor.execute("""
                CREATE TABLE user_roles (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL,
                    role_id INT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(UserID),
                    FOREIGN KEY (role_id) REFERENCES roles(RoleID),
                    CONSTRAINT UQ_UserRole UNIQUE (user_id, role_id)
                )
            """)
        
        # Insert users if none exist
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            print("Inserting test users...")
            
            # Define users and their roles
            users_data = [
                # [username, password, email, firstname, lastname, roles]
                ['admin', 'admin', 'admin@library.com', 'Admin', 'User', ['Admin']],
                ['jsmith', 'password123', 'john.smith@example.com', 'John', 'Smith', ['Staff']],
                ['mjones', 'password123', 'mary.jones@example.com', 'Mary', 'Jones', ['Staff']],
                ['dlee', 'password123', 'david.lee@example.com', 'David', 'Lee', ['Member']],
                ['swilson', 'password123', 'sarah.wilson@example.com', 'Sarah', 'Wilson', ['Member']],
                ['mjohnson', 'password123', 'michael.johnson@example.com', 'Michael', 'Johnson', ['Member']],
                ['rbrown', 'password123', 'robert.brown@example.com', 'Robert', 'Brown', ['Member']],
                ['pwilliams', 'password123', 'patricia.williams@example.com', 'Patricia', 'Williams', ['Member']],
                ['jgarcia', 'password123', 'james.garcia@example.com', 'James', 'Garcia', ['Guest']],
                ['lmartinez', 'password123', 'linda.martinez@example.com', 'Linda', 'Martinez', ['Guest']],
                ['rthomas', 'password123', 'richard.thomas@example.com', 'Richard', 'Thomas', ['Guest']],
                ['etaylor', 'password123', 'elizabeth.taylor@example.com', 'Elizabeth', 'Taylor', ['Guest']]
            ]
            
            for user in users_data:
                username, password, email, firstname, lastname, roles = user
                
                # Hash the password
                password_hash = generate_password_hash(password)
                
                # Insert user
                cursor.execute(
                    "INSERT INTO users (Username, PasswordHash, Email, FirstName, LastName, IsActive) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    username, password_hash, email, firstname, lastname, 1
                )
                
                # Get the user ID
                cursor.execute("SELECT UserID FROM users WHERE Username = ?", username)
                user_id = cursor.fetchone()[0]
                
                # Assign roles
                for role_name in roles:
                    cursor.execute("SELECT RoleID FROM roles WHERE RoleName = ?", role_name)
                    role_id = cursor.fetchone()[0]
                    
                    cursor.execute(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                        user_id, role_id
                    )
            
            conn.commit()
            print("Users created successfully!")
        else:
            print("Users already exist, skipping user creation.")
            
    print("Database initialization complete!")

if __name__ == "__main__":
    init_db()
