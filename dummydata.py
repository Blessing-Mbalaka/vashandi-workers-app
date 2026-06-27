"""
Dummy data generator for Vashandi Workers App.

Preferred command:
    python manage.py seed_demo_data

Fallback shell method:
    python manage.py shell -c "exec(open('dummydata.py').read())"
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from workers.models import (
    Country, Job, ProjectDispute, ProjectPhase, ProjectTask, ProjectTracker,
    Review, Service, TradeCategory,
)

User = get_user_model()

DEFAULT_PASSWORD = "password123"


def upsert_user(user_data):
    country = Country.objects.filter(code=user_data.get("country_code", "ZW")).first()
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
            "country": country,
            "verification_status": "approved",
        },
    )
    user.set_password(DEFAULT_PASSWORD)
    user.save()
    return user


def upsert_admin_user():
    admin_country = Country.objects.filter(code="ZW").first()
    admin_user, _ = User.objects.update_or_create(
        username="platform_admin",
        defaults={
            "email": "admin@vashandi.local",
            "first_name": "Platform",
            "last_name": "Admin",
            "current_role": "both",
            "account_type": "individual",
            "location": "Harare, Zimbabwe",
            "phone": "+263770000001",
            "country": admin_country,
            "verification_status": "approved",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )
    admin_user.set_password("AdminPass123!")
    admin_user.save()
    return admin_user


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
            "category_ref": TradeCategory.objects.filter(slug=service_data["category"]).first(),
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
            "category_ref": TradeCategory.objects.filter(slug=job_data["category"]).first(),
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


def upsert_project_tracker(tracker_data):
    tracker, _ = ProjectTracker.objects.update_or_create(
        job=tracker_data["job"],
        defaults={
            "client": tracker_data["client"],
            "provider": tracker_data["provider"],
            "title": tracker_data["title"],
            "overview": tracker_data["overview"],
            "status": tracker_data["status"],
            "client_signature": tracker_data.get("client_signature", ""),
            "provider_signature": tracker_data.get("provider_signature", ""),
            "client_signed_at": tracker_data.get("client_signed_at"),
            "provider_signed_at": tracker_data.get("provider_signed_at"),
            "approved_at": tracker_data.get("approved_at"),
        },
    )
    return tracker


def upsert_project_phase(phase_data):
    phase, _ = ProjectPhase.objects.update_or_create(
        tracker=phase_data["tracker"],
        sequence=phase_data["sequence"],
        defaults={
            "title": phase_data["title"],
            "client_scope": phase_data["client_scope"],
            "provider_plan": phase_data.get("provider_plan", ""),
            "provider_notes": phase_data.get("provider_notes", ""),
            "planned_amount": phase_data.get("planned_amount", Decimal("0.00")),
            "plan_status": phase_data.get("plan_status", "draft"),
            "execution_status": phase_data.get("execution_status", "not_started"),
            "fund_release_status": phase_data.get("fund_release_status", "locked"),
            "provider_evidence_notes": phase_data.get("provider_evidence_notes", ""),
            "payment_proof_notes": phase_data.get("payment_proof_notes", ""),
            "payment_proof_uploaded_at": phase_data.get("payment_proof_uploaded_at"),
            "payment_acknowledgement_signature": phase_data.get("payment_acknowledgement_signature", ""),
            "payment_acknowledgement_notes": phase_data.get("payment_acknowledgement_notes", ""),
            "payment_acknowledged_at": phase_data.get("payment_acknowledged_at"),
            "client_approval_signature": phase_data.get("client_approval_signature", ""),
            "provider_submission_signature": phase_data.get("provider_submission_signature", ""),
            "provider_submitted_at": phase_data.get("provider_submitted_at"),
            "client_approved_at": phase_data.get("client_approved_at"),
        },
    )
    return phase


def upsert_project_task(task_data):
    task, _ = ProjectTask.objects.update_or_create(
        phase=task_data["phase"],
        sequence=task_data["sequence"],
        defaults={
            "title": task_data["title"],
            "customer_definition": task_data["customer_definition"],
            "provider_execution_plan": task_data.get("provider_execution_plan", ""),
            "provider_description": task_data.get("provider_description", ""),
            "completion_notes": task_data.get("completion_notes", ""),
            "status": task_data.get("status", "client_defined"),
            "client_plan_signature": task_data.get("client_plan_signature", ""),
            "client_completion_signature": task_data.get("client_completion_signature", ""),
            "provider_updated_at": task_data.get("provider_updated_at"),
            "client_approved_at": task_data.get("client_approved_at"),
            "completed_at": task_data.get("completed_at"),
        },
    )
    return task


def upsert_project_dispute(dispute_data):
    dispute, _ = ProjectDispute.objects.update_or_create(
        tracker=dispute_data["tracker"],
        phase=dispute_data.get("phase"),
        task=dispute_data.get("task"),
        reason=dispute_data["reason"],
        defaults={
            "raised_by": dispute_data["raised_by"],
            "status": dispute_data.get("status", "open"),
            "admin_resolution": dispute_data.get("admin_resolution", ""),
            "resolved_by": dispute_data.get("resolved_by"),
            "resolved_at": dispute_data.get("resolved_at"),
        },
    )
    return dispute


def create_dummy_data():
    print("Creating dummy data for Vashandi Workers App...")
    print("Seeding users, services, jobs, reviews, and project tracker data...")

    clients = [
        {
            "username": "tendai_moyo",
            "email": "tendai@example.com",
            "first_name": "Tendai",
            "last_name": "Moyo",
            "current_role": "client",
            "location": "Harare, Zimbabwe",
            "phone": "+263771234567",
            "country_code": "ZW",
        },
        {
            "username": "sarah_ncube",
            "email": "sarah@example.com",
            "first_name": "Sarah",
            "last_name": "Ncube",
            "current_role": "client",
            "location": "Bulawayo, Zimbabwe",
            "phone": "+263772345678",
            "country_code": "ZW",
        },
        {
            "username": "michael_banda",
            "email": "michael@example.com",
            "first_name": "Michael",
            "last_name": "Banda",
            "current_role": "client",
            "location": "Harare, Zimbabwe",
            "phone": "+263773456789",
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
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
            "country_code": "ZW",
        },
    ]

    print("\nCreating users...")
    admin_user = upsert_admin_user()
    print(f"   Created admin: {admin_user.get_full_name()} ({admin_user.username})")
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

    print("\nCreating project tracker data...")
    active_job = created_jobs[2]
    tracker = upsert_project_tracker({
        "job": active_job,
        "client": active_job.client,
        "provider": active_job.assigned_provider,
        "title": "Home Office Bookshelf Project Tracker",
        "overview": "Track planning, fabrication, installation, and sign-off phase by phase so funds are only released after client approval.",
        "status": "active",
        "client_signature": "Tendai Moyo",
        "provider_signature": "James Ndlovu",
        "client_signed_at": timezone.now(),
        "provider_signed_at": timezone.now(),
        "approved_at": timezone.now(),
    })
    phase_one = upsert_project_phase({
        "tracker": tracker,
        "sequence": 1,
        "title": "Design Approval",
        "client_scope": "Agree on final bookshelf dimensions, shelf spacing, stain color, and fixing points.",
        "provider_plan": "Prepare a measured sketch, timber cut-list, finish samples, and installation method for approval.",
        "provider_notes": "Need wall measurements confirmed before cutting timber.",
        "planned_amount": Decimal("250.00"),
        "plan_status": "approved",
        "execution_status": "approved",
        "fund_release_status": "released",
        "payment_proof_notes": "Bank transfer proof uploaded for the design approval deposit.",
        "payment_proof_uploaded_at": timezone.now() - timedelta(days=4),
        "payment_acknowledgement_signature": "James Ndlovu",
        "payment_acknowledgement_notes": "Deposit received and cleared.",
        "payment_acknowledged_at": timezone.now() - timedelta(days=4),
        "client_approval_signature": "Michael Banda",
        "provider_submission_signature": "James Ndlovu",
        "provider_submitted_at": timezone.now() - timedelta(days=5),
        "client_approved_at": timezone.now() - timedelta(days=4),
    })
    phase_two = upsert_project_phase({
        "tracker": tracker,
        "sequence": 2,
        "title": "Fabrication and Installation",
        "client_scope": "Build, sand, stain, transport, install, and leave the unit ready for use.",
        "provider_plan": "Fabricate off-site, do a dry fit, then final install and touch-ups at client premises.",
        "provider_notes": "Installation to happen once Phase 1 sign-off is locked.",
        "planned_amount": Decimal("550.00"),
        "plan_status": "approved",
        "execution_status": "in_progress",
        "fund_release_status": "locked",
        "client_approval_signature": "Michael Banda",
        "client_approved_at": timezone.now() - timedelta(days=2),
    })
    task_one = upsert_project_task({
        "phase": phase_one,
        "sequence": 1,
        "title": "Confirm wall measurements",
        "customer_definition": "Client confirms the final install wall and preferred bookshelf width/height.",
        "provider_execution_plan": "Visit site, measure twice, and prepare scaled notes.",
        "provider_description": "Measurements and fixing points captured.",
        "completion_notes": "Client agreed final measurements on site.",
        "status": "completed",
        "client_plan_signature": "Michael Banda",
        "client_completion_signature": "Michael Banda",
        "provider_updated_at": timezone.now() - timedelta(days=6),
        "client_approved_at": timezone.now() - timedelta(days=4),
        "completed_at": timezone.now() - timedelta(days=4),
    })
    task_two = upsert_project_task({
        "phase": phase_two,
        "sequence": 1,
        "title": "Cut and assemble bookshelf frame",
        "customer_definition": "Frame must match the approved design and support book weight safely.",
        "provider_execution_plan": "Cut all timber, assemble the frame, and pre-test load bearing in workshop.",
        "provider_description": "Frame assembly is underway in workshop.",
        "status": "in_progress",
        "client_plan_signature": "Michael Banda",
        "provider_updated_at": timezone.now() - timedelta(days=1),
    })
    upsert_project_task({
        "phase": phase_two,
        "sequence": 2,
        "title": "Install and final finishing",
        "customer_definition": "Install cleanly, align shelves, and leave no visible damage on walls or floor.",
        "provider_execution_plan": "Transport, mount securely, stain match, and finish on site.",
        "status": "approved_to_start",
        "client_plan_signature": "Michael Banda",
        "provider_updated_at": timezone.now() - timedelta(days=1),
        "client_approved_at": timezone.now() - timedelta(days=1),
    })
    upsert_project_dispute({
        "tracker": tracker,
        "phase": phase_two,
        "task": task_two,
        "raised_by": active_job.client,
        "reason": "Client wants admin review if stain finish does not match the approved sample before final release.",
        "status": "open",
    })
    print(f"   Created project tracker: {tracker.title}")

    print("\nDummy data creation complete.")
    print("\nSummary:")
    print(f"   - Users seeded: {len(created_clients) + len(created_providers)}")
    print("   - Admin users: 1")
    print(f"   - Clients: {len(created_clients)}")
    print(f"   - Providers: {len(created_providers)}")
    print(f"   - Services: {len(created_services)}")
    print(f"   - Jobs: {len(created_jobs)}")
    print(f"   - Reviews: {len(reviews_data)}")
    print("   - Project trackers: 1")
    print("   - Project phases: 2")
    print("   - Project disputes: 1")
    print(f"\nAll seeded users have password: {DEFAULT_PASSWORD}")
    print("\nYou can now log in with:")
    print(f"   Client: tendai_moyo / {DEFAULT_PASSWORD}")
    print(f"   Provider: john_phiri / {DEFAULT_PASSWORD}")
    print("   Admin: platform_admin / AdminPass123!")


if __name__ == "__main__":
    create_dummy_data()
