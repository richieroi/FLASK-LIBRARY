from datetime import timedelta
import os

class Config:
    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mysecretlibrarysystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Database settings
    DB_SERVER = os.environ.get('DESKTOP-170MKOG') or 'localhost'
    DB_NAME = os.environ.get('library_system') or 'library_system'
    DB_DRIVER = os.environ.get('DB_DRIVER') or 'ODBC Driver 17 for SQL Server'
    
    # Connection string for pyodbc
    DB_CONNECTION_STRING = f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"
    
    # Backup settings
    BACKUP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    
    @staticmethod
    def init_app(app):
        # Create backup folder if it doesn't exist
        if not os.path.exists(Config.BACKUP_FOLDER):
            os.makedirs(Config.BACKUP_FOLDER)
