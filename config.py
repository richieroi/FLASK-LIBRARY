import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database configuration
    # SQLite (default/fallback database that works without configuration)
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///library.db'
    
    # SQL Server connection options - uncomment and adjust ONE of these options as needed
    # Option 1: Using ODBC Driver with DSN
    # SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc:///?odbc_connect=DSN=YourDSNName;'
    
    #Option 2: Using ODBC Driver with direct connection string (Windows Authentication)
    SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-170MKOG;DATABASE=library_system;Trusted_Connection=yes;'
    
    # Option 3: Using ODBC Driver with SQL authentication
    # SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://username:password@DESKTOP-170MKOG/library_system?driver=ODBC+Driver+17+for+SQL+Server'
    
    # General settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BACKUP_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'backups')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    @staticmethod
    def init_app(app):
        # Create backup folder if it doesn't exist
        os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)
