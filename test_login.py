import requests
import json

# Test login endpoint
def test_login():
    url = "http://127.0.0.1:5002/login"
    
    # Test data
    test_cases = [
        {
            "username": "admin",
            "password": "admin123",
            "expected": "success"
        },
        {
            "username": "admin",
            "password": "wrong",
            "expected": "error"
        },
        {
            "username": "nonexistent", 
            "password": "admin123",
            "expected": "error"
        }
    ]
    
    print("🧪 Testing Login Endpoint")
    print("=" * 40)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test['username']}/{test['password']}")
        
        try:
            response = requests.post(url, 
                json={
                    "username": test["username"],
                    "password": test["password"]
                },
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"Response: {data}")
                
                if test['expected'] == 'success':
                    if response.status_code == 200 and data.get('success'):
                        print("✅ PASS - Login successful")
                    else:
                        print("❌ FAIL - Expected success")
                else:
                    if response.status_code != 200 or data.get('error'):
                        print("✅ PASS - Expected error")
                    else:
                        print("❌ FAIL - Expected error")
            else:
                print(f"Non-JSON response: {response.text[:100]}...")
                
        except requests.exceptions.ConnectionError:
            print("❌ FAIL - Cannot connect to server")
        except Exception as e:
            print(f"❌ ERROR - {e}")

if __name__ == "__main__":
    test_login()