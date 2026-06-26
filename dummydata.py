"""
Dummy data generator for Vashandi Workers App.

Run this script using:
    python manage.py shell < dummydata.py

Or in the shell:
    exec(open('dummydata.py').read())
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from workers.models import Job, Review, Service

User = get_user_model()

DEFAULT_PASSWORD = "password123"


def upsert_user(user_data):
    user, _ = User.objects.update_or_create(
        username=user_data["username"],
        defaults={
            "email": user_data["email"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "current_role": user_data["current_role"],
            "location": user_data["location"],
            "phone": user_data["phone"],
            "bio": user_data.get("bio", ""),
        },
    )
    user.set_password(DEFAULT_PASSWORD)
    user.save()
    return user


def upsert_service(service_data):
    service, _ = Service.objects.update_or_create(
        provider=service_data["provider"],
        title=service_data["title"],
        defaults={
            "category": service_data["category"],
            "description": service_data["description"],
            "price_per_hour": service_data["price_per_hour"],
            "experience_years": service_data["experience_years"],
            "response_time": service_data["response_time"],
            "is_active": True,
        },
    )
    return service


def upsert_job(job_data):
    job, _ = Job.objects.update_or_create(
        client=job_data["client"],
        title=job_data["title"],
        defaults={
            "category": job_data["category"],
            "description": job_data["description"],
            "budget": job_data["budget"],
            "location": job_data["location"],
            "status": job_data["status"],
            "deadline": job_data["deadline"],
            "assigned_provider": job_data.get("assigned_provider"),
            "service": job_data.get("service"),
        },
    )
    return job


def upsert_review(review_data):
    review, _ = Review.objects.update_or_create(
        service=review_data["service"],
        reviewer=review_data["reviewer"],
        job=review_data.get("job"),
        defaults={
            "rating": review_data["rating"],
            "comment": review_data["comment"],
            "sentiment": review_data["sentiment"],
        },
    )
    return review


def create_dummy_data():
    print("Creating dummy data for Vashandi Workers App...")
    print("Seeding users, services, jobs, and reviews...")

    clients = [
        {
            "username": "tendai_moyo",
            "email": "tendai@example.com",
            "first_name": "Tendai",
            "last_name": "Moyo",
            "current_role": "client",
            "location": "Harare, Zimbabwe",
            "phone": "+263771234567",
        },
        {
            "username": "sarah_ncube",
            "email": "sarah@example.com",
            "first_name": "Sarah",
            "last_name": "Ncube",
            "current_role": "client",
            "location": "Bulawayo, Zimbabwe",
            "phone": "+263772345678",
        },
        {
            "username": "michael_banda",
            "email": "michael@example.com",
            "first_name": "Michael",
            "last_name": "Banda",
            "current_role": "client",
            "location": "Harare, Zimbabwe",
            "phone": "+263773456789",
        },
    ]

    providers = [
        {
            "username": "john_phiri",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Phiri",
            "current_role": "provider",
            "location": "Harare, Zimbabwe",
            "phone": "+263774567890",
            "bio": "Expert plumber with 8 years of experience",
        },
        {
            "username": "david_moyo",
            "email": "david@example.com",
            "first_name": "David",
            "last_name": "Moyo",
            "current_role": "provider",
            "location": "Bulawayo, Zimbabwe",
            "phone": "+263775678901",
            "bio": "Certified electrician with 6 years of experience",
        },
        {
            "username": "james_ndlovu",
            "email": "james@example.com",
            "first_name": "James",
            "last_name": "Ndlovu",
            "current_role": "provider",
            "location": "Harare, Zimbabwe",
            "phone": "+263776789012",
            "bio": "Skilled carpenter specializing in custom furniture",
        },
        {
            "username": "thomas_sibanda",
            "email": "thomas@example.com",
            "first_name": "Thomas",
            "last_name": "Sibanda",
            "current_role": "provider",
            "location": "Mutare, Zimbabwe",
            "phone": "+263777890123",
            "bio": "Professional painter with 5 years of experience",
        },
        {
            "username": "patrick_mlambo",
            "email": "patrick@example.com",
            "first_name": "Patrick",
            "last_name": "Mlambo",
            "current_role": "provider",
            "location": "Gweru, Zimbabwe",
            "phone": "+263778901234",
            "bio": "24/7 emergency plumbing services",
        },
        {
            "username": "emmanuel_chiweshe",
            "email": "emmanuel@example.com",
            "first_name": "Emmanuel",
            "last_name": "Chiweshe",
            "current_role": "provider",
            "location": "Harare, Zimbabwe",
            "phone": "+263779012345",
            "bio": "Solar panel installation specialist",
        },
        {
            "username": "gibson_nyathi",
            "email": "gibson@example.com",
            "first_name": "Gibson",
            "last_name": "Nyathi",
            "current_role": "provider",
            "location": "Kwekwe, Zimbabwe",
            "phone": "+263770123456",
            "bio": "Door and window installation expert",
        },
        {
            "username": "admire_chigwedere",
            "email": "admire@example.com",
            "first_name": "Admire",
            "last_name": "Chigwedere",
            "current_role": "provider",
            "location": "Harare, Zimbabwe",
            "phone": "+263771234560",
            "bio": "Commercial painting services specialist",
        },
    ]

    print("\nCreating users...")
    created_clients = []
    for client_data in clients:
        user = upsert_user(client_data)
        created_clients.append(user)
        print(f"   Created client: {user.get_full_name()}")

    print("\nCreating providers...")
    created_providers = []
    for provider_data in providers:
        user = upsert_user(provider_data)
        created_providers.append(user)
        print(f"   Created provider: {user.get_full_name()}")

    print("\nCreating services...")
    services_data = [
        {
            "provider": created_providers[0],
            "category": "plumbing",
            "title": "Professional Plumbing Services",
            "description": "Expert plumber with 8 years of experience. Specializing in residential and commercial plumbing repairs, installations, and maintenance. Available for emergency callouts.",
            "price_per_hour": Decimal("50.00"),
            "experience_years": 8,
            "response_time": "2h",
        },
        {
            "provider": created_providers[1],
            "category": "electrical",
            "title": "Licensed Electrician Services",
            "description": "Certified electrician offering comprehensive electrical services including wiring, installations, repairs, and safety inspections. Licensed and insured.",
            "price_per_hour": Decimal("60.00"),
            "experience_years": 6,
            "response_time": "1h",
        },
        {
            "provider": created_providers[2],
            "category": "carpentry",
            "title": "Custom Carpentry & Furniture",
            "description": "Skilled carpenter specializing in custom furniture, cabinets, and woodwork. Quality craftsmanship with attention to detail.",
            "price_per_hour": Decimal("45.00"),
            "experience_years": 10,
            "response_time": "3h",
        },
        {
            "provider": created_providers[3],
            "category": "painting",
            "title": "Interior & Exterior Painting",
            "description": "Professional painter with expertise in both residential and commercial projects. Quality finishes and clean workmanship guaranteed.",
            "price_per_hour": Decimal("35.00"),
            "experience_years": 5,
            "response_time": "4h",
        },
        {
            "provider": created_providers[4],
            "category": "plumbing",
            "title": "Emergency Plumbing Services",
            "description": "24/7 emergency plumbing services. Fast response times for urgent repairs, leaks, and installations.",
            "price_per_hour": Decimal("55.00"),
            "experience_years": 7,
            "response_time": "30min",
        },
        {
            "provider": created_providers[5],
            "category": "electrical",
            "title": "Solar Panel Installation",
            "description": "Specialized in solar panel installation and maintenance. Helping homes and businesses go green with renewable energy solutions.",
            "price_per_hour": Decimal("70.00"),
            "experience_years": 4,
            "response_time": "2h",
        },
        {
            "provider": created_providers[6],
            "category": "carpentry",
            "title": "Door & Window Installation",
            "description": "Expert in door and window installations, repairs, and custom frames. Precision work with quality materials.",
            "price_per_hour": Decimal("40.00"),
            "experience_years": 9,
            "response_time": "3h",
        },
        {
            "provider": created_providers[7],
            "category": "painting",
            "title": "Commercial Painting Services",
            "description": "Specializing in large-scale commercial painting projects. Experienced team with professional equipment.",
            "price_per_hour": Decimal("38.00"),
            "experience_years": 6,
            "response_time": "5h",
        },
    ]

    created_services = []
    for service_data in services_data:
        service = upsert_service(service_data)
        created_services.append(service)
        print(f"   Created service: {service.title}")

    print("\nCreating jobs...")
    jobs_data = [
        {
            "client": created_clients[0],
            "title": "Fix Leaking Kitchen Sink",
            "category": "plumbing",
            "description": "Kitchen sink has been leaking for a few days. Need it fixed urgently.",
            "budget": Decimal("100.00"),
            "location": "Harare, Zimbabwe",
            "status": "open",
            "deadline": date.today() + timedelta(days=7),
        },
        {
            "client": created_clients[1],
            "title": "Install Solar Panels",
            "category": "electrical",
            "description": "Looking to install solar panels on my rooftop to reduce electricity costs.",
            "budget": Decimal("5000.00"),
            "location": "Bulawayo, Zimbabwe",
            "status": "open",
            "deadline": date.today() + timedelta(days=30),
        },
        {
            "client": created_clients[2],
            "title": "Build Custom Bookshelf",
            "category": "carpentry",
            "description": "Need a custom-built bookshelf for my home office. Dimensions: 2m x 3m.",
            "budget": Decimal("800.00"),
            "location": "Harare, Zimbabwe",
            "status": "in_progress",
            "assigned_provider": created_providers[2],
            "service": created_services[2],
            "deadline": date.today() + timedelta(days=14),
        },
        {
            "client": created_clients[0],
            "title": "Paint Living Room",
            "category": "painting",
            "description": "Looking to repaint my living room. Room size is approximately 5m x 4m.",
            "budget": Decimal("400.00"),
            "location": "Harare, Zimbabwe",
            "status": "completed",
            "assigned_provider": created_providers[3],
            "service": created_services[3],
            "deadline": date.today() - timedelta(days=7),
        },
    ]

    created_jobs = []
    for job_data in jobs_data:
        job = upsert_job(job_data)
        created_jobs.append(job)
        print(f"   Created job: {job.title}")

    print("\nCreating reviews...")
    reviews_data = [
        {
            "service": created_services[0],
            "reviewer": created_clients[1],
            "rating": 5,
            "comment": "Excellent service! John fixed my leaking pipes quickly and professionally. Very satisfied with his work.",
            "sentiment": "positive",
        },
        {
            "service": created_services[0],
            "reviewer": created_clients[2],
            "rating": 5,
            "comment": "Highly recommend! Punctual, skilled, and fair pricing. Will definitely hire again.",
            "sentiment": "positive",
        },
        {
            "service": created_services[0],
            "reviewer": created_clients[0],
            "rating": 4,
            "comment": "Good work overall. Took a bit longer than expected but the quality was great.",
            "sentiment": "neutral",
        },
        {
            "service": created_services[1],
            "reviewer": created_clients[0],
            "rating": 5,
            "comment": "David is fantastic! Fixed our electrical issues safely and explained everything clearly.",
            "sentiment": "positive",
        },
        {
            "service": created_services[1],
            "reviewer": created_clients[1],
            "rating": 4,
            "comment": "Professional and knowledgeable. Pricing is fair for the quality of work.",
            "sentiment": "positive",
        },
        {
            "service": created_services[2],
            "reviewer": created_clients[2],
            "rating": 5,
            "comment": "Beautiful custom cabinets! James exceeded our expectations with his craftsmanship.",
            "sentiment": "positive",
        },
        {
            "service": created_services[2],
            "reviewer": created_clients[0],
            "rating": 5,
            "comment": "Outstanding work! The bookshelf is exactly what I wanted. Highly recommended.",
            "sentiment": "positive",
            "job": created_jobs[2],
        },
        {
            "service": created_services[3],
            "reviewer": created_clients[0],
            "rating": 5,
            "comment": "Transformed our home beautifully! Very neat and professional work.",
            "sentiment": "positive",
            "job": created_jobs[3],
        },
        {
            "service": created_services[3],
            "reviewer": created_clients[1],
            "rating": 4,
            "comment": "Good job, though had to point out a few spots that needed touch-ups.",
            "sentiment": "neutral",
        },
        {
            "service": created_services[4],
            "reviewer": created_clients[2],
            "rating": 5,
            "comment": "Saved us during a plumbing emergency! Very fast response and excellent work.",
            "sentiment": "positive",
        },
        {
            "service": created_services[5],
            "reviewer": created_clients[1],
            "rating": 5,
            "comment": "Professional solar installation. Our electricity bills have dropped significantly!",
            "sentiment": "positive",
        },
        {
            "service": created_services[6],
            "reviewer": created_clients[0],
            "rating": 4,
            "comment": "Good installation work. Doors fit perfectly and look great.",
            "sentiment": "positive",
        },
        {
            "service": created_services[7],
            "reviewer": created_clients[2],
            "rating": 5,
            "comment": "Completed our office painting on time and within budget. Very happy!",
            "sentiment": "positive",
        },
    ]

    for review_data in reviews_data:
        review = upsert_review(review_data)
        print(f"   Created review: {review.rating}/5 for {review.service.title}")

    print("\nDummy data creation complete.")
    print("\nSummary:")
    print(f"   - Users seeded: {len(created_clients) + len(created_providers)}")
    print(f"   - Clients: {len(created_clients)}")
    print(f"   - Providers: {len(created_providers)}")
    print(f"   - Services: {len(created_services)}")
    print(f"   - Jobs: {len(created_jobs)}")
    print(f"   - Reviews: {len(reviews_data)}")
    print(f"\nAll seeded users have password: {DEFAULT_PASSWORD}")
    print("\nYou can now log in with:")
    print(f"   Client: tendai_moyo / {DEFAULT_PASSWORD}")
    print(f"   Provider: john_phiri / {DEFAULT_PASSWORD}")


create_dummy_data()
