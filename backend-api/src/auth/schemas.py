from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """Data safe to return to user"""

    # Allows model to be populated from SQLAlchemy ORM objects
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    onc_token: str
    is_admin: bool = False


class CreateUserRequest(BaseModel):
    """Payload for Registration"""

    username: str
    password: str
    onc_token: str


class UpdateUserRequest(BaseModel):
    """Payload for updating user info"""

    username: Optional[str] = None
    onc_token: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Payload to change password"""

    current_password: str
    new_password: str
    confirm_password: str


class Token(BaseModel):
    """JWT Token Response"""

    access_token: str
    token_type: str
