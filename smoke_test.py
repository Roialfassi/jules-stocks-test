import requests
import time

def test_smoke():
    try:
        r = requests.get('http://localhost:5000/login')
        print(f"Login Page Status: {r.status_code}")
        assert r.status_code == 200

        # Register
        s = requests.Session()
        # Get CSRF?
        # The app injects it in JS. We need to parse it or use the API which checks header.
        # But we need the token first. It's in the HTML.

        # For simplicity, if we don't have easy CSRF extraction, we might skip POST tests in this smoke script.
        # But we can verify pages load.

        r = requests.get('http://localhost:5000/register')
        assert r.status_code == 200

        print("Smoke test passed: Pages match 200 OK")
    except Exception as e:
        print(f"Smoke test failed: {e}")
        exit(1)

if __name__ == "__main__":
    test_smoke()
