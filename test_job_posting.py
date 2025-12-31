import requests
import json

print("Testing Job Posting API...\n")

# First, login as a client
session = requests.Session()

# Get CSRF token
login_page = session.get('http://127.0.0.1:8000/login/')
csrf_token = session.cookies.get('csrftoken', '')

# Login
login_data = {'username': 'tendai_moyo', 'password': 'password123'}
login_response = session.post(
    'http://127.0.0.1:8000/api/login/',
    json=login_data,
    headers={
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
)

print(f"Login Status: {login_response.status_code}")
if login_response.status_code == 200:
    print(f"✅ Logged in as: {login_response.json()['user']['username']}\n")
else:
    print(f"❌ Login failed: {login_response.json()}\n")
    exit()

# Now try to post a job
job_data = {
    'title': 'Need Plumbing Repair',
    'category': 'plumbing',
    'description': 'Broken pipe in the kitchen, needs urgent repair',
    'budget': '150.00',
    'location': 'Harare, Zimbabwe',
    'deadline': '2025-12-31'
}

print("Posting Job with data:")
print(json.dumps(job_data, indent=2))
print()

job_response = session.post(
    'http://127.0.0.1:8000/api/jobs/',
    json=job_data,
    headers={
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
)

print(f"Job Posting Status: {job_response.status_code}")
print(f"Response:")
print(json.dumps(job_response.json(), indent=2))

if job_response.status_code in [200, 201]:
    print("\n✅ Job posted successfully!")
else:
    print("\n❌ Job posting failed!")
