import requests
import json

# Test login endpoint
url = 'http://127.0.0.1:8000/api/login/'

# Test credentials from README
test_users = [
    {'username': 'tendai_moyo', 'password': 'password123', 'expected': 'client'},
    {'username': 'john_phiri', 'password': 'password123', 'expected': 'provider'},
    {'username': 'admin', 'password': 'admin123', 'expected': 'admin'},
]

print("Testing login API endpoint...\n")

for user in test_users:
    print(f"Testing {user['username']}...")
    
    try:
        # Get CSRF token first
        session = requests.Session()
        session.get('http://127.0.0.1:8000/login/')
        csrf_token = session.cookies.get('csrftoken', '')
        
        # Attempt login
        response = session.post(
            url,
            json={'username': user['username'], 'password': user['password']},
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token,
                'Referer': 'http://127.0.0.1:8000/login/'
            }
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        
        if response.status_code == 200:
            print(f"  ✅ SUCCESS - {user['username']} logged in\n")
        else:
            print(f"  ❌ FAILED - {user['username']} login failed\n")
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}\n")

print("\nTest complete!")
