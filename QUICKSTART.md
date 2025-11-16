# 🚀 Quick Start Guide - Vashandi Workers App

## Your Django app is ready! Follow these steps to start using it:

### 1. Server Status ✅
The development server is currently running at: **http://127.0.0.1:8000/**

### 2. Access the Application

#### Option A: Login Page (Start Here)
Open your browser and navigate to:
```
http://127.0.0.1:8000/login/
```

Try these pre-loaded accounts:
- **Client**: `tendai_moyo` / `password123`
- **Provider**: `john_phiri` / `password123`

#### Option B: Admin Panel
```
http://127.0.0.1:8000/admin/
```
- **Username**: `admin`
- **Password**: `admin123`

### 3. Main Features to Test

#### As a Client 👤
1. **Browse Services**
   - View 8 pre-loaded services (plumbing, electrical, carpentry, painting)
   - Use category filters
   - Search for specific services

2. **Post a Job**
   - Click "Post a Job" button
   - Fill in job details
   - Submit and view in dashboard stats

3. **View Service Details**
   - Click on any service card
   - Read reviews and ratings
   - View provider profile
   - Contact provider

4. **Switch to Provider Mode**
   - Click the toggle switch in the navigation
   - See provider-specific stats

#### As a Provider 🛠️
1. **Login** as `john_phiri` / `password123`
2. **View Stats**
   - See your jobs completed
   - Check your average rating
   - View total reviews

3. **Browse Job Opportunities**
   - Toggle affects the main view
   - See available jobs from clients

4. **Switch to Client Mode**
   - Toggle back to hire others

### 4. API Endpoints to Test

Open these URLs in your browser or use a tool like Postman:

#### Get All Services
```
http://127.0.0.1:8000/api/services/
```

#### Filter Services by Category
```
http://127.0.0.1:8000/api/services/?category=plumbing
```

#### Search Services
```
http://127.0.0.1:8000/api/services/?search=solar
```

#### Get Dashboard Stats
```
http://127.0.0.1:8000/api/stats/
```

#### Get All Jobs
```
http://127.0.0.1:8000/api/jobs/
```

#### Get All Reviews
```
http://127.0.0.1:8000/api/reviews/
```

### 5. Pre-loaded Data Summary

✅ **11 Users**
- 3 Clients
- 8 Providers
- 1 Admin

✅ **8 Services** across categories:
- 2 Plumbing services
- 2 Electrical services  
- 2 Carpentry services
- 2 Painting services

✅ **4 Jobs**
- 1 Open (Fix Leaking Kitchen Sink)
- 1 Open (Install Solar Panels)
- 1 In Progress (Build Custom Bookshelf)
- 1 Completed (Paint Living Room)

✅ **13 Reviews**
- All services have reviews
- Ratings range from 4-5 stars
- Mix of positive and neutral sentiment

### 6. Common Tasks

#### Register New User
1. Go to http://127.0.0.1:8000/login/
2. Click "Register" tab
3. Fill in the form
4. Choose role (Client or Provider)
5. Submit

#### Create a Service (as Provider)
Use the API or admin panel:
```python
# In Django shell or admin
POST /api/services/
{
    "category": "plumbing",
    "title": "My New Service",
    "description": "Service description",
    "price_per_hour": 45.00,
    "experience_years": 5,
    "response_time": "2h"
}
```

#### Leave a Review
```python
POST /api/reviews/
{
    "service": 1,
    "rating": 5,
    "comment": "Excellent work!"
}
```

### 7. Stop/Start the Server

#### Stop the Server
Press `CTRL + C` in the terminal where the server is running

#### Start the Server Again
```bash
cd "c:\Users\bjmba\OneDrive\Desktop\Vashandi Workers App"
python manage.py runserver
```

### 8. Useful Commands

#### Open Django Shell
```bash
python manage.py shell
```

#### Create a New Superuser
```bash
python manage.py createsuperuser
```

#### View All Users
```bash
python manage.py shell
>>> from workers.models import User
>>> User.objects.all()
```

#### Reload Dummy Data
```bash
Get-Content dummydata.py | python manage.py shell
```

### 9. File Structure Quick Reference

```
📁 Project Root
├── 📄 manage.py              # Django management
├── 📄 dummydata.py           # Sample data generator
├── 📄 db.sqlite3             # Database file
├── 📁 vashandi_project/      # Project settings
│   ├── settings.py           # Main settings
│   └── urls.py               # Root URL config
└── 📁 workers/               # Main app
    ├── models.py             # Database models
    ├── views.py              # Views & APIs
    ├── serializers.py        # API serializers
    ├── urls.py               # App URLs
    ├── admin.py              # Admin config
    └── templates/workers/    # HTML templates
        ├── login.html        # Login/Register
        └── dashboard.html    # Main dashboard
```

### 10. Troubleshooting

**Problem**: Can't access http://127.0.0.1:8000/
**Solution**: Make sure the server is running. Check the terminal for errors.

**Problem**: Login doesn't work
**Solution**: 
- Check you're using the correct credentials
- Make sure you ran the dummy data script
- Try: `tendai_moyo` / `password123`

**Problem**: No services showing
**Solution**: Reload dummy data:
```bash
Get-Content dummydata.py | python manage.py shell
```

**Problem**: API returns 403 Forbidden
**Solution**: Make sure you're logged in (session authentication)

### 11. Next Steps

Now that everything is set up:

1. ✅ Explore the dashboard UI
2. ✅ Test role switching
3. ✅ Post a job as a client
4. ✅ Browse services and reviews
5. ✅ Test the search functionality
6. ✅ Check out the admin panel
7. ✅ Experiment with the APIs

### 12. Need Help?

- 📖 Check README.md for detailed documentation
- 🔧 Use the admin panel to inspect data
- 🐛 Check terminal for error messages
- 📝 Review the code in models.py and views.py

---

**🎉 Enjoy your fully functional Django Workers App!**

All users share password: `password123`
Admin credentials: `admin` / `admin123`
