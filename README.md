# Vashandi Workers App - Django Full Stack Application

🛠️ A full-featured Django web application connecting clients with skilled workers in Zimbabwe.

## Features

- ✅ User authentication (Login/Register)
- ✅ Dual role support (Client/Provider) with toggle functionality
- ✅ Service listings with search and filtering
- ✅ Job posting system
- ✅ Reviews and ratings
- ✅ Real-time statistics dashboard
- ✅ RESTful API endpoints
- ✅ Responsive design with custom CSS styling
- ✅ Role-based access control

## Tech Stack

- **Backend**: Django 5.2.1
- **API**: Django REST Framework 3.16.0
- **Database**: SQLite (development)
- **Authentication**: Django Session Authentication
- **Frontend**: Vanilla JavaScript with Django Templates
- **Styling**: Custom CSS with dark theme

## Project Structure

```
Vashandi Workers App/
├── vashandi_project/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── workers/                    # Main application
│   ├── models.py              # Database models (User, Service, Job, Review, Message)
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # API views and template views
│   ├── urls.py                # URL routing
│   ├── admin.py               # Admin panel configuration
│   ├── templates/workers/     # HTML templates
│   │   ├── login.html        # Login/Register page
│   │   └── dashboard.html    # Main dashboard
│   └── migrations/            # Database migrations
├── dummydata.py               # Script to populate database with sample data
├── manage.py                  # Django management script
└── db.sqlite3                 # SQLite database
```

## Database Models

### User (Custom User Model)
- Extended Django AbstractUser
- Fields: current_role, phone, location, bio, avatar_initials
- Supports client/provider role switching

### Service
- Provider's service offerings
- Fields: category, title, description, price_per_hour, experience_years, response_time
- Calculated properties: average_rating, review_count, jobs_completed

### Job
- Jobs posted by clients
- Fields: client, assigned_provider, title, category, description, budget, location, deadline, status
- Status choices: open, in_progress, completed, cancelled

### Review
- Reviews for services
- Fields: service, reviewer, job, rating (1-5), comment, sentiment
- Auto-detect sentiment based on rating

### Message
- Communication between users
- Fields: sender, recipient, service, job, content, is_read

## API Endpoints

### Authentication
- `POST /api/register/` - User registration
- `POST /api/login/` - User login
- `GET /api/user/` - Get current user info
- `PATCH /api/toggle-role/` - Toggle user role (client/provider)

### Services
- `GET /api/services/` - List all services (supports filtering & search)
- `POST /api/services/` - Create new service (providers only)
- `GET /api/services/{id}/` - Service detail with reviews
- `GET /api/services/my_services/` - Current user's services
- `POST /api/services/{id}/contact/` - Contact service provider

### Jobs
- `GET /api/jobs/` - List all jobs (supports filtering)
- `POST /api/jobs/` - Post new job (clients only)
- `GET /api/jobs/{id}/` - Job detail
- `GET /api/jobs/my_jobs/` - Current user's posted jobs
- `GET /api/jobs/assigned_jobs/` - Jobs assigned to provider

### Reviews
- `GET /api/reviews/` - List reviews (filterable by service)
- `POST /api/reviews/` - Create review

### Messages
- `GET /api/messages/` - List user's messages
- `POST /api/messages/` - Send message
- `GET /api/messages/inbox/` - User's inbox
- `GET /api/messages/sent/` - User's sent messages
- `POST /api/messages/{id}/mark_read/` - Mark message as read

### Statistics
- `GET /api/stats/` - Dashboard statistics (role-based)

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Django (already installed globally)

### Installation

1. **Install dependencies**
   ```bash
   pip install djangorestframework django-cors-headers
   ```

2. **Run migrations**
   ```bash
   cd "c:\Users\bjmba\OneDrive\Desktop\Vashandi Workers App"
   python manage.py migrate
   ```

3. **Load dummy data**
   ```bash
   Get-Content dummydata.py | python manage.py shell
   ```

4. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   - Main app: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/
   - Login page: http://127.0.0.1:8000/login/

## User Accounts (Pre-loaded)

### Clients
- **Username**: `tendai_moyo` | **Password**: `password123`
- **Username**: `sarah_ncube` | **Password**: `password123`
- **Username**: `michael_banda` | **Password**: `password123`

### Providers
- **Username**: `john_phiri` | **Password**: `password123` (Plumber)
- **Username**: `david_moyo` | **Password**: `password123` (Electrician)
- **Username**: `james_ndlovu` | **Password**: `password123` (Carpenter)
- **Username**: `thomas_sibanda` | **Password**: `password123` (Painter)
- **Username**: `patrick_mlambo` | **Password**: `password123` (Emergency Plumber)
- **Username**: `emmanuel_chiweshe` | **Password**: `password123` (Solar Installer)
- **Username**: `gibson_nyathi` | **Password**: `password123` (Door/Window)
- **Username**: `admire_chigwedere` | **Password**: `password123` (Commercial Painter)

### Admin
- **Username**: `admin` | **Password**: `admin123`

## Usage

### As a Client
1. Login with a client account
2. Browse available services
3. Search and filter by category
4. View service details and reviews
5. Post new jobs
6. Toggle to provider mode to offer services

### As a Provider
1. Login with a provider account
2. View available job opportunities
3. Manage your services
4. Track completed jobs and ratings
5. Toggle to client mode to hire others

### Role Switching
- Click the toggle switch in the navigation bar
- Switch between "Client Mode" and "Provider Mode"
- Role preference is saved to the database
- Dashboard updates based on current role

## Features Explained

### Search & Filter
- Search by service title, description, or provider name
- Filter by category (Plumbing, Electrical, Carpentry, Painting, etc.)
- Real-time search results

### Reviews System
- 5-star rating system
- Automatic sentiment detection (positive/neutral/negative)
- Reviews linked to completed jobs
- Displays reviewer name and time posted

### Job Management
- Create jobs with title, category, description, budget, location, deadline
- Track job status (open, in_progress, completed, cancelled)
- Assign jobs to providers
- View job history

### Statistics Dashboard
**Client View:**
- Active Workers
- Jobs Posted
- Satisfaction Rate
- Support Availability

**Provider View:**
- Active Jobs
- Jobs Completed
- Average Rating
- Total Reviews

## Custom Styling

The application uses a custom dark theme with:
- Dark navy background (#0f172a)
- Blue gradient accents (#3b82f6 to #06b6d4)
- Glass morphism effects
- Smooth animations and transitions
- Responsive design for mobile devices

## Admin Panel

Access at `/admin/` with admin credentials to:
- Manage users, services, jobs, reviews, and messages
- View and edit all data
- Monitor system activity
- Configure site settings

## API Testing

You can test the API using tools like:
- **Browser**: Navigate to API endpoints directly
- **Postman**: Import and test endpoints
- **cURL**: Command-line testing
- **Django REST Framework browsable API**: Built-in interface

Example API call:
```bash
curl http://127.0.0.1:8000/api/services/
```

## Development Notes

- CSRF protection is enabled for forms
- Session-based authentication for API
- CORS configured for development (adjust for production)
- SQLite database for development (switch to PostgreSQL/MySQL for production)
- DEBUG mode is ON (turn off in production)

## Future Enhancements

- [ ] Real-time messaging with WebSockets
- [ ] Payment integration
- [ ] Email notifications
- [ ] File uploads for service portfolios
- [ ] Advanced search with location-based filtering
- [ ] Mobile app (React Native/Flutter)
- [ ] Provider verification system
- [ ] In-app chat support
- [ ] Booking calendar integration

## Troubleshooting

### Database Issues
```bash
# Reset database
python manage.py flush
python manage.py migrate
Get-Content dummydata.py | python manage.py shell
```

### Port Already in Use
```bash
# Use a different port
python manage.py runserver 8080
```

### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic
```

## Security Notes

⚠️ **For Development Only**
- Change SECRET_KEY in production
- Set DEBUG = False in production
- Configure ALLOWED_HOSTS properly
- Use environment variables for sensitive data
- Enable HTTPS in production
- Implement rate limiting for APIs
- Use strong passwords
- Configure CORS properly

## Support

For issues or questions:
- Check the Django documentation: https://docs.djangoproject.com/
- Django REST Framework docs: https://www.django-rest-framework.org/
- Create an issue in the project repository

## License

This project is for educational purposes.

---

**Built with ❤️ using Django**

Developed: November 2025
Version: 1.0.0
