from functools import wraps
from flask import session, abort

# def role_required(role_id):
#     """Decorator to ensure the user has a specific role."""
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             # Retrieve user roles from the session
#             user_info = session.get('user_info', {})
#             roles = user_info.get('roles', [])
            
#             # Check if the required role is present
#             if not any(role.get('id') == role_id for role in roles):
#                 abort(403)  # Forbidden if the role is not found
            
#             return func(*args, **kwargs)
#         return wrapper
#     return decorator

# # Predefined role decorators
# is_teacher = role_required('ROLE_TEACHER')
# is_student = role_required('ROLE_STUDENT')


from functools import wraps
from flask import session, abort

def has_role(role_id):
    """Returns True if the user has the specified role, otherwise False."""
    user_info = session.get('user_info', {})
    roles = user_info.get('roles', [])
    return any(role.get('id') == role_id for role in roles)

def role_required(role_id):
    """Decorator to ensure the user has a specific role."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not has_role(role_id):  # Use the bool check instead
                abort(403)  # Forbidden if the role is not found
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Predefined role decorators
is_teacher = role_required('ROLE_TEACHER')
is_student = role_required('ROLE_STUDENT')

# Boolean functions for direct role checking mostly for admin views
def is_teacher_bool():
    return has_role('ROLE_TEACHER')

def is_student_bool():
    return has_role('ROLE_STUDENT')
