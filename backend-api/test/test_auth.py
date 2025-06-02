from fastapi.testclient import TestClient
from src.main import app 

client = TestClient(app)

def test_login_returns_token():
    response = client.post("auth/login", data={"username": "account1", "password": "anything"})
    assert response.status_code == 200
    json = response.json()
    assert "access_token" in json
    assert json["token_type"] == "bearer"

def test_register_user_returns_token():
    response = client.post("auth/register", json={"username": "miles", "password": "mypassword", "onc_token": "abcdef"})
    assert response.status_code == 200
    json = response.json()
    assert json["access_token"] == "miles"
    assert json["token_type"] == "bearer"