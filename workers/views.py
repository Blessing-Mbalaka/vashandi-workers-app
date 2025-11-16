from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Service, Job, Review, Message
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ServiceSerializer,
    ServiceListSerializer, JobSerializer, ReviewSerializer, MessageSerializer
)

User = get_user_model()


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_api(request):
    """Get current user info"""
    return Response(UserSerializer(request.user).data)


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
        
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(provider__first_name__icontains=search) |
                Q(provider__last_name__icontains=search)
            )
        
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
        category = self.request.query_params.get('category')
        status_filter = self.request.query_params.get('status')
        
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(client=self.request.user)
    
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
        serializer.save(reviewer=self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for Message CRUD operations"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
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
            return Response({'error': 'Not authorized'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        message.is_read = True
        message.save()
        return Response({'message': 'Marked as read'})


@api_view(['GET'])
def dashboard_stats_api(request):
    """Get dashboard statistics"""
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
            }
        else:
            stats = {
                'active_workers': Service.objects.filter(is_active=True).count(),
                'jobs_posted': Job.objects.filter(client=request.user).count(),
                'satisfaction_rate': 98,  # Can be calculated based on reviews
                'support_available': '24/7',
            }
    else:
        stats = {
            'active_workers': Service.objects.filter(is_active=True).count(),
            'jobs_posted': Job.objects.count(),
            'satisfaction_rate': 98,
            'support_available': '24/7',
        }
    
    return Response(stats)

