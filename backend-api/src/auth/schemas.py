from pydantic import BaseModel


# Data safe to return to user
class User(BaseModel):
    user_id: int
    username: str
    onc_token: str
    is_admin: bool = False


class UserInDB(User):
    hashed_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    onc_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
