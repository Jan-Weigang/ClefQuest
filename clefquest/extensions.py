from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_session import Session
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
admin = Admin(name="Admin Panel", template_mode="bootstrap4")
oauth = OAuth()

def init_session(app):
    """Initialize Flask-Session with app."""
    Session(app)  # ✅ Correct way to initialize Flask-Session