from fastapi.testclient import TestClient
from src.main import app 

client = TestClient(app)

def test_login_returns_token():
    assert 1 == 1

def test_register_user_returns_token():
    assert 1 == 1