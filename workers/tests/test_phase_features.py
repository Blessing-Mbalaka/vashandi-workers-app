from django.test import TestCase
from django.test import RequestFactory
from django.urls import reverse
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.contrib.auth.models import AnonymousUser
import json
from rest_framework.test import APIClient
from django.utils import timezone

from workers.middleware import FrontendSafeExceptionMiddleware
from workers.models import (
    User, Service, Job, Message, Bid, Notification, Review, RFQ, Invoice,
    TradeCategory, Country, ProjectTracker, ProjectPhase, ProjectTask, ProjectDispute,
)


class PhaseFeatureTests(TestCase):
    def setUp(self):
        self.zimbabwe, _ = Country.objects.get_or_create(
            name='Zimbabwe',
            code='ZW',
            defaults={
                'currency_code': 'USD',
                'currency_name': 'United States Dollar',
                'currency_symbol': '$',
                'phone_code': '+263'
            }
        )
        self.client_user = User.objects.create_user(
            username='client', password='pass123', first_name='Client', last_name='User', current_role='client',
            country=self.zimbabwe, verification_status='approved'
        )
        self.provider_user = User.objects.create_user(
            username='provider', password='pass123', first_name='Provider', last_name='User', current_role='provider',
            country=self.zimbabwe, verification_status='approved'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin', password='pass123', email='admin@example.com'
        )
        self.home_trade, _ = TradeCategory.objects.get_or_create(name='Home Services', slug='home-services')
        self.plumbing_category, _ = TradeCategory.objects.get_or_create(
            name='Plumbing',
            slug='plumbing',
            defaults={'parent': self.home_trade}
        )
        if self.plumbing_category.parent_id != self.home_trade.id:
            self.plumbing_category.parent = self.home_trade
            self.plumbing_category.save(update_fields=['parent'])
        self.service = Service.objects.create(
            provider=self.provider_user,
            category='plumbing',
            category_ref=self.plumbing_category,
            title='Pipe Fix',
            description='Fix leaky pipes',
            price_per_hour=50,
            experience_years=5
        )
        self.job = Job.objects.create(
            client=self.client_user,
            title='Kitchen leak',
            category='plumbing',
            category_ref=self.plumbing_category,
            description='Leak in the kitchen sink',
            budget=120,
            location='Harare',
            deadline=timezone.now().date(),
            status='open'
        )
        self.api_client = APIClient()
        self.request_factory = RequestFactory()

    def authenticate(self, user):
        self.api_client.force_authenticate(user=user)

    def test_message_conversation_endpoint(self):
        Message.objects.create(
            sender=self.client_user,
            recipient=self.provider_user,
            service=self.service,
            content='Hello there!'
        )
        self.authenticate(self.provider_user)
        response = self.api_client.get('/api/messages/conversations/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['user_name'], self.client_user.get_full_name())
        self.assertEqual(payload[0]['service_id'], self.service.id)
        self.assertEqual(payload[0]['service_title'], self.service.title)

    def test_category_tree_endpoint(self):
        self.authenticate(self.client_user)
        response = self.api_client.get('/api/categories/')
        self.assertEqual(response.status_code, 200)
        raw_payload = response.json()
        payload = raw_payload if isinstance(raw_payload, list) else raw_payload.get('results', [])
        self.assertEqual(payload[0]['name'], 'Home Services')
        self.assertEqual(payload[0]['children'][0]['slug'], 'plumbing')

    def test_country_endpoint_returns_african_country_data(self):
        response = self.api_client.get('/api/countries/')
        self.assertEqual(response.status_code, 200)
        raw_payload = response.json()
        payload = raw_payload if isinstance(raw_payload, list) else raw_payload.get('results', [])
        self.assertGreater(len(payload), 0)
        self.assertIn('currency_code', payload[0])
        self.assertTrue(Country.objects.filter(code='ZW', currency_code='USD').exists())

    def test_dashboard_stats_separates_workers_companies_and_services(self):
        company_provider = User.objects.create_user(
            username='company-provider',
            password='pass123',
            first_name='Company',
            last_name='Provider',
            current_role='provider',
            account_type='company',
            company_name='Build Better Ltd',
            country=self.zimbabwe,
            verification_status='approved',
        )
        Service.objects.create(
            provider=company_provider,
            category='plumbing',
            category_ref=self.plumbing_category,
            title='Corporate Plumbing Team',
            description='Commercial plumbing support',
            price_per_hour=95,
            experience_years=9,
            is_active=True,
        )

        self.authenticate(self.client_user)
        response = self.api_client.get('/api/stats/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['active_workers'], 1)
        self.assertEqual(payload['active_companies'], 1)
        self.assertEqual(payload['active_providers_total'], 2)
        self.assertEqual(payload['active_services'], 2)

    def test_pending_verification_user_cannot_login_until_approved(self):
        pending_document = SimpleUploadedFile('company-documents.pdf', b'filecontent', content_type='application/pdf')
        register_response = self.api_client.post('/api/register/', {
            'username': 'pending-user',
            'email': 'pending@example.com',
            'password': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'Pending',
            'last_name': 'User',
            'current_role': 'provider',
            'account_type': 'company',
            'company_name': 'Pending Services Ltd',
            'country': self.zimbabwe.id,
            'location': 'Harare',
            'verification_document': pending_document,
        })
        self.assertEqual(register_response.status_code, 201)

        blocked_login = self.api_client.post('/api/login/', {
            'username': 'pending-user',
            'password': 'complexpass123',
        }, format='json')
        self.assertEqual(blocked_login.status_code, 403)
        self.assertIn('pending admin verification', blocked_login.json()['error'])
        self.assertIn('verification documents', blocked_login.json()['error'])

        user = User.objects.get(username='pending-user')
        user.verification_status = 'approved'
        user.save(update_fields=['verification_status'])

        allowed_login = self.api_client.post('/api/login/', {
            'username': 'pending-user',
            'password': 'complexpass123',
        }, format='json')
        self.assertEqual(allowed_login.status_code, 200)

    def test_company_registration_requires_company_documents_message(self):
        register_response = self.api_client.post('/api/register/', {
            'username': 'company-no-doc',
            'email': 'company-no-doc@example.com',
            'password': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'Company',
            'last_name': 'Owner',
            'current_role': 'provider',
            'account_type': 'company',
            'company_name': 'BuildRight Projects',
            'country': self.zimbabwe.id,
            'location': 'Harare',
        })
        self.assertEqual(register_response.status_code, 400)
        self.assertIn('Company verification documents are required.', register_response.json()['verification_document'][0])

    def test_individual_registration_requires_certified_id_message(self):
        register_response = self.api_client.post('/api/register/', {
            'username': 'individual-no-doc',
            'email': 'individual-no-doc@example.com',
            'password': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'Indy',
            'last_name': 'Worker',
            'current_role': 'provider',
            'account_type': 'individual',
            'country': self.zimbabwe.id,
            'location': 'Harare',
        })
        self.assertEqual(register_response.status_code, 400)
        self.assertIn('Certified ID document is required.', register_response.json()['verification_document'][0])

    def test_job_creation_accepts_category_ref(self):
        self.authenticate(self.client_user)
        response = self.api_client.post('/api/jobs/', {
            'title': 'Install shower',
            'category_ref': self.plumbing_category.id,
            'description': 'Need a new shower mixer installed.',
            'budget': '210.00',
            'location': 'Harare',
            'deadline': str(timezone.now().date()),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        created_job = Job.objects.get(id=response.json()['id'])
        self.assertEqual(created_job.category_ref, self.plumbing_category)
        self.assertEqual(created_job.category, 'plumbing')

    def test_admin_overview_and_user_management_endpoints(self):
        pending_document = SimpleUploadedFile('company-documents.pdf', b'filecontent', content_type='application/pdf')
        pending_user = User.objects.create_user(
            username='awaiting-review',
            email='awaiting@example.com',
            password='complexpass123',
            first_name='Awaiting',
            last_name='Review',
            current_role='provider',
            account_type='company',
            company_name='Awaiting Review Ltd',
            country=self.zimbabwe,
            verification_status='pending',
            verification_document=pending_document,
        )

        self.authenticate(self.admin_user)
        overview_response = self.api_client.get('/api/admin/overview/')
        self.assertEqual(overview_response.status_code, 200)
        overview = overview_response.json()
        self.assertGreaterEqual(overview['verification']['pending'], 1)

        users_response = self.api_client.get('/api/admin/users/?verification_status=pending')
        self.assertEqual(users_response.status_code, 200)
        self.assertTrue(any(user['username'] == 'awaiting-review' for user in users_response.json()))

        update_response = self.api_client.patch(
            f'/api/admin/users/{pending_user.id}/',
            {
                'verification_status': 'approved',
                'verification_notes': 'Approved in automated admin test.',
                'current_role': 'both',
                'is_staff': True,
            },
            format='json'
        )
        self.assertEqual(update_response.status_code, 200)
        pending_user.refresh_from_db()
        self.assertEqual(pending_user.verification_status, 'approved')
        self.assertEqual(pending_user.current_role, 'both')
        self.assertTrue(pending_user.is_staff)
        self.assertEqual(pending_user.reviewed_by, self.admin_user)

    def test_admin_portal_requires_superuser(self):
        self.client.force_login(self.client_user)
        forbidden = self.client.get('/admin-portal/')
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_login(self.admin_user)
        allowed = self.client.get('/admin-portal/')
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, 'Admin Portal')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ERROR_ALERT_RECIPIENTS=['bjmbalaka@gmail.com'],
        DEFAULT_FROM_EMAIL='no-reply@example.com',
    )
    def test_exception_middleware_redirects_frontend_and_emails_reference(self):
        request = self.request_factory.get('/jobs/123/')
        request.user = AnonymousUser()

        middleware = FrontendSafeExceptionMiddleware(lambda req: (_ for _ in ()).throw(ValueError('boom')))
        response = middleware(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/we-hit-a-snag/?ref=', response.url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('bjmbalaka@gmail.com', mail.outbox[0].to)
        self.assertIn('/jobs/123/', mail.outbox[0].body)
        self.assertIn('ValueError: boom', mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ERROR_ALERT_RECIPIENTS=['bjmbalaka@gmail.com'],
        DEFAULT_FROM_EMAIL='no-reply@example.com',
    )
    def test_exception_middleware_hides_api_details_and_emails_reference(self):
        request = self.request_factory.get('/api/services/', HTTP_ACCEPT='application/json')
        request.user = AnonymousUser()

        middleware = FrontendSafeExceptionMiddleware(lambda req: (_ for _ in ()).throw(RuntimeError('api failure')))
        response = middleware(request)

        self.assertEqual(response.status_code, 500)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertEqual(payload['error'], 'We hit a snag. The issue has been logged and the team has been notified.')
        self.assertTrue(payload['reference'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('RuntimeError: api failure', mail.outbox[0].body)

    def test_project_tracker_phase_task_and_dispute_flow(self):
        self.job.assigned_provider = self.provider_user
        self.job.status = 'in_progress'
        self.job.save(update_fields=['assigned_provider', 'status'])

        self.authenticate(self.client_user)
        tracker_response = self.api_client.post('/api/project-trackers/', {
            'job': self.job.id,
            'title': 'Kitchen Repair Tracker',
            'overview': 'Track plumbing tasks by phase.',
            'client_signature': 'Client User',
        }, format='json')
        self.assertEqual(tracker_response.status_code, 201)
        tracker_id = tracker_response.json()['id']

        phase_response = self.api_client.post('/api/project-phases/', {
            'tracker': tracker_id,
            'sequence': 1,
            'title': 'Leak Inspection',
            'client_scope': 'Inspect sink and isolate the root cause.',
            'planned_amount': '40.00',
        }, format='json')
        self.assertEqual(phase_response.status_code, 201)
        phase_id = phase_response.json()['id']

        task_response = self.api_client.post('/api/project-tasks/', {
            'phase': phase_id,
            'sequence': 1,
            'title': 'Inspect trap and joints',
            'customer_definition': 'Check visible leaks and report findings.',
        }, format='json')
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.json()['id']

        self.authenticate(self.provider_user)
        plan_phase = self.api_client.post(f'/api/project-phases/{phase_id}/submit_plan/', {
            'provider_plan': 'Inspect all fittings, isolate leak source, and prepare a repair summary.',
            'provider_notes': 'Will bring testing tape and moisture detector.',
        }, format='json')
        self.assertEqual(plan_phase.status_code, 200)

        plan_task = self.api_client.post(f'/api/project-tasks/{task_id}/provider_plan/', {
            'provider_execution_plan': 'Tighten joints, check washers, and pressure-test afterward.',
            'provider_description': 'Inspection and immediate repair if the fault is minor.',
        }, format='json')
        self.assertEqual(plan_task.status_code, 200)

        self.authenticate(self.client_user)
        approve_phase = self.api_client.post(f'/api/project-phases/{phase_id}/approve_plan/', {'signature': 'Client User'}, format='json')
        self.assertEqual(approve_phase.status_code, 200)
        approve_task = self.api_client.post(f'/api/project-tasks/{task_id}/approve_plan/', {'signature': 'Client User'}, format='json')
        self.assertEqual(approve_task.status_code, 200)

        self.authenticate(self.provider_user)
        start_phase = self.api_client.post(f'/api/project-phases/{phase_id}/start_phase/')
        self.assertEqual(start_phase.status_code, 200)
        start_task = self.api_client.post(f'/api/project-tasks/{task_id}/start/')
        self.assertEqual(start_task.status_code, 200)
        submit_task = self.api_client.post(f'/api/project-tasks/{task_id}/submit_completion/', {
            'completion_notes': 'Inspection completed and leak source identified.',
        }, format='json')
        self.assertEqual(submit_task.status_code, 200)

        self.authenticate(self.client_user)
        approve_task_completion = self.api_client.post(f'/api/project-tasks/{task_id}/approve_completion/', {
            'signature': 'Client User',
        }, format='json')
        self.assertEqual(approve_task_completion.status_code, 200)

        self.authenticate(self.provider_user)
        submit_phase = self.api_client.post(f'/api/project-phases/{phase_id}/submit_completion/', {
            'provider_evidence_notes': 'Phase inspection and reporting completed.',
            'signature': 'Provider User',
        })
        self.assertEqual(submit_phase.status_code, 200)

        self.authenticate(self.client_user)
        approve_phase_completion = self.api_client.post(f'/api/project-phases/{phase_id}/approve_completion/', {
            'signature': 'Client User',
        }, format='json')
        self.assertEqual(approve_phase_completion.status_code, 200)

        payment_proof = SimpleUploadedFile('payment-proof.pdf', b'proof', content_type='application/pdf')
        payment_proof_response = self.api_client.post(f'/api/project-phases/{phase_id}/submit_payment_proof/', {
            'payment_proof_notes': 'Bank transfer receipt for approved phase.',
            'payment_proof_file': payment_proof,
        })
        self.assertEqual(payment_proof_response.status_code, 200)

        self.authenticate(self.provider_user)
        acknowledge_payment = self.api_client.post(f'/api/project-phases/{phase_id}/acknowledge_payment/', {
            'signature': 'Provider User',
            'payment_acknowledgement_notes': 'Payment received and matched to phase 1.',
        }, format='json')
        self.assertEqual(acknowledge_payment.status_code, 200)

        self.authenticate(self.client_user)
        dispute_response = self.api_client.post('/api/project-disputes/', {
            'tracker': tracker_id,
            'phase': phase_id,
            'task': task_id,
            'reason': 'Testing admin dispute handling for unresolved client concern.',
        }, format='json')
        self.assertEqual(dispute_response.status_code, 201)

        tracker = ProjectTracker.objects.get(id=tracker_id)
        phase = ProjectPhase.objects.get(id=phase_id)
        task = ProjectTask.objects.get(id=task_id)
        dispute = ProjectDispute.objects.get(tracker=tracker)
        self.assertEqual(tracker.status, 'disputed')
        self.assertEqual(phase.fund_release_status, 'held')
        self.assertEqual(task.status, 'disputed')
        self.assertEqual(dispute.status, 'open')

    def test_next_phase_waits_for_payment_acknowledgement(self):
        self.job.assigned_provider = self.provider_user
        self.job.status = 'in_progress'
        self.job.save(update_fields=['assigned_provider', 'status'])

        tracker = ProjectTracker.objects.create(
            job=self.job,
            client=self.client_user,
            provider=self.provider_user,
            title='Phase Gate Tracker',
            overview='Make sure next phase waits for payment acknowledgement.',
            status='active',
            client_signature='Client User',
            provider_signature='Provider User',
            client_signed_at=timezone.now(),
            provider_signed_at=timezone.now(),
            approved_at=timezone.now(),
        )
        phase_one = ProjectPhase.objects.create(
            tracker=tracker,
            sequence=1,
            title='Phase One',
            client_scope='Complete the first deliverable.',
            provider_plan='Deliver the first milestone.',
            planned_amount='50.00',
            plan_status='approved',
            execution_status='approved',
            fund_release_status='pending_release',
            provider_submitted_at=timezone.now(),
            client_approved_at=timezone.now(),
        )
        phase_two = ProjectPhase.objects.create(
            tracker=tracker,
            sequence=2,
            title='Phase Two',
            client_scope='Continue to second milestone.',
            provider_plan='Deliver the second milestone.',
            planned_amount='50.00',
            plan_status='approved',
        )

        self.authenticate(self.provider_user)
        blocked_start = self.api_client.post(f'/api/project-phases/{phase_two.id}/start_phase/')
        self.assertEqual(blocked_start.status_code, 400)
        self.assertIn('Previous phases must be paid and acknowledged', blocked_start.json()['error'])

        phase_one.fund_release_status = 'released'
        phase_one.payment_acknowledged_at = timezone.now()
        phase_one.save(update_fields=['fund_release_status', 'payment_acknowledged_at'])

        allowed_start = self.api_client.post(f'/api/project-phases/{phase_two.id}/start_phase/')
        self.assertEqual(allowed_start.status_code, 200)

    def test_invoice_can_be_downloaded_as_html(self):
        invoice = Invoice.objects.create(
            provider=self.provider_user,
            client=self.client_user,
            service=self.service,
            title='Kitchen Leak Invoice',
            scope_of_work='Inspect leak and replace damaged fittings.',
            line_items='Labour - 1\nParts - 1',
            subtotal='100.00',
            tax_amount='15.00',
            total_amount='115.00',
            notes='Pay within 7 days.',
            status='sent',
        )

        self.authenticate(self.client_user)
        response = self.api_client.get(f'/api/invoices/{invoice.id}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('Kitchen Leak Invoice', response.content.decode('utf-8'))

    def test_admin_can_resolve_dispute_and_restore_project_state(self):
        self.job.assigned_provider = self.provider_user
        self.job.status = 'in_progress'
        self.job.save(update_fields=['assigned_provider', 'status'])

        tracker = ProjectTracker.objects.create(
            job=self.job,
            client=self.client_user,
            provider=self.provider_user,
            title='Resolved Tracker',
            overview='Testing dispute restoration.',
            status='active',
            client_signature='Client User',
            provider_signature='Provider User',
            client_signed_at=timezone.now(),
            provider_signed_at=timezone.now(),
            approved_at=timezone.now(),
        )
        phase = ProjectPhase.objects.create(
            tracker=tracker,
            sequence=1,
            title='Inspection',
            client_scope='Inspect and report.',
            provider_plan='Inspect and send findings.',
            planned_amount='40.00',
            plan_status='approved',
            execution_status='approved',
            fund_release_status='released',
            payment_proof_notes='Proof already uploaded.',
            payment_proof_uploaded_at=timezone.now(),
            payment_acknowledgement_signature='Provider User',
            payment_acknowledgement_notes='Received.',
            payment_acknowledged_at=timezone.now(),
            client_approval_signature='Client User',
            provider_submission_signature='Provider User',
            provider_submitted_at=timezone.now(),
            client_approved_at=timezone.now(),
        )
        task = ProjectTask.objects.create(
            phase=phase,
            sequence=1,
            title='Inspect pipe joints',
            customer_definition='Check all visible joints.',
            provider_execution_plan='Inspect and pressure test.',
            completion_notes='Inspection completed.',
            status='completed',
            client_plan_signature='Client User',
            client_completion_signature='Client User',
            completed_at=timezone.now(),
            client_approved_at=timezone.now(),
        )

        self.authenticate(self.client_user)
        dispute_response = self.api_client.post('/api/project-disputes/', {
            'tracker': tracker.id,
            'phase': phase.id,
            'task': task.id,
            'reason': 'Client wants admin review.',
        }, format='json')
        self.assertEqual(dispute_response.status_code, 201)
        dispute_id = dispute_response.json()['id']

        self.authenticate(self.admin_user)
        resolve_response = self.api_client.post(f'/api/project-disputes/{dispute_id}/resolve/', {
            'status': 'dismissed',
            'admin_resolution': 'Complaint dismissed because the provider met the signed scope.',
        }, format='json')
        self.assertEqual(resolve_response.status_code, 200)

        tracker.refresh_from_db()
        phase.refresh_from_db()
        task.refresh_from_db()
        dispute = ProjectDispute.objects.get(id=dispute_id)
        self.assertEqual(dispute.status, 'dismissed')
        self.assertEqual(tracker.status, 'active')
        self.assertEqual(phase.execution_status, 'approved')
        self.assertEqual(phase.fund_release_status, 'released')
        self.assertEqual(task.status, 'completed')
        self.assertTrue(Notification.objects.filter(
            recipient=self.client_user,
            notification_type='dispute',
            title='Project dispute resolved',
        ).exists())

    def test_job_status_change_requires_owner(self):
        other_user = User.objects.create_user(username='other', password='pass123')
        self.authenticate(other_user)
        response = self.api_client.post(f'/api/jobs/{self.job.id}/change_status/', {'status': 'in_progress'})
        self.assertEqual(response.status_code, 403)

        self.authenticate(self.client_user)
        response = self.api_client.post(
            f'/api/jobs/{self.job.id}/change_status/',
            {'status': 'in_progress', 'provider_id': self.provider_user.id}
        )
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'in_progress')
        self.assertEqual(self.job.assigned_provider, self.provider_user)

    def test_bid_lifecycle(self):
        self.authenticate(self.provider_user)
        response = self.api_client.post('/api/bids/', {
            'job': self.job.id,
            'amount': 100,
            'timeline': '1_week',
            'proposal_message': 'I can fix this quickly with quality work and provide a detailed repair guarantee.'
        })
        self.assertEqual(response.status_code, 201)
        bid_id = response.json()['id']

        self.authenticate(self.client_user)
        accept = self.api_client.post(f'/api/bids/{bid_id}/accept/')
        self.assertEqual(accept.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.assigned_provider, self.provider_user)
        self.assertEqual(self.job.status, 'in_progress')

    def test_notifications_mark_read(self):
        Notification.objects.create(
            recipient=self.provider_user,
            actor=self.client_user,
            notification_type='message',
            title='Test',
            description='Test notification'
        )
        self.authenticate(self.provider_user)
        response = self.api_client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)
        mark = self.api_client.post('/api/notifications/mark_all_read/')
        self.assertEqual(mark.status_code, 200)
        self.assertTrue(Notification.objects.filter(recipient=self.provider_user, is_read=True).exists())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='no-reply@example.com',
        SEND_MESSAGE_EMAILS=True,
    )
    def test_message_creates_notification_email_and_unread_count(self):
        self.client_user.email = 'client@example.com'
        self.client_user.save(update_fields=['email'])
        self.provider_user.email = 'provider@example.com'
        self.provider_user.save(update_fields=['email'])

        self.authenticate(self.client_user)
        response = self.api_client.post('/api/messages/', {
            'recipient': self.provider_user.id,
            'service': self.service.id,
            'content': 'Can you help with a plumbing issue tomorrow?'
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Message.objects.filter(recipient=self.provider_user, service=self.service).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.provider_user, notification_type='message').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New message from', mail.outbox[0].subject)
        self.assertIn('plumbing issue tomorrow', mail.outbox[0].body)
        self.assertTrue(mail.outbox[0].alternatives)
        self.assertIn('text/html', mail.outbox[0].alternatives[0])
        self.assertIn('Vashandi', mail.outbox[0].alternatives[0][0])

        self.authenticate(self.provider_user)
        unread_response = self.api_client.get('/api/messages/unread_count/')
        self.assertEqual(unread_response.status_code, 200)
        self.assertEqual(unread_response.json()['unread'], 1)

        list_response = self.api_client.get(f'/api/messages/?conversation_with={self.client_user.id}&service={self.service.id}')
        self.assertEqual(list_response.status_code, 200)
        unread_response = self.api_client.get('/api/messages/unread_count/')
        self.assertEqual(unread_response.json()['unread'], 0)

    def test_completed_job_can_be_reviewed_with_comment(self):
        self.job.service = self.service
        self.job.assigned_provider = self.provider_user
        self.job.status = 'completed'
        self.job.save(update_fields=['service', 'assigned_provider', 'status'])

        self.authenticate(self.client_user)
        response = self.api_client.post('/api/reviews/', {
            'service': self.service.id,
            'job': self.job.id,
            'rating': 5,
            'comment': 'Great work, quick turnaround, and clear communication.'
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Review.objects.filter(service=self.service, reviewer=self.client_user, job=self.job).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.provider_user, notification_type='review').exists())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='no-reply@example.com',
    )
    def test_rfq_invoice_and_analytics_flow(self):
        self.client_user.email = 'client@example.com'
        self.client_user.save(update_fields=['email'])
        self.provider_user.email = 'provider@example.com'
        self.provider_user.save(update_fields=['email'])

        self.authenticate(self.client_user)
        rfq_response = self.api_client.post('/api/rfqs/', {
            'service': self.service.id,
            'title': 'Bathroom plumbing RFQ',
            'requirements': 'Need a full quote for bathroom pipe replacement.',
            'quantity': 2,
            'target_budget': '250.00',
        }, format='json')
        self.assertEqual(rfq_response.status_code, 201)
        rfq_id = rfq_response.json()['id']
        self.assertTrue(RFQ.objects.filter(id=rfq_id, provider=self.provider_user, client=self.client_user).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New RFQ', mail.outbox[0].subject)

        self.authenticate(self.provider_user)
        invoice_response = self.api_client.post('/api/invoices/', {
            'rfq': rfq_id,
            'title': 'Quote for bathroom plumbing',
            'scope_of_work': 'Remove damaged pipes and install replacement fittings.',
            'line_items': 'Pipe removal\nReplacement pipes\nTesting and cleanup',
            'subtotal': '300.00',
            'tax_amount': '45.00',
            'notes': 'Includes labor and testing.',
        }, format='json')
        self.assertEqual(invoice_response.status_code, 201)
        invoice = Invoice.objects.get(id=invoice_response.json()['id'])
        self.assertEqual(str(invoice.total_amount), '345.00')
        rfq = RFQ.objects.get(id=rfq_id)
        self.assertEqual(rfq.status, 'quoted')
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('New invoice', mail.outbox[1].subject)

        analytics_response = self.api_client.get('/api/analytics/')
        self.assertEqual(analytics_response.status_code, 200)
        analytics = analytics_response.json()
        self.assertEqual(analytics['rfqs_total'], 1)
        self.assertEqual(analytics['invoices_total'], 1)
        self.assertGreaterEqual(float(analytics['pricing']['average']), 345.0)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='no-reply@example.com',
    )
    def test_notification_sample_suite_sends_all_types(self):
        from workers.email_utils import send_notification_samples

        results = send_notification_samples('sample@example.com')
        self.assertEqual(len(results), 7)
        self.assertEqual(len(mail.outbox), 7)
        self.assertTrue(all(success for _, (success, _) in results))
        self.assertTrue(all(message.alternatives for message in mail.outbox))
