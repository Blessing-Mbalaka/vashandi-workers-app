from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Service, Job, Review, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name',
                  'current_role', 'phone', 'location', 'bio', 'avatar_initials']
        read_only_fields = ['id', 'avatar_initials']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 
                  'last_name', 'current_role', 'phone', 'location']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    reviewer_initials = serializers.CharField(source='reviewer.avatar_initials', read_only=True)
    days_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = ['id', 'service', 'reviewer', 'reviewer_name', 'reviewer_initials',
                  'job', 'rating', 'comment', 'sentiment', 'created_at', 'days_ago']
        read_only_fields = ['id', 'reviewer', 'created_at', 'sentiment']
    
    def get_days_ago(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        if delta.days == 0:
            return 'Today'
        elif delta.days == 1:
            return '1 day ago'
        elif delta.days < 7:
            return f'{delta.days} days ago'
        elif delta.days < 14:
            return '1 week ago'
        elif delta.days < 30:
            return f'{delta.days // 7} weeks ago'
        else:
            return f'{delta.days // 30} months ago'


class ServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    provider_initials = serializers.CharField(source='provider.avatar_initials', read_only=True)
    provider_location = serializers.CharField(source='provider.location', read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    jobs_completed = serializers.ReadOnlyField()
    reviews = ReviewSerializer(many=True, read_only=True)
    
    class Meta:
        model = Service
        fields = ['id', 'provider', 'provider_name', 'provider_initials', 'provider_location',
                  'category', 'title', 'description', 'price_per_hour', 'experience_years',
                  'response_time', 'is_active', 'average_rating', 'review_count', 
                  'jobs_completed', 'reviews', 'created_at', 'updated_at']
        read_only_fields = ['id', 'provider', 'created_at', 'updated_at']


class ServiceListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing services without reviews"""
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    provider_initials = serializers.CharField(source='provider.avatar_initials', read_only=True)
    provider_location = serializers.CharField(source='provider.location', read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    jobs_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = Service
        fields = ['id', 'provider', 'provider_name', 'provider_initials', 'provider_location',
                  'category', 'title', 'description', 'price_per_hour', 'experience_years',
                  'response_time', 'is_active', 'average_rating', 'review_count', 
                  'jobs_completed', 'created_at']
        read_only_fields = ['id', 'provider', 'created_at']


class JobSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='assigned_provider.get_full_name', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)
    
    class Meta:
        model = Job
        fields = ['id', 'client', 'client_name', 'service', 'service_title', 
                  'assigned_provider', 'provider_name', 'title', 'category', 
                  'description', 'budget', 'location', 'deadline', 'status',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'client', 'created_at', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'recipient', 'recipient_name',
                  'service', 'job', 'content', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']
