from flask import session, redirect, url_for
from .iserv import iserv
from config import Config


def home():
    """Redirect the user to the appropriate dashboard based on their role."""
    user_info = session.get("user_info")
    if not user_info:
        return redirect(url_for("login"))

    if any(role.get("id") == "ROLE_STUDENT" for role in user_info.get("roles", [])):
        return redirect(url_for("student.student"))
    elif any(role.get("id") == "ROLE_TEACHER" for role in user_info.get("roles", [])):
        return redirect(url_for("teacher.teacher_dashboard"))
    else:
        return "Unauthorized", 403

def login():
    """Redirect user to IServ login."""
    if session.get("user_info"):
        return home()
    
    redirect_uri = f"https://{Config.SERVER_DOMAIN}/authorize"
    assert iserv
    return iserv.authorize_redirect(redirect_uri)

def authorize():
    """Handle IServ OAuth callback and set user session."""
    assert iserv
    token = iserv.authorize_access_token()
    user_info = iserv.userinfo(token=token)

    # Store user info in session
    session["user_info"] = user_info

    return home()

def logout():
    """Logout the user and clear session."""
    session.clear()
    return 'Logged out! <a href="/">Go to Home</a>'
