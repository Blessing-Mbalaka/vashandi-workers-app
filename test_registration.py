import requests
import json

# Test registration endpoint
url = 'http://127.0.0.1:8000/api/register/'

# Test new user registration
new_user = {
    'username': 'test_user_123',
    'email': 'testuser@example.com',
    'password': 'TestPass123!',
    'password2': 'TestPass123!',
    'first_name': 'Test',
    'last_name': 'User',
    'current_role': 'client',
    'location': 'Harare, Zimbabwe',
    'phone': '+263771111111'
}

print("Testing registration API endpoint...\n")
print(f"Registering new user: {new_user['username']}")

try:
    # Get CSRF token first
    session = requests.Session()
    session.get('http://127.0.0.1:8000/login/')
    csrf_token = session.cookies.get('csrftoken', '')
    
    # Attempt registration
    response = session.post(
        url,
        json=new_user,
        headers={
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token,
            'Referer': 'http://127.0.0.1:8000/login/'
        }
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("\n✅ SUCCESS - User registered successfully!")
        
        # Try logging in with new account
        print("\nTesting login with new account...")
        login_response = session.post(
            'http://127.0.0.1:8000/api/login/',
            json={'username': new_user['username'], 'password': new_user['password']},
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token,
                'Referer': 'http://127.0.0.1:8000/login/'
            }
        )
        
        print(f"Login Status: {login_response.status_code}")
        if login_response.status_code == 200:
            print("✅ Login with new account SUCCESSFUL!")
        else:
            print(f"❌ Login failed: {login_response.json()}")
    else:
        print(f"\n❌ FAILED - Registration failed")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "="*50)

# Test duplicate username
print("\nTesting duplicate username validation...")
try:
    duplicate_user = new_user.copy()
    duplicate_user['email'] = 'different@example.com'
    
    response = session.post(
        url,
        json=duplicate_user,
        headers={
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token,
            'Referer': 'http://127.0.0.1:8000/login/'
        }
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 400:
        print("✅ Duplicate username correctly rejected")
        print(f"Response: {response.json()}")
    else:
        print("❌ Duplicate validation failed")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "="*50)

# Test password mismatch
print("\nTesting password mismatch validation...")
try:
    mismatch_user = {
        'username': 'another_test_user',
        'email': 'another@example.com',
        'password': 'TestPass123!',
        'password2': 'DifferentPass123!',
        'first_name': 'Another',
        'last_name': 'User',
        'current_role': 'provider'
    }
    
    response = session.post(
        url,
        json=mismatch_user,
        headers={
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token,
            'Referer': 'http://127.0.0.1:8000/login/'
        }
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 400:
        print("✅ Password mismatch correctly rejected")
        print(f"Response: {response.json()}")
    else:
        print("❌ Password mismatch validation failed")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n\nRegistration Test Complete!")
