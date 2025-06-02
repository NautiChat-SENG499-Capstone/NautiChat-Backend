from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from .schemas import UserInDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

FAKE_USER = UserInDB(
    user_id=1,
    username="account1",
    hashed_password="password1",
    onc_token="fakeONCtoken",
    is_admin=True,
)


def fake_decode_token(_token) -> UserInDB:
    return FAKE_USER


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    # For now always return a fake user
    user = fake_decode_token(token)
    return user


def get_admin_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    # For now always return an "admin user"
    user = fake_decode_token(token)
    return user
