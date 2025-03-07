# Alexandria Library Management System

A comprehensive web-based library management system built with Flask and SQLAlchemy, designed to provide easy book cataloging, member management, loan tracking, and administrative functions.

![Alexandria Library System]

## Features

- **Book Management**: Catalog, search, and manage books by title, author, category, and availability
- **Member Management**: Track member information, membership status, and loan history
- **Loan System**: Process loans and returns with automated fine calculation
- **Role-Based Access Control**: Different levels of access for admins, staff, members, and guests
- **User Dashboard**: Customized dashboards based on user roles
- **Responsive Design**: Works on desktop and mobile devices

## Technology Stack

- **Backend**: Python, Flask
- **Database**: SQL Server (with fallback to SQLite)
- **ORM**: SQLAlchemy
- **Frontend**: Bootstrap 4, jQuery, Font Awesome
- **Authentication**: Custom session-based auth with password hashing

## Installation

### Prerequisites

- Python 3.6 or higher
- SQL Server or SQLite
- pip (Python package installer)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/richieroi/LIBRARY.git
   cd library-management-system
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure the database in `config.py`:
   ```python
   # Use SQL Server
   SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server'
   
   # Or use SQLite (uncomment to use)
   # SQLALCHEMY_DATABASE_URI = 'sqlite:///library.db'
   ```

5. Initialize the database:
   ```
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. Run the application:
   ```
   python app.py
   ```

7. Access the application at `http://localhost:5000`

## Directory Structure

