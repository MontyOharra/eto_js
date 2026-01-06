"""
Authentication domain types.
"""
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Represents an authenticated user."""
    staff_emp_id: int
    username: str  # Staff_Login - used for audit trail (Orders_UpdtLID)
    display_name: str
    first_name: str
    last_name: str
