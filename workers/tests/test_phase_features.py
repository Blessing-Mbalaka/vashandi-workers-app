from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.test.utils import override_settings
from rest_framework.test import APIClient
from django.utils import timezone

from workers.models import User, Service, Job, Message, Bid, Notification, Review, RFQ, Invoice, TradeCategory


class PhaseFeatureTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client', password='pass123', first_name='Client', last_name='User', current_role='client'
        )
        self.provider_user = User.objects.create_user(
            username='provider', password='pass123', first_name='Provider', last_name='User', current_role='provider'
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
