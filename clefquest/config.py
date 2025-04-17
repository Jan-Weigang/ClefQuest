import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///clefquest.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session Configuration
    SESSION_TYPE = "filesystem"  # Can be 'redis', 'sqlalchemy', etc.
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True  # Sign session IDs for extra security

    # OAuth Credentials (IServ)
    ISERV_CLIENT_ID = os.environ.get("ISERV_CLIENT_ID")
    ISERV_CLIENT_SECRET = os.environ.get("ISERV_CLIENT_SECRET")
    ISERV_CLIENT_DOMAIN = os.environ.get("ISERV_CLIENT_DOMAIN")
    SERVER_DOMAIN = os.environ.get("SERVER_DOMAIN")
