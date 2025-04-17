from extensions import oauth
from .routes import home, login, authorize, logout  # Import route functions

iserv = None

def init_sso(app):
    """Initialize SSO and register OAuth providers."""
    oauth.init_app(app)



def register_sso_routes(app):
    """Attach SSO routes to Flask app."""
    app.add_url_rule("/", "home", home)
    app.add_url_rule("/login", "login", login)
    app.add_url_rule("/authorize", "authorize", authorize)
    app.add_url_rule("/logout", "logout", logout)
