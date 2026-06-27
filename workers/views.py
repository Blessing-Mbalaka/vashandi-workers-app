from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .email_utils import (
    send_bid_email as send_bid_email_notification,
    send_invoice_email as send_invoice_email_notification,
    send_message_email as send_message_email_notification,
    send_review_email as send_review_email_notification,
    send_rfq_email as send_rfq_email_notification,
    send_status_change_email as send_status_change_email_notification,
    send_welcome_email as send_welcome_email_notification,
)
from .message import MessageManager
from .models import (
    Bid, Country, Invoice, Job, Message, Notification, RFQ, Review, Service,
    TradeCategory, ProjectTracker, ProjectPhase, ProjectTask, ProjectDispute,
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ServiceSerializer,
    ServiceListSerializer, JobSerializer, ReviewSerializer, MessageSerializer,
    BidSerializer, InvoiceSerializer, NotificationSerializer, RFQSerializer,
    TradeCategorySerializer, CountrySerializer, ProjectTrackerSerializer,
    ProjectPhaseSerializer, ProjectTaskSerializer, ProjectDisputeSerializer,
    AdminUserSerializer,
)

User = get_user_model()


def apply_category_filters(queryset, params):
    category_id = params.get('category_id')
    trade_id = params.get('trade_id')
    category_value = params.get('category')

    if category_id:
        return queryset.filter(category_ref_id=category_id)

    if trade_id:
        return queryset.filter(Q(category_ref_id=trade_id) | Q(category_ref__parent_id=trade_id))

    if category_value and category_value != 'all':
        category_obj = TradeCategory.objects.filter(Q(slug=category_value) | Q(name__iexact=category_value)).first()
        if category_obj:
            if category_obj.parent_id:
                return queryset.filter(Q(category_ref=category_obj) | Q(category=category_obj.slug))
            return queryset.filter(
                Q(category_ref=category_obj) |
                Q(category_ref__parent=category_obj) |
                Q(category=category_obj.slug)
            )
        return queryset.filter(category=category_value)

    return queryset


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


def send_welcome_email(user):
    return send_welcome_email_notification(user)


def send_message_email(message_obj):
    return send_message_email_notification(message_obj)


def send_rfq_email(rfq):
    return send_rfq_email_notification(rfq)


def send_invoice_email(invoice):
    return send_invoice_email_notification(invoice)


def notify_admins(*, actor, title, description, related_object=None):
    for admin_user in User.objects.filter(is_superuser=True):
        create_notification(
            recipient=admin_user,
            actor=actor,
            notification_type=Notification.DISPUTE,
            title=title,
            description=description,
            related_object=related_object,
        )


def restore_task_state_after_dispute(task):
    if task.client_completion_signature:
        task.status = 'completed'
    elif task.completed_at:
        task.status = 'submitted'
    elif task.client_plan_signature:
        task.status = 'approved_to_start'
    elif task.provider_execution_plan:
        task.status = 'planned'
    else:
        task.status = 'client_defined'
    task.save(update_fields=['status', 'updated_at'])


def restore_phase_state_after_dispute(phase):
    if phase.payment_acknowledged_at:
        phase.execution_status = 'approved'
        phase.fund_release_status = 'released'
    elif phase.payment_proof_uploaded_at:
        phase.execution_status = 'approved'
        phase.fund_release_status = 'payment_submitted'
    elif phase.client_approved_at and phase.provider_submitted_at:
        phase.execution_status = 'approved'
        phase.fund_release_status = 'pending_release'
    elif phase.provider_submitted_at:
        phase.execution_status = 'submitted'
        phase.fund_release_status = 'pending_release'
    elif phase.tasks.filter(status__in=['in_progress', 'submitted', 'completed']).exists():
        phase.execution_status = 'in_progress'
        phase.fund_release_status = 'locked'
    else:
        phase.execution_status = 'not_started'
        phase.fund_release_status = 'locked'
    phase.save(update_fields=['execution_status', 'fund_release_status', 'updated_at'])


def ensure_admin_user(user):
    if not user.is_authenticated or not user.is_superuser:
        raise DjangoPermissionDenied('Only superusers can access this area.')


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


@login_required
def admin_portal_view(request):
    """Admin portal for superusers to manage accounts and platform oversight."""
    ensure_admin_user(request.user)
    return render(request, 'workers/admin_portal.html')


def logout_view(request):
    """Logout user"""
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    """User profile page"""
    return render(request, 'workers/profile.html')


def public_profile_view(request, user_id):
    """Public-facing profile for an individual provider or company."""
    profile_user = get_object_or_404(
        User.objects.select_related('country'),
        id=user_id
    )
    services = Service.objects.filter(provider=profile_user, is_active=True).select_related('category_ref', 'category_ref__parent')
    return render(request, 'workers/public_profile.html', {
        'profile_user': profile_user,
        'services': services,
    })


def snag_view(request):
    """Generic frontend-safe error page."""
    return render(request, 'workers/snag.html', {
        'reference': request.GET.get('ref', ''),
    }, status=500)


# API Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        email_sent, email_error = send_welcome_email(user)
        return Response({
            'message': 'Registration successful. Your account is pending admin approval before you can log in.',
            'user': UserSerializer(user).data,
            'email_sent': email_sent,
            'email_error': email_error,
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
        if not user.is_active:
            return Response({'error': 'Your account is disabled. Please contact support.'}, status=status.HTTP_403_FORBIDDEN)
        if not user.can_access_platform:
            if user.verification_status == 'rejected':
                note = f" Reason: {user.verification_notes}" if user.verification_notes else ''
                return Response(
                    {'error': f'Your verification was not approved.{note} Please contact an administrator to review your account or register again with updated documents.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return Response(
                {'error': 'Your account is pending admin verification. You can log in once your verification documents are approved.'},
                status=status.HTTP_403_FORBIDDEN
            )
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
        return Response(UserSerializer(request.user, context={'request': request}).data)

    editable_fields = {
        'first_name', 'last_name', 'phone', 'location', 'bio', 'account_type',
        'company_name', 'company_website', 'vat_number', 'country', 'verification_document'
    }
    data = {key: value for key, value in request.data.items() if key in editable_fields}
    if not data:
        return Response({'error': 'No editable fields provided.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = UserSerializer(request.user, data=data, partial=True, context={'request': request})
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    if 'verification_document' in data:
        user.verification_status = 'pending'
        user.verification_notes = ''
        user.verified_at = None
        user.reviewed_by = None
        user.save(update_fields=['verification_status', 'verification_notes', 'verified_at', 'reviewed_by'])
    return Response(UserSerializer(user, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_overview_api(request):
    ensure_admin_user(request.user)

    verification_counts = User.objects.aggregate(
        pending=Count('id', filter=Q(verification_status='pending')),
        approved=Count('id', filter=Q(verification_status='approved')),
        rejected=Count('id', filter=Q(verification_status='rejected')),
    )
    account_mix = User.objects.aggregate(
        clients=Count('id', filter=Q(current_role='client')),
        providers=Count('id', filter=Q(current_role='provider')),
        hybrid=Count('id', filter=Q(current_role='both')),
        companies=Count('id', filter=Q(account_type='company')),
        individuals=Count('id', filter=Q(account_type='individual')),
        active_accounts=Count('id', filter=Q(is_active=True)),
    )
    open_disputes = ProjectDispute.objects.filter(status='open').count()
    shared_pricing = Invoice.objects.aggregate(
        average=Avg('total_amount'),
        minimum=Min('total_amount'),
        maximum=Max('total_amount'),
    )
    pending_users = User.objects.filter(verification_status='pending').order_by('date_joined')[:6]
    recent_disputes = ProjectDispute.objects.select_related('tracker', 'raised_by').order_by('-created_at')[:6]

    return Response({
        'verification': verification_counts,
        'accounts': account_mix,
        'platform': {
            'services': Service.objects.count(),
            'jobs_open': Job.objects.filter(status='open').count(),
            'jobs_in_progress': Job.objects.filter(status='in_progress').count(),
            'rfqs_total': RFQ.objects.count(),
            'invoices_total': Invoice.objects.count(),
            'open_disputes': open_disputes,
        },
        'shared_pricing': {
            'average': shared_pricing['average'] or 0,
            'minimum': shared_pricing['minimum'] or 0,
            'maximum': shared_pricing['maximum'] or 0,
        },
        'pending_users': AdminUserSerializer(pending_users, many=True, context={'request': request}).data,
        'recent_disputes': ProjectDisputeSerializer(recent_disputes, many=True, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_api(request):
    ensure_admin_user(request.user)

    queryset = User.objects.select_related('country').order_by('-date_joined')
    verification_filter = request.query_params.get('verification_status')
    role_filter = request.query_params.get('role')
    account_type_filter = request.query_params.get('account_type')
    q = request.query_params.get('q')

    if verification_filter:
        queryset = queryset.filter(verification_status=verification_filter)
    if role_filter:
        queryset = queryset.filter(current_role=role_filter)
    if account_type_filter:
        queryset = queryset.filter(account_type=account_type_filter)
    if q:
        queryset = queryset.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(company_name__icontains=q)
        )

    return Response(AdminUserSerializer(queryset[:150], many=True, context={'request': request}).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_user_detail_api(request, user_id):
    ensure_admin_user(request.user)
    target_user = get_object_or_404(User, id=user_id)
    serializer = AdminUserSerializer(target_user, data=request.data, partial=True, context={'request': request})
    serializer.is_valid(raise_exception=True)
    updated_user = serializer.save()

    if updated_user.verification_status == 'approved' and not updated_user.verified_at:
        updated_user.verified_at = timezone.now()
        updated_user.reviewed_by = request.user
        updated_user.save(update_fields=['verified_at', 'reviewed_by'])
    elif updated_user.verification_status == 'rejected':
        updated_user.verified_at = None
        updated_user.reviewed_by = request.user
        updated_user.save(update_fields=['verified_at', 'reviewed_by'])

    return Response(AdminUserSerializer(updated_user, context={'request': request}).data)


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
    queryset = Service.objects.select_related('provider', 'category_ref', 'category_ref__parent').filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceListSerializer
        return ServiceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search')
        location = self.request.query_params.get('location')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        queryset = apply_category_filters(queryset, self.request.query_params)
        
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
        services = self.get_queryset().filter(provider=request.user)
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
            description=f'{request.user.display_name} sent you a message about {service.title}.',
            related_object=message
        )
        send_message_email(message)
        
        return Response({
            'message': 'Message sent successfully',
            'data': MessageSerializer(message).data
        })


class JobViewSet(viewsets.ModelViewSet):
    """ViewSet for Job CRUD operations"""
    queryset = Job.objects.select_related('client', 'assigned_provider', 'service', 'category_ref', 'category_ref__parent').all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        status_filter = params.get('status')
        service_id = params.get('service')
        min_budget = params.get('min_budget')
        max_budget = params.get('max_budget')
        location = params.get('location')
        date_posted = params.get('date_posted')
        deadline_filter = params.get('deadline')
        sort = params.get('sort')
        
        queryset = apply_category_filters(queryset, params)
        
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        if service_id:
            queryset = queryset.filter(service_id=service_id)

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
        jobs = self.get_queryset().filter(client=request.user)
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assigned_jobs(self, request):
        """Get jobs assigned to current user (as provider)"""
        jobs = self.get_queryset().filter(assigned_provider=request.user)
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
                description = f'{job.client.display_name} updated {job.title} to {job.get_status_display()}.'
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
                send_status_change_email_notification(job, request.user, note)

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
            description=f'{self.request.user.display_name} left a {review.rating}-star review.',
            related_object=review
        )
        send_review_email_notification(review)


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
                description=f'{request.user.display_name} sent you a new message.',
                related_object=message
            )
            send_message_email(message)
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
                'user_name': convo['other_user'].display_name,
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
            description=f'{user.display_name} placed a bid for {user.currency_symbol}{bid.amount}.',
            related_object=bid
        )
        send_bid_email_notification(
            recipient=job.client,
            actor=user,
            subject=f'New bid on {job.title}',
            heading='New Bid Received',
            intro=f'{user.display_name} placed a new bid on your job.',
            job_title=job.title,
            amount=bid.amount,
            extra_label='Proposal Timeline',
            extra_value=bid.get_timeline_display(),
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
        send_bid_email_notification(
            recipient=bid.provider,
            actor=request.user,
            subject=f'Bid accepted for {bid.job.title}',
            heading='Bid Accepted',
            intro=f'{request.user.display_name} accepted your bid.',
            job_title=bid.job.title,
            amount=bid.amount,
            extra_label='Status',
            extra_value='Accepted',
        )
        serializer = self.get_serializer(bid)
        return Response(serializer.data)


class RFQViewSet(viewsets.ModelViewSet):
    """ViewSet for RFQ operations"""
    queryset = RFQ.objects.select_related('client', 'provider', 'service', 'service__provider')
    serializer_class = RFQSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            Q(client=self.request.user) | Q(provider=self.request.user)
        )
        direction = self.request.query_params.get('direction')
        status_filter = self.request.query_params.get('status')

        if direction == 'sent':
            queryset = queryset.filter(client=self.request.user)
        elif direction == 'received':
            queryset = queryset.filter(provider=self.request.user)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.current_role not in {'client', 'both'}:
            raise PermissionDenied('Only clients can submit RFQs.')

        service = serializer.validated_data['service']
        rfq = serializer.save(client=user, provider=service.provider)
        create_notification(
            recipient=service.provider,
            actor=user,
            notification_type=Notification.RFQ,
            title=f'New RFQ for {service.title}',
            description=f'{user.display_name} sent an RFQ: {rfq.title}.',
            related_object=rfq
        )
        send_rfq_email(rfq)

    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        rfq = self.get_object()
        if rfq.provider != request.user:
            return Response({'error': 'Only the provider can review this RFQ.'}, status=status.HTTP_403_FORBIDDEN)
        rfq.status = 'reviewed'
        rfq.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(rfq).data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for provider invoices"""
    queryset = Invoice.objects.select_related('provider', 'client', 'rfq', 'service')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            Q(provider=self.request.user) | Q(client=self.request.user)
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.current_role not in {'provider', 'both'}:
            raise PermissionDenied('Only providers can create invoices.')

        rfq = serializer.validated_data.get('rfq')
        if not rfq:
            raise PermissionDenied('Invoices must be linked to an RFQ.')
        if rfq.provider != user:
            raise PermissionDenied('You can only invoice RFQs assigned to you.')

        invoice = serializer.save(
            provider=user,
            client=rfq.client,
            service=rfq.service,
            status='sent'
        )
        rfq.status = 'quoted'
        rfq.save(update_fields=['status', 'updated_at'])
        create_notification(
            recipient=rfq.client,
            actor=user,
            notification_type=Notification.INVOICE,
            title=f'New invoice for {rfq.title}',
            description=f'{user.display_name} sent you an invoice for {user.currency_symbol}{invoice.total_amount}.',
            related_object=invoice
        )
        send_invoice_email(invoice)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        invoice = self.get_object()
        if invoice.client != request.user:
            return Response({'error': 'Only the client can accept this invoice.'}, status=status.HTTP_403_FORBIDDEN)
        invoice.status = 'accepted'
        invoice.save(update_fields=['status', 'updated_at'])
        if invoice.rfq:
            invoice.rfq.status = 'accepted'
            invoice.rfq.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        if invoice.client != request.user:
            return Response({'error': 'Only the client can mark this invoice as paid.'}, status=status.HTTP_403_FORBIDDEN)
        invoice.status = 'paid'
        invoice.save(update_fields=['status', 'updated_at'])
        if invoice.rfq:
            invoice.rfq.status = 'closed'
            invoice.rfq.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        invoice = self.get_object()
        if request.user not in {invoice.client, invoice.provider} and not request.user.is_staff:
            return Response({'error': 'You do not have permission to download this invoice.'}, status=status.HTTP_403_FORBIDDEN)

        line_items = invoice.line_items or 'No line items provided.'
        notes = invoice.notes or 'No additional notes.'
        currency_symbol = invoice.client.currency_symbol
        currency_code = invoice.client.currency_code
        safe_title = ''.join(char if char.isalnum() else '-' for char in invoice.title.lower()).strip('-') or f'invoice-{invoice.id}'
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{invoice.title}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; margin: 0; background: #f6f1e6; color: #15120d; }}
    .page {{ max-width: 920px; margin: 32px auto; background: #fffdf8; border: 1px solid #ddc48a; padding: 40px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 24px; border-bottom: 2px solid #c59a32; padding-bottom: 24px; margin-bottom: 24px; }}
    .brand {{ font-size: 30px; font-weight: 700; letter-spacing: 0.04em; color: #8f6918; }}
    .eyebrow {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em; color: #8f6918; }}
    .panel {{ border: 1px solid #ead9b3; padding: 18px; margin-top: 18px; background: #fffaf0; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: #8f6918; margin-bottom: 6px; }}
    .value {{ font-size: 16px; line-height: 1.7; white-space: pre-wrap; }}
    .total {{ font-size: 28px; font-weight: 700; color: #15120d; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="hero">
      <div>
        <div class="brand">Vashandi</div>
        <div class="eyebrow">Stored Invoice Export</div>
      </div>
      <div>
        <div class="label">Invoice</div>
        <div class="value">{invoice.title}</div>
        <div class="label" style="margin-top: 10px;">Status</div>
        <div class="value">{invoice.get_status_display()}</div>
      </div>
    </div>
    <div class="grid">
      <div class="panel">
        <div class="label">Provider</div>
        <div class="value">{invoice.provider.display_name}</div>
        <div class="label" style="margin-top: 10px;">Client</div>
        <div class="value">{invoice.client.display_name}</div>
      </div>
      <div class="panel">
        <div class="label">Linked RFQ</div>
        <div class="value">{invoice.rfq.title if invoice.rfq else 'Direct invoice'}</div>
        <div class="label" style="margin-top: 10px;">Due Date</div>
        <div class="value">{invoice.due_date or 'Not specified'}</div>
      </div>
    </div>
    <div class="panel">
      <div class="label">Scope of Work</div>
      <div class="value">{invoice.scope_of_work}</div>
    </div>
    <div class="panel">
      <div class="label">Line Items</div>
      <div class="value">{line_items}</div>
    </div>
    <div class="grid">
      <div class="panel">
        <div class="label">Notes</div>
        <div class="value">{notes}</div>
      </div>
      <div class="panel">
        <div class="label">Subtotal</div>
        <div class="value">{currency_symbol}{invoice.subtotal} {currency_code}</div>
        <div class="label" style="margin-top: 10px;">Tax</div>
        <div class="value">{currency_symbol}{invoice.tax_amount} {currency_code}</div>
        <div class="label" style="margin-top: 10px;">Total</div>
        <div class="total">{currency_symbol}{invoice.total_amount} {currency_code}</div>
      </div>
    </div>
  </div>
</body>
</html>"""
        response = HttpResponse(html, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{safe_title}.html"'
        return response


class ProjectTrackerViewSet(viewsets.ModelViewSet):
    """Milestone-based project tracker for awarded jobs."""

    queryset = ProjectTracker.objects.select_related('job', 'client', 'provider').prefetch_related('phases__tasks', 'disputes')
    serializer_class = ProjectTrackerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(Q(client=user) | Q(provider=user))

    def perform_create(self, serializer):
        user = self.request.user
        if user.current_role not in {'client', 'both'}:
            raise PermissionDenied('Only clients can create project trackers.')

        job = serializer.validated_data['job']
        if job.client != user:
            raise PermissionDenied('You can only create a tracker for your own job.')
        if not job.assigned_provider:
            raise PermissionDenied('Assign a provider before creating a project tracker.')

        client_signature = serializer.validated_data.get('client_signature', '').strip()
        tracker = serializer.save(
            client=user,
            provider=job.assigned_provider,
            status='draft',
            client_signed_at=timezone.now() if client_signature else None,
        )
        create_notification(
            recipient=job.assigned_provider,
            actor=user,
            notification_type=Notification.STATUS,
            title='New project tracker created',
            description=f'{user.display_name} created a project tracker for {job.title}.',
            related_object=tracker,
        )

    @action(detail=True, methods=['post'])
    def provider_sign(self, request, pk=None):
        tracker = self.get_object()
        if tracker.provider != request.user:
            return Response({'error': 'Only the assigned provider can sign the tracker.'}, status=status.HTTP_403_FORBIDDEN)

        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Provider signature is required.'}, status=status.HTTP_400_BAD_REQUEST)

        tracker.provider_signature = signature
        tracker.provider_signed_at = timezone.now()
        tracker.status = 'pending_client_approval'
        tracker.save(update_fields=['provider_signature', 'provider_signed_at', 'status', 'updated_at'])
        return Response(self.get_serializer(tracker).data)

    @action(detail=True, methods=['post'])
    def client_approve(self, request, pk=None):
        tracker = self.get_object()
        if tracker.client != request.user:
            return Response({'error': 'Only the client can approve the tracker.'}, status=status.HTTP_403_FORBIDDEN)

        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Client signature is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not tracker.provider_signature:
            return Response({'error': 'Wait for the provider to sign the tracker before client approval.'}, status=status.HTTP_400_BAD_REQUEST)

        if not tracker.phases.exists():
            return Response({'error': 'Add at least one phase before approving the tracker.'}, status=status.HTTP_400_BAD_REQUEST)

        tracker.client_signature = signature
        tracker.client_signed_at = timezone.now()
        tracker.approved_at = timezone.now()
        tracker.status = 'active'
        tracker.save(update_fields=['client_signature', 'client_signed_at', 'approved_at', 'status', 'updated_at'])
        return Response(self.get_serializer(tracker).data)


class ProjectPhaseViewSet(viewsets.ModelViewSet):
    queryset = ProjectPhase.objects.select_related('tracker', 'tracker__client', 'tracker__provider').prefetch_related('tasks')
    serializer_class = ProjectPhaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        tracker_id = self.request.query_params.get('tracker')
        if not user.is_staff:
            queryset = queryset.filter(Q(tracker__client=user) | Q(tracker__provider=user))
        if tracker_id:
            queryset = queryset.filter(tracker_id=tracker_id)
        return queryset

    def perform_create(self, serializer):
        tracker = serializer.validated_data['tracker']
        if tracker.client != self.request.user:
            raise PermissionDenied('Only the client can add project phases.')
        serializer.save()

    @action(detail=True, methods=['post'])
    def submit_plan(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can submit a phase plan.'}, status=status.HTTP_403_FORBIDDEN)

        provider_plan = request.data.get('provider_plan', '').strip()
        if not provider_plan:
            return Response({'error': 'Provider plan is required.'}, status=status.HTTP_400_BAD_REQUEST)

        phase.provider_plan = provider_plan
        phase.provider_notes = request.data.get('provider_notes', '').strip()
        phase.plan_status = 'pending_client_approval'
        phase.save(update_fields=['provider_plan', 'provider_notes', 'plan_status', 'updated_at'])
        return Response(self.get_serializer(phase).data)

    @action(detail=True, methods=['post'])
    def approve_plan(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.client != request.user:
            return Response({'error': 'Only the client can approve a phase plan.'}, status=status.HTTP_403_FORBIDDEN)

        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Client signature is required.'}, status=status.HTTP_400_BAD_REQUEST)

        phase.client_approval_signature = signature
        phase.client_approved_at = timezone.now()
        phase.plan_status = 'approved'
        phase.save(update_fields=['client_approval_signature', 'client_approved_at', 'plan_status', 'updated_at'])
        if phase.tracker.status == 'draft':
            phase.tracker.status = 'pending_client_approval'
            phase.tracker.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(phase).data)

    @action(detail=True, methods=['post'])
    def start_phase(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can start a phase.'}, status=status.HTTP_403_FORBIDDEN)
        if phase.plan_status != 'approved':
            return Response({'error': 'Approve the phase plan before starting work.'}, status=status.HTTP_400_BAD_REQUEST)
        if phase.tracker.phases.filter(sequence__lt=phase.sequence).exclude(fund_release_status='released').exists():
            return Response({'error': 'Previous phases must be paid and acknowledged before the next phase can start.'}, status=status.HTTP_400_BAD_REQUEST)
        phase.execution_status = 'in_progress'
        phase.save(update_fields=['execution_status', 'updated_at'])
        return Response(self.get_serializer(phase).data)

    @action(detail=True, methods=['post'])
    def submit_completion(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can submit phase completion.'}, status=status.HTTP_403_FORBIDDEN)
        if phase.tasks.exclude(status='completed').exists():
            return Response({'error': 'Complete all tasks before submitting the phase.'}, status=status.HTTP_400_BAD_REQUEST)

        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Provider signature is required.'}, status=status.HTTP_400_BAD_REQUEST)

        phase.provider_submission_signature = signature
        phase.provider_evidence_notes = request.data.get('provider_evidence_notes', '').strip()
        if request.FILES.get('provider_evidence_image'):
            phase.provider_evidence_image = request.FILES['provider_evidence_image']
        phase.provider_submitted_at = timezone.now()
        phase.execution_status = 'submitted'
        phase.fund_release_status = 'pending_release'
        phase.save()
        phase.tracker.status = 'in_review'
        phase.tracker.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(phase).data)

    @action(detail=True, methods=['post'])
    def approve_completion(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.client != request.user:
            return Response({'error': 'Only the client can approve phase completion.'}, status=status.HTTP_403_FORBIDDEN)

        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Client signature is required.'}, status=status.HTTP_400_BAD_REQUEST)

        phase.client_approval_signature = signature
        phase.client_approved_at = timezone.now()
        phase.execution_status = 'approved'
        phase.fund_release_status = 'pending_release'
        phase.save(update_fields=['client_approval_signature', 'client_approved_at', 'execution_status', 'fund_release_status', 'updated_at'])

        create_notification(
            recipient=phase.tracker.provider,
            actor=request.user,
            notification_type=Notification.STATUS,
            title='Phase approved, payment proof pending',
            description=f'{request.user.display_name} approved {phase.title}. Upload payment proof next so the phase can be released.',
            related_object=phase,
        )

        tracker = phase.tracker
        tracker.status = 'active'
        tracker.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(phase).data)

    @action(detail=True, methods=['post'])
    def submit_payment_proof(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.client != request.user:
            return Response({'error': 'Only the client can submit payment proof.'}, status=status.HTTP_403_FORBIDDEN)
        if phase.execution_status != 'approved':
            return Response({'error': 'Approve the completed phase before uploading payment proof.'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.FILES.get('payment_proof_file'):
            return Response({'error': 'Payment proof file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        phase.payment_proof_file = request.FILES['payment_proof_file']
        phase.payment_proof_notes = request.data.get('payment_proof_notes', '').strip()
        phase.payment_proof_uploaded_at = timezone.now()
        phase.fund_release_status = 'payment_submitted'
        phase.save(update_fields=['payment_proof_file', 'payment_proof_notes', 'payment_proof_uploaded_at', 'fund_release_status', 'updated_at'])

        create_notification(
            recipient=phase.tracker.provider,
            actor=request.user,
            notification_type=Notification.INVOICE,
            title='Payment proof uploaded',
            description=f'{request.user.display_name} uploaded payment proof for {phase.title}. Acknowledge receipt to release the phase.',
            related_object=phase,
        )
        return Response(self.get_serializer(phase).data)

    @action(detail=True, methods=['post'])
    def acknowledge_payment(self, request, pk=None):
        phase = self.get_object()
        if phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can acknowledge payment.'}, status=status.HTTP_403_FORBIDDEN)
        if phase.fund_release_status != 'payment_submitted':
            return Response({'error': 'Payment proof must be uploaded before acknowledgement.'}, status=status.HTTP_400_BAD_REQUEST)

        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Acknowledgement signature is required.'}, status=status.HTTP_400_BAD_REQUEST)

        phase.payment_acknowledgement_signature = signature
        phase.payment_acknowledgement_notes = request.data.get('payment_acknowledgement_notes', '').strip()
        phase.payment_acknowledged_at = timezone.now()
        phase.fund_release_status = 'released'
        phase.save(update_fields=[
            'payment_acknowledgement_signature', 'payment_acknowledgement_notes',
            'payment_acknowledged_at', 'fund_release_status', 'updated_at'
        ])

        tracker = phase.tracker
        if not tracker.phases.exclude(execution_status='approved', fund_release_status='released').exists():
            tracker.status = 'completed'
        else:
            tracker.status = 'active'
        tracker.save(update_fields=['status', 'updated_at'])

        create_notification(
            recipient=phase.tracker.client,
            actor=request.user,
            notification_type=Notification.INVOICE,
            title='Payment acknowledged',
            description=f'{request.user.display_name} acknowledged payment for {phase.title}.',
            related_object=phase,
        )
        return Response(self.get_serializer(phase).data)


class ProjectTaskViewSet(viewsets.ModelViewSet):
    queryset = ProjectTask.objects.select_related('phase', 'phase__tracker')
    serializer_class = ProjectTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        phase_id = self.request.query_params.get('phase')
        if not user.is_staff:
            queryset = queryset.filter(Q(phase__tracker__client=user) | Q(phase__tracker__provider=user))
        if phase_id:
            queryset = queryset.filter(phase_id=phase_id)
        return queryset

    def perform_create(self, serializer):
        phase = serializer.validated_data['phase']
        if phase.tracker.client != self.request.user:
            raise PermissionDenied('Only the client can define phase tasks.')
        serializer.save()

    @action(detail=True, methods=['post'])
    def provider_plan(self, request, pk=None):
        task = self.get_object()
        if task.phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can draft the task plan.'}, status=status.HTTP_403_FORBIDDEN)

        task.provider_execution_plan = request.data.get('provider_execution_plan', '').strip()
        task.provider_description = request.data.get('provider_description', '').strip()
        if not task.provider_execution_plan:
            return Response({'error': 'Task execution plan is required.'}, status=status.HTTP_400_BAD_REQUEST)
        task.status = 'planned'
        task.provider_updated_at = timezone.now()
        task.save(update_fields=['provider_execution_plan', 'provider_description', 'status', 'provider_updated_at', 'updated_at'])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def approve_plan(self, request, pk=None):
        task = self.get_object()
        if task.phase.tracker.client != request.user:
            return Response({'error': 'Only the client can approve the task plan.'}, status=status.HTTP_403_FORBIDDEN)
        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Client signature is required.'}, status=status.HTTP_400_BAD_REQUEST)
        task.client_plan_signature = signature
        task.client_approved_at = timezone.now()
        task.status = 'approved_to_start'
        task.save(update_fields=['client_plan_signature', 'client_approved_at', 'status', 'updated_at'])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        if task.phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can start this task.'}, status=status.HTTP_403_FORBIDDEN)
        if task.status != 'approved_to_start':
            return Response({'error': 'Approve the task plan before starting.'}, status=status.HTTP_400_BAD_REQUEST)
        task.status = 'in_progress'
        task.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def submit_completion(self, request, pk=None):
        task = self.get_object()
        if task.phase.tracker.provider != request.user:
            return Response({'error': 'Only the provider can submit task completion.'}, status=status.HTTP_403_FORBIDDEN)
        task.completion_notes = request.data.get('completion_notes', '').strip()
        task.status = 'submitted'
        task.completed_at = timezone.now()
        task.save(update_fields=['completion_notes', 'status', 'completed_at', 'updated_at'])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def approve_completion(self, request, pk=None):
        task = self.get_object()
        if task.phase.tracker.client != request.user:
            return Response({'error': 'Only the client can approve task completion.'}, status=status.HTTP_403_FORBIDDEN)
        signature = request.data.get('signature', '').strip()
        if not signature:
            return Response({'error': 'Client signature is required.'}, status=status.HTTP_400_BAD_REQUEST)
        task.client_completion_signature = signature
        task.client_approved_at = timezone.now()
        task.status = 'completed'
        task.save(update_fields=['client_completion_signature', 'client_approved_at', 'status', 'updated_at'])
        return Response(self.get_serializer(task).data)


class ProjectDisputeViewSet(viewsets.ModelViewSet):
    queryset = ProjectDispute.objects.select_related('tracker', 'phase', 'task', 'raised_by', 'resolved_by')
    serializer_class = ProjectDisputeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(Q(tracker__client=user) | Q(tracker__provider=user))

    def perform_create(self, serializer):
        tracker = serializer.validated_data['tracker']
        user = self.request.user
        if user not in {tracker.client, tracker.provider} and not user.is_staff:
            raise PermissionDenied('Only project participants can raise a dispute.')

        dispute = serializer.save(raised_by=user)
        tracker.status = 'disputed'
        tracker.save(update_fields=['status', 'updated_at'])
        if dispute.phase:
            dispute.phase.execution_status = 'disputed'
            dispute.phase.fund_release_status = 'held'
            dispute.phase.save(update_fields=['execution_status', 'fund_release_status', 'updated_at'])
        if dispute.task:
            dispute.task.status = 'disputed'
            dispute.task.save(update_fields=['status', 'updated_at'])

        notify_admins(
            actor=user,
            title='Project dispute flagged',
            description=f'{user.display_name} flagged a dispute on {tracker.title}.',
            related_object=dispute,
        )

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        if not request.user.is_staff:
            return Response({'error': 'Only admins can resolve disputes.'}, status=status.HTTP_403_FORBIDDEN)

        resolution = request.data.get('admin_resolution', '').strip()
        status_value = request.data.get('status', 'resolved')
        if not resolution:
            return Response({'error': 'Admin resolution notes are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if status_value not in {'resolved', 'dismissed'}:
            return Response({'error': 'Invalid dispute status.'}, status=status.HTTP_400_BAD_REQUEST)

        dispute.admin_resolution = resolution
        dispute.status = status_value
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.save(update_fields=['admin_resolution', 'status', 'resolved_by', 'resolved_at', 'updated_at'])

        if dispute.task and dispute.task.status == 'disputed':
            restore_task_state_after_dispute(dispute.task)
        if dispute.phase and dispute.phase.execution_status == 'disputed':
            restore_phase_state_after_dispute(dispute.phase)

        tracker = dispute.tracker
        if not tracker.disputes.filter(status='open').exists():
            tracker.status = 'active'
            tracker.save(update_fields=['status', 'updated_at'])

        for participant in {tracker.client, tracker.provider}:
            create_notification(
                recipient=participant,
                actor=request.user,
                notification_type=Notification.DISPUTE,
                title='Project dispute resolved',
                description=f'An admin marked the dispute on {tracker.title} as {status_value}.',
                related_object=dispute,
            )
        return Response(self.get_serializer(dispute).data)


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
        send_bid_email_notification(
            recipient=bid.provider,
            actor=request.user,
            subject=f'Bid update for {bid.job.title}',
            heading='Bid Rejected',
            intro=f'{request.user.display_name} rejected your bid.',
            job_title=bid.job.title,
            amount=bid.amount,
            extra_label='Status',
            extra_value='Rejected',
        )
        serializer = self.get_serializer(bid)
        return Response(serializer.data)


class TradeCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only category tree for dashboard filters and forms."""

    serializer_class = TradeCategorySerializer
    permission_classes = [permissions.AllowAny]
    queryset = TradeCategory.objects.filter(is_active=True).prefetch_related('children')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.filter(parent__isnull=True)
        return queryset.order_by('sort_order', 'name')

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
            description=f'{request.user.display_name} withdrew their bid on {bid.job.title}.',
            related_object=bid.job
        )
        send_bid_email_notification(
            recipient=bid.job.client,
            actor=request.user,
            subject=f'Bid withdrawn for {bid.job.title}',
            heading='Bid Withdrawn',
            intro=f'{request.user.display_name} withdrew their bid.',
            job_title=bid.job.title,
            amount=bid.amount,
            extra_label='Status',
            extra_value='Withdrawn',
        )
        serializer = self.get_serializer(bid)
        return Response(serializer.data)


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only African country directory."""

    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]
    queryset = Country.objects.filter(is_active=True).order_by('name')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_api(request):
    """Shared analytics for RFQs and invoice pricing."""
    user = request.user

    shared_service_counts = list(
        RFQ.objects.values('service__title', 'service__category')
        .annotate(rfq_count=Count('id'))
        .order_by('-rfq_count')[:5]
    )
    shared_pricing = Invoice.objects.aggregate(
        average=Avg('total_amount'),
        minimum=Min('total_amount'),
        maximum=Max('total_amount'),
    )

    if user.current_role == 'provider':
        user_rfqs = RFQ.objects.filter(provider=user)
        user_invoices = Invoice.objects.filter(provider=user)
        customer_count = user_rfqs.values('client').distinct().count()
        service_breakdown = list(
            user_rfqs.values('service__title')
            .annotate(rfq_count=Count('id'))
            .order_by('-rfq_count')
        )
    else:
        user_rfqs = RFQ.objects.filter(client=user)
        user_invoices = Invoice.objects.filter(client=user)
        customer_count = 1 if user_rfqs.exists() else 0
        service_breakdown = list(
            user_rfqs.values('service__title')
            .annotate(rfq_count=Count('id'))
            .order_by('-rfq_count')
        )

    user_pricing = user_invoices.aggregate(
        average=Avg('total_amount'),
        minimum=Min('total_amount'),
        maximum=Max('total_amount'),
    )

    return Response({
        'rfqs_total': user_rfqs.count(),
        'invoices_total': user_invoices.count(),
        'customers_sent_rfq_count': customer_count,
        'services_most_requested': service_breakdown,
        'shared_services_most_requested': shared_service_counts,
        'pricing': {
            'average': user_pricing['average'] or 0,
            'minimum': user_pricing['minimum'] or 0,
            'maximum': user_pricing['maximum'] or 0,
        },
        'shared_pricing': {
            'average': shared_pricing['average'] or 0,
            'minimum': shared_pricing['minimum'] or 0,
            'maximum': shared_pricing['maximum'] or 0,
        }
    })


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

