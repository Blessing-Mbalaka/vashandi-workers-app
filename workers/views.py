from datetime import timedelta

from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .message import MessageManager
from .models import Bid, Job, Message, Notification, Review, Service
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ServiceSerializer,
    ServiceListSerializer, JobSerializer, ReviewSerializer, MessageSerializer,
    BidSerializer, NotificationSerializer
)

User = get_user_model()


def create_notification(*, recipient, actor, notification_type, title, description, related_object=None):
    """Utility to create notifications safely"""
    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        description=description,
        related_object_id=getattr(related_object, 'id', None),
        related_model=related_object.__class__.__name__ if related_object else ''
    )


# Template Views
def login_view(request):
    """Login/Register page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'workers/login.html')


@login_required
def dashboard_view(request):
    """Main dashboard view"""
    return render(request, 'workers/dashboard.html')


def logout_view(request):
    """Logout user"""
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    """User profile page"""
    return render(request, 'workers/profile.html')


# API Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        login(request, user)
        return Response({
            'message': 'Registration successful',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """User login endpoint"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'error': 'Please provide both username and password'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def current_user_api(request):
    """Get or update current user info"""
    if request.method == 'GET':
        return Response(UserSerializer(request.user).data)

    editable_fields = {'first_name', 'last_name', 'phone', 'location', 'bio'}
    data = {key: value for key, value in request.data.items() if key in editable_fields}
    if not data:
        return Response({'error': 'No editable fields provided.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = UserSerializer(request.user, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_role_api(request):
    """Toggle user role between client and provider"""
    role = request.data.get('role')
    if role not in ['client', 'provider']:
        return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
    
    request.user.current_role = role
    request.user.save()
    return Response({
        'message': 'Role updated successfully',
        'user': UserSerializer(request.user).data
    })


class ServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Service CRUD operations"""
    queryset = Service.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceListSerializer
        return ServiceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        location = self.request.query_params.get('location')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(provider__first_name__icontains=search) |
                Q(provider__last_name__icontains=search)
            )

        if location:
            queryset = queryset.filter(provider__location__icontains=location)

        if min_price:
            queryset = queryset.filter(price_per_hour__gte=min_price)

        if max_price:
            queryset = queryset.filter(price_per_hour__lte=max_price)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_services(self, request):
        """Get current user's services"""
        services = self.queryset.filter(provider=request.user)
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def contact(self, request, pk=None):
        """Contact service provider"""
        service = self.get_object()
        content = request.data.get('message')
        
        if not content:
            return Response({'error': 'Message content required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        message = Message.objects.create(
            sender=request.user,
            recipient=service.provider,
            service=service,
            content=content
        )

        create_notification(
            recipient=service.provider,
            actor=request.user,
            notification_type=Notification.MESSAGE,
            title='New service inquiry',
            description=f'{request.user.get_full_name()} sent you a message about {service.title}.',
            related_object=message
        )
        
        return Response({
            'message': 'Message sent successfully',
            'data': MessageSerializer(message).data
        })


class JobViewSet(viewsets.ModelViewSet):
    """ViewSet for Job CRUD operations"""
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        category = params.get('category')
        status_filter = params.get('status')
        min_budget = params.get('min_budget')
        max_budget = params.get('max_budget')
        location = params.get('location')
        date_posted = params.get('date_posted')
        deadline_filter = params.get('deadline')
        sort = params.get('sort')
        
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        if min_budget:
            queryset = queryset.filter(budget__gte=min_budget)

        if max_budget:
            queryset = queryset.filter(budget__lte=max_budget)

        if location:
            queryset = queryset.filter(location__icontains=location)

        if date_posted in {'7', '30'}:
            days = int(date_posted)
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=days))

        if deadline_filter:
            if deadline_filter == 'urgent':
                queryset = queryset.filter(deadline__lte=timezone.now().date() + timedelta(days=3))
            elif deadline_filter == 'week':
                queryset = queryset.filter(deadline__lte=timezone.now().date() + timedelta(days=7))
            elif deadline_filter == 'month':
                queryset = queryset.filter(deadline__lte=timezone.now().date() + timedelta(days=30))

        sort_map = {
            'newest': '-created_at',
            'budget_high': '-budget',
            'deadline': 'deadline',
        }
        if sort in sort_map:
            queryset = queryset.order_by(sort_map[sort])
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

    def update(self, request, *args, **kwargs):
        job = self.get_object()
        if job.client != request.user:
            raise PermissionDenied('Only the job owner can update this job.')
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        job = self.get_object()
        if job.client != request.user:
            raise PermissionDenied('Only the job owner can update this job.')
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def my_jobs(self, request):
        """Get current user's posted jobs"""
        jobs = self.queryset.filter(client=request.user)
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assigned_jobs(self, request):
        """Get jobs assigned to current user (as provider)"""
        jobs = self.queryset.filter(assigned_provider=request.user)
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Update job status with validation and notification support"""
        job = self.get_object()
        if job.client != request.user:
            return Response(
                {'error': 'Only the job owner can update the status.'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('status')
        valid_transitions = {
            'open': {'in_progress', 'cancelled'},
            'in_progress': {'completed', 'cancelled'},
            'completed': set(),
            'cancelled': set(),
        }

        valid_statuses = {choice[0] for choice in Job.STATUS_CHOICES}
        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status provided.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in valid_transitions[job.status]:
            return Response({'error': 'Invalid status transition.'}, status=status.HTTP_400_BAD_REQUEST)

        note = request.data.get('note', '').strip()
        provider_id = request.data.get('provider_id')
        if new_status == 'in_progress' and not (job.assigned_provider or provider_id):
            return Response({'error': 'Please assign a provider before starting the job.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            job.status = new_status
            if provider_id:
                try:
                    provider = User.objects.get(id=provider_id)
                except User.DoesNotExist:
                    return Response({'error': 'Provider not found.'}, status=status.HTTP_404_NOT_FOUND)
                job.assigned_provider = provider
            job.save()

            if job.assigned_provider:
                description = f'{job.client.get_full_name()} updated {job.title} to {job.get_status_display()}.'
                if note:
                    description += f' Note: {note}'
                create_notification(
                    recipient=job.assigned_provider,
                    actor=request.user,
                    notification_type=Notification.STATUS,
                    title=f'Job status updated to {job.get_status_display()}',
                    description=description,
                    related_object=job
                )

        serializer = self.get_serializer(job)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Review CRUD operations"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        service_id = self.request.query_params.get('service')
        
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        return queryset
    
    def perform_create(self, serializer):
        service = serializer.validated_data['service']
        if service.provider == self.request.user:
            raise PermissionDenied('You cannot review your own service.')

        job = serializer.validated_data.get('job')
        if job:
            if job.status != 'completed':
                raise PermissionDenied('You can only review completed jobs.')
            if self.request.user not in {job.client, job.assigned_provider}:
                raise PermissionDenied('You must be part of the job to leave a review.')

        review = serializer.save(reviewer=self.request.user)
        create_notification(
            recipient=service.provider,
            actor=self.request.user,
            notification_type=Notification.REVIEW,
            title='New review received',
            description=f'{self.request.user.get_full_name()} left a {review.rating}-star review.',
            related_object=review
        )


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for Message CRUD operations"""
    queryset = Message.objects.select_related('sender', 'recipient', 'service', 'job')
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = self.queryset.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        )
        conversation_with = self.request.query_params.get('conversation_with')
        service_id = self.request.query_params.get('service')
        job_id = self.request.query_params.get('job')

        if conversation_with:
            queryset = queryset.filter(
                Q(sender=self.request.user, recipient_id=conversation_with) |
                Q(sender_id=conversation_with, recipient=self.request.user)
            )

        if service_id:
            queryset = queryset.filter(service_id=service_id)

        if job_id:
            queryset = queryset.filter(job_id=job_id)

        return queryset.order_by('created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        conversation_with = request.query_params.get('conversation_with')
        if conversation_with:
            queryset.filter(recipient=request.user, sender_id=conversation_with).update(is_read=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new message with detailed error handling"""
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return Response(
                {'error': 'You must be logged in to send messages. Please log in first.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate required fields
        recipient_id = request.data.get('recipient')
        content = request.data.get('content', '').strip()
        service_id = request.data.get('service')
        job_id = request.data.get('job')
        
        if not recipient_id:
            return Response(
                {'error': 'Recipient is required. Please select a user to message.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not content:
            return Response(
                {'error': 'Message cannot be empty. Please type a message.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(content) > 5000:
            return Response(
                {'error': 'Message is too long. Maximum 5000 characters allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if recipient exists
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'The recipient user does not exist. Please refresh and try again.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if trying to message self
        if recipient_id == request.user.id:
            return Response(
                {'error': 'You cannot send a message to yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate service or job reference
        if not service_id and not job_id:
            return Response(
                {'error': 'You must specify either a service or job for this message.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = None
        job = None
        
        if service_id:
            try:
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                return Response(
                    {'error': 'The service no longer exists. Please refresh and try again.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        if job_id:
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(
                    {'error': 'The job no longer exists. Please refresh and try again.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create the message
        try:
            message = Message.objects.create(
                sender=request.user,
                recipient=recipient,
                service=service,
                job=job,
                content=content
            )
            create_notification(
                recipient=recipient,
                actor=request.user,
                notification_type=Notification.MESSAGE,
                title='New message received',
                description=f'{request.user.get_full_name()} sent you a new message.',
                related_object=message
            )
            serializer = self.get_serializer(message)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to send message: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
    
    @action(detail=False, methods=['get'])
    def inbox(self, request):
        """Get user's inbox"""
        messages = self.queryset.filter(recipient=request.user)
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """Get user's sent messages"""
        messages = self.queryset.filter(sender=request.user)
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        if message.recipient != request.user:
            return Response({
                'error': 'You do not have permission to mark this message as read. You can only mark messages sent to you.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        message.is_read = True
        message.save()
        return Response({'message': 'Marked as read', 'success': True})
    
    @action(detail=False, methods=['get'])
    def conversations(self, request):
        """Return list of conversations with latest message preview"""
        conversations = []
        for convo in MessageManager.get_conversations_for_user(request.user):
            latest = convo['latest_message']
            conversations.append({
                'user_id': convo['other_user'].id,
                'user_name': convo['other_user'].get_full_name(),
                'user_initials': convo['other_user'].avatar_initials,
                'latest_message': latest.content,
                'timestamp': latest.created_at.isoformat(),
                'is_unread': convo['unread'],
                'service_id': latest.service_id,
                'service_title': latest.service.title if latest.service else None,
                'job_id': latest.job_id,
                'job_title': latest.job.title if latest.job else None,
            })
        return Response(conversations)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Number of unread messages"""
        count = Message.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all messages as read for user"""
        Message.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'success': True})


class BidViewSet(viewsets.ModelViewSet):
    """ViewSet for bid operations"""
    queryset = Bid.objects.select_related('provider', 'job', 'job__client')
    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        job_id = self.request.query_params.get('job')
        provider_id = self.request.query_params.get('provider')

        if job_id:
            queryset = queryset.filter(job_id=job_id)

        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)

        user = self.request.user
        return queryset.filter(Q(provider=user) | Q(job__client=user))

    def perform_create(self, serializer):
        user = self.request.user
        if user.current_role not in {'provider', 'both'}:
            raise PermissionDenied('Only providers can place bids.')

        job = serializer.validated_data['job']
        if job.client == user:
            raise PermissionDenied('You cannot bid on your own job.')

        if job.status != 'open':
            raise PermissionDenied('You can only bid on open jobs.')

        if Bid.objects.filter(provider=user, job=job).exists():
            raise PermissionDenied('You already placed a bid on this job.')

        bid = serializer.save(provider=user)
        create_notification(
            recipient=job.client,
            actor=user,
            notification_type=Notification.BID,
            title=f'New bid on {job.title}',
            description=f'{user.get_full_name()} placed a bid for ${bid.amount}.',
            related_object=bid
        )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        bid = self.get_object()
        if bid.job.client != request.user:
            return Response({'error': 'Only the job owner can accept bids.'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            bid.is_accepted = True
            bid.withdrawn = False
            bid.save()
            bid.job.status = 'in_progress'
            bid.job.assigned_provider = bid.provider
            bid.job.save()
            Bid.objects.filter(job=bid.job).exclude(pk=bid.pk).update(is_accepted=False)

        create_notification(
            recipient=bid.provider,
            actor=request.user,
            notification_type=Notification.BID,
            title='Bid accepted',
            description=f'Your bid for {bid.job.title} was accepted.',
            related_object=bid.job
        )
        serializer = self.get_serializer(bid)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for user notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied('Notifications are generated automatically.')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'success': True})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread': count})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        bid = self.get_object()
        if bid.job.client != request.user:
            return Response({'error': 'Only the job owner can reject bids.'}, status=status.HTTP_403_FORBIDDEN)

        bid.is_accepted = False
        bid.save(update_fields=['is_accepted'])
        create_notification(
            recipient=bid.provider,
            actor=request.user,
            notification_type=Notification.BID,
            title='Bid rejected',
            description=f'Your bid for {bid.job.title} was rejected.',
            related_object=bid.job
        )
        serializer = self.get_serializer(bid)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        bid = self.get_object()
        if bid.provider != request.user:
            return Response({'error': 'Only the provider can withdraw their bid.'}, status=status.HTTP_403_FORBIDDEN)
        if bid.is_accepted:
            return Response({'error': 'Accepted bids cannot be withdrawn.'}, status=status.HTTP_400_BAD_REQUEST)

        bid.withdrawn = True
        bid.save(update_fields=['withdrawn'])
        create_notification(
            recipient=bid.job.client,
            actor=request.user,
            notification_type=Notification.BID,
            title='Bid withdrawn',
            description=f'{request.user.get_full_name()} withdrew their bid on {bid.job.title}.',
            related_object=bid.job
        )
        serializer = self.get_serializer(bid)
        return Response(serializer.data)


@api_view(['GET'])
def dashboard_stats_api(request):
    """Get dashboard statistics"""
    unread_messages = 0
    unread_notifications = 0
    if request.user.is_authenticated:
        unread_messages = Message.objects.filter(recipient=request.user, is_read=False).count()
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()

    if request.user.is_authenticated:
        if request.user.current_role == 'provider':
            stats = {
                'active_jobs': Job.objects.filter(
                    assigned_provider=request.user, 
                    status='in_progress'
                ).count(),
                'jobs_completed': Job.objects.filter(
                    assigned_provider=request.user, 
                    status='completed'
                ).count(),
                'average_rating': Review.objects.filter(
                    service__provider=request.user
                ).aggregate(avg=Avg('rating'))['avg'] or 0,
                'total_reviews': Review.objects.filter(
                    service__provider=request.user
                ).count(),
                'pending_bids': Bid.objects.filter(provider=request.user, withdrawn=False, is_accepted=False).count(),
                'unread_messages': unread_messages,
                'unread_notifications': unread_notifications,
            }
        else:
            stats = {
                'active_workers': Service.objects.filter(is_active=True).count(),
                'jobs_posted': Job.objects.filter(client=request.user).count(),
                'satisfaction_rate': 98,  # Can be calculated based on reviews
                'support_available': '24/7',
                'bids_received': Bid.objects.filter(job__client=request.user).count(),
                'unread_messages': unread_messages,
                'unread_notifications': unread_notifications,
            }
    else:
        stats = {
            'active_workers': Service.objects.filter(is_active=True).count(),
            'jobs_posted': Job.objects.count(),
            'satisfaction_rate': 98,
            'support_available': '24/7',
            'unread_messages': 0,
            'unread_notifications': 0,
        }
    
    return Response(stats)

