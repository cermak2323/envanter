import requests

try:
    response = requests.post("http://127.0.0.1:5002/login", 
        json={"username": "admin", "password": "admin123"},
        timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")