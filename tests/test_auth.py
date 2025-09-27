import pytest
from app import create_app
from unittest.mock import patch, MagicMock

# --- Fixtures ---
@pytest.fixture
def app():
    """
    Create a new app instance for each test, with Firebase services fully mocked.
    """
    # This patches the objects at the module level, so any import of them gets the mock.
    with patch('services.firebase_service.db', MagicMock()), \
         patch('services.firebase_service.auth', MagicMock()), \
         patch('services.firebase_service.create_user_with_group') as mock_create_user:

        app = create_app('testing')
        # Attach the mock to the app so we can assert its calls in the test
        app.mock_create_user = mock_create_user
        yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

# --- Tests ---

def test_register_user_success(client, app):
    """Test successful user registration via the API."""
    response = client.post('/api/register', json={
        'email': 'test@example.com',
        'password': 'Password123',
        'username': 'testuser',
        'consent': True
    })

    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'
    app.mock_create_user.assert_called_once_with(
        'test@example.com', 'Password123', 'testuser', True, '127.0.0.1'
    )

def test_register_user_weak_password(client):
    """Test registration failure with a weak password."""
    response = client.post('/api/register', json={
        'email': 'test2@example.com', 'password': '123',
        'username': 'testuser2', 'consent': True
    })
    assert response.status_code == 400
    assert 'Password must be at least 8 characters long' in response.get_json()['message']

@patch('services.firebase_service.verify_token')
@patch('services.firebase_service.get_user')
def test_login_required_decorator(mock_get_user, mock_verify_token, client):
    """Test the @login_required decorator for both valid and invalid tokens."""
    # Test with valid token
    mock_verify_token.return_value = {'uid': 'testuid123'}
    mock_get_user.return_value = {'role': 'user'}
    response = client.get('/api/user/profile', headers={'Authorization': 'Bearer valid_token'})
    assert response.status_code == 200

    # Test with invalid token
    mock_verify_token.return_value = None
    response = client.get('/api/user/profile', headers={'Authorization': 'Bearer invalid_token'})
    assert response.status_code == 401
    assert 'Invalid or expired token' in response.get_json()['message']

    # Test with no token (page redirect)
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.location