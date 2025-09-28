import pytest
import os
from app import create_app
from services import sqlite_service
from flask import session

# --- Fixtures ---

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # create a temporary file to isolate the database for each test
    db_path = "test_temp.sqlite"

    app = create_app('testing')
    app.config.update({
        "DATABASE": db_path,
    })

    with app.app_context():
        sqlite_service.init_db()

    yield app

    # cleanup
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

# --- Tests ---

def test_register_user_success(client):
    """Test successful user registration."""
    response = client.post('/api/register', json={
        'email': 'test@example.com',
        'password': 'Password123',
        'username': 'testuser',
        'consent': True
    })

    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'

    # Verify the user was actually created in the database
    with client.application.app_context():
        db = sqlite_service.get_db()
        user = db.execute("SELECT * FROM users WHERE email = 'test@example.com'").fetchone()
        assert user is not None
        assert user['username'] == 'testuser'

def test_register_user_weak_password(client):
    """Test registration failure with a weak password."""
    response = client.post('/api/register', json={
        'email': 'test2@example.com', 'password': '123',
        'username': 'testuser2', 'consent': True
    })
    assert response.status_code == 400
    assert 'Password must be at least 8 characters long' in response.get_json()['message']

def test_login_and_logout(client):
    """Test user login, accessing a protected route, and then logging out."""
    # First, register a user to log in with
    client.post('/api/register', json={
        'email': 'login@example.com',
        'password': 'Password123',
        'username': 'loginuser',
        'consent': True
    })

    # Test login
    login_response = client.post('/api/session-login', json={
        'email': 'login@example.com',
        'password': 'Password123'
    })
    assert login_response.status_code == 200
    assert login_response.get_json()['status'] == 'success'

    # With the client, the session is now active. Access a protected route.
    profile_response = client.get('/api/user/profile')
    assert profile_response.status_code == 200
    assert profile_response.get_json()['email'] == 'login@example.com'

    # Test logout
    logout_response = client.post('/api/logout')
    assert logout_response.status_code == 200
    assert logout_response.get_json()['status'] == 'success'

    # After logout, the protected route should be inaccessible
    profile_response_after_logout = client.get('/api/user/profile')
    assert profile_response_after_logout.status_code == 401

def test_login_invalid_credentials(client):
    """Test login failure with invalid credentials."""
    # Register user
    client.post('/api/register', json={
        'email': 'wrongpass@example.com',
        'password': 'Password123',
        'username': 'wrongpassuser',
        'consent': True
    })

    # Attempt login with wrong password
    login_response = client.post('/api/session-login', json={
        'email': 'wrongpass@example.com',
        'password': 'wrongpassword'
    })
    assert login_response.status_code == 401
    assert 'Invalid credentials' in login_response.get_json()['message']