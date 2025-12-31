from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone

from workers.models import User, Service, Job, Message, Bid, Notification


class PhaseFeatureTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client', password='pass123', first_name='Client', last_name='User', current_role='client'
        )
        self.provider_user = User.objects.create_user(
            username='provider', password='pass123', first_name='Provider', last_name='User', current_role='provider'
        )
        self.service = Service.objects.create(
            provider=self.provider_user,
            category='plumbing',
            title='Pipe Fix',
            description='Fix leaky pipes',
            price_per_hour=50,
            experience_years=5
        )
        self.job = Job.objects.create(
            client=self.client_user,
            title='Kitchen leak',
            category='plumbing',
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
