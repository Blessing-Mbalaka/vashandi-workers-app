"""
Message utility module for handling messaging operations
Provides helper functions and validators for messaging functionality
"""

from datetime import datetime
from django.utils.timesince import timesince
from workers.models import Message, User


class MessageManager:
    """Manager class for message operations"""

    @staticmethod
    def get_conversation(user1, user2, service=None, job=None):
        """
        Get all messages between two users
        
        Args:
            user1: First user
            user2: Second user
            service: Optional service to filter by
            job: Optional job to filter by
        
        Returns:
            QuerySet of messages
        """
        messages = Message.objects.filter(
            sender__in=[user1, user2],
            recipient__in=[user1, user2]
        ).order_by('created_at')

        if service:
            messages = messages.filter(service=service)
        if job:
            messages = messages.filter(job=job)

        return messages

    @staticmethod
    def create_message(sender, recipient, service=None, job=None, content=''):
        """
        Create a new message
        
        Args:
            sender: User sending the message
            recipient: User receiving the message
            service: Optional service reference
            job: Optional job reference
            content: Message content
        
        Returns:
            Created Message instance
        """
        if not content or not content.strip():
            raise ValueError('Message content cannot be empty')

        if len(content) > 5000:
            raise ValueError('Message cannot exceed 5000 characters')

        if sender == recipient:
            raise ValueError('Cannot send message to yourself')

        return Message.objects.create(
            sender=sender,
            recipient=recipient,
            service=service,
            job=job,
            content=content.strip()
        )

    @staticmethod
    def mark_as_read(message):
        """
        Mark a message as read
        
        Args:
            message: Message instance
        
        Returns:
            Updated message
        """
        message.is_read = True
        message.save()
        return message

    @staticmethod
    def get_unread_count(user):
        """
        Get count of unread messages for a user
        
        Args:
            user: User instance
        
        Returns:
            Integer count of unread messages
        """
        return Message.objects.filter(recipient=user, is_read=False).count()

    @staticmethod
    def get_conversations_for_user(user):
        """
        Get all unique conversations for a user (with the latest message)
        
        Args:
            user: User instance
        
        Returns:
            List of conversation dictionaries
        """
        # Get all messages involving this user
        sender_ids = set(Message.objects.filter(
            sender=user
        ).values_list('recipient_id', flat=True))
        recipient_ids = set(Message.objects.filter(
            recipient=user
        ).values_list('sender_id', flat=True))
        user_ids = (sender_ids | recipient_ids) - {None}

        conversations = []
        for user_id in user_ids:
            other_user = User.objects.filter(id=user_id).first()
            if not other_user:
                continue

            latest_message = Message.objects.filter(
                sender__in=[user, other_user],
                recipient__in=[user, other_user]
            ).select_related('sender', 'recipient').order_by('-created_at').first()

            if latest_message:
                conversations.append({
                    'other_user': other_user,
                    'latest_message': latest_message,
                    'unread': Message.objects.filter(
                        sender=other_user,
                        recipient=user,
                        is_read=False
                    ).exists()
                })

        return sorted(conversations, key=lambda x: x['latest_message'].created_at, reverse=True)

    @staticmethod
    def format_message(message, current_user=None):
        """
        Format a message for API response
        
        Args:
            message: Message instance
        
        Returns:
            Formatted message dictionary
        """
        return {
            'id': message.id,
            'sender_name': message.sender.display_name,
            'sender_id': message.sender.id,
            'recipient_name': message.recipient.display_name,
            'recipient_id': message.recipient.id,
            'service_title': message.service.title if message.service else None,
            'job_title': message.job.title if message.job else None,
            'content': message.content,
            'is_read': message.is_read,
            'created_at': message.created_at.isoformat(),
            'time_ago': timesince(message.created_at) + ' ago',
            'is_sent_by_user': current_user.id == message.sender_id if current_user else False
        }


class MessageValidator:
    """Validator class for message operations"""

    @staticmethod
    def validate_message_content(content):
        """
        Validate message content
        
        Args:
            content: Message content to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content:
            return False, 'Message content is required'

        if not isinstance(content, str):
            return False, 'Message content must be a string'

        if len(content.strip()) == 0:
            return False, 'Message cannot be empty or whitespace only'

        if len(content) > 5000:
            return False, 'Message cannot exceed 5000 characters'

        return True, None

    @staticmethod
    def validate_users(sender, recipient):
        """
        Validate sender and recipient
        
        Args:
            sender: Sender user instance
            recipient: Recipient user instance
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if sender == recipient:
            return False, 'Cannot send message to yourself'

        if not isinstance(sender, User):
            return False, 'Sender must be a valid user'

        if not isinstance(recipient, User):
            return False, 'Recipient must be a valid user'

        return True, None

    @staticmethod
    def validate_service_and_job(service, job):
        """
        Validate service and job references
        
        Args:
            service: Optional Service instance
            job: Optional Job instance
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # At least one of service or job should be provided
        if service is None and job is None:
            return False, 'Either a service or job reference is required'

        return True, None
