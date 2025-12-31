"""
Test suite for messaging functionality
Tests message creation, retrieval, and validation functionality
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from workers.models import Message
from workers.message import MessageManager, MessageValidator

User = get_user_model()


class MessageManagerTestCase(TestCase):
    """Test cases for MessageManager utility class"""

    def setUp(self):
        """Set up test users and data"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='user1@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User1'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='user2@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User2'
        )

    def test_create_message(self):
        """Test creating a message"""
        message = MessageManager.create_message(
            sender=self.user1,
            recipient=self.user2,
            content='Hello, this is a test message'
        )

        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.recipient, self.user2)
        self.assertEqual(message.content, 'Hello, this is a test message')
        self.assertFalse(message.is_read)

    def test_create_message_empty_content(self):
        """Test creating a message with empty content"""
        with self.assertRaises(ValueError) as context:
            MessageManager.create_message(
                sender=self.user1,
                recipient=self.user2,
                content=''
            )
        self.assertIn('empty', str(context.exception).lower())

    def test_create_message_to_self(self):
        """Test creating a message to yourself"""
        with self.assertRaises(ValueError) as context:
            MessageManager.create_message(
                sender=self.user1,
                recipient=self.user1,
                content='Self message'
            )
        self.assertIn('yourself', str(context.exception).lower())

    def test_create_message_content_too_long(self):
        """Test creating a message with content exceeding limit"""
        long_content = 'x' * 5001
        with self.assertRaises(ValueError) as context:
            MessageManager.create_message(
                sender=self.user1,
                recipient=self.user2,
                content=long_content
            )
        self.assertIn('exceed', str(context.exception).lower())

    def test_mark_as_read(self):
        """Test marking a message as read"""
        message = MessageManager.create_message(
            sender=self.user1,
            recipient=self.user2,
            content='Test message'
        )
        self.assertFalse(message.is_read)

        marked_message = MessageManager.mark_as_read(message)
        self.assertTrue(marked_message.is_read)

    def test_get_unread_count(self):
        """Test getting unread message count"""
        # Create messages where user2 is recipient
        MessageManager.create_message(
            sender=self.user1,
            recipient=self.user2,
            content='Unread 1'
        )
        MessageManager.create_message(
            sender=self.user1,
            recipient=self.user2,
            content='Unread 2'
        )

        # Create one read message
        msg = MessageManager.create_message(
            sender=self.user1,
            recipient=self.user2,
            content='Read message'
        )
        MessageManager.mark_as_read(msg)

        unread_count = MessageManager.get_unread_count(self.user2)
        self.assertEqual(unread_count, 2)

    def test_get_conversation(self):
        """Test retrieving a conversation between two users"""
        # Create multiple messages
        msg1 = MessageManager.create_message(
            sender=self.user1,
            recipient=self.user2,
            content='Message 1'
        )
        msg2 = MessageManager.create_message(
            sender=self.user2,
            recipient=self.user1,
            content='Message 2'
        )

        conversation = MessageManager.get_conversation(self.user1, self.user2)
        self.assertEqual(conversation.count(), 2)
        self.assertIn(msg1, conversation)
        self.assertIn(msg2, conversation)


class MessageValidatorTestCase(TestCase):
    """Test cases for MessageValidator utility class"""

    def setUp(self):
        """Set up test users"""
        self.user1 = User.objects.create_user(
            username='validator1',
            email='validator1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='validator2',
            email='validator2@test.com',
            password='testpass123'
        )

    def test_validate_empty_content(self):
        """Test validation of empty content"""
        is_valid, error = MessageValidator.validate_message_content('')
        self.assertFalse(is_valid)
        self.assertIn('required', error.lower())

    def test_validate_whitespace_only_content(self):
        """Test validation of whitespace-only content"""
        is_valid, error = MessageValidator.validate_message_content('   ')
        self.assertFalse(is_valid)
        self.assertIn('empty', error.lower())

    def test_validate_content_too_long(self):
        """Test validation of content exceeding limit"""
        long_content = 'x' * 5001
        is_valid, error = MessageValidator.validate_message_content(long_content)
        self.assertFalse(is_valid)
        self.assertIn('exceed', error.lower())

    def test_validate_valid_content(self):
        """Test validation of valid content"""
        is_valid, error = MessageValidator.validate_message_content('Valid message content')
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_same_user(self):
        """Test validation of sending message to yourself"""
        is_valid, error = MessageValidator.validate_users(self.user1, self.user1)
        self.assertFalse(is_valid)
        self.assertIn('yourself', error.lower())

    def test_validate_different_users(self):
        """Test validation of different users"""
        is_valid, error = MessageValidator.validate_users(self.user1, self.user2)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
