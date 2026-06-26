from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Service, Job, Review, Message, Bid, Notification, RFQ, Invoice, TradeCategory

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
        return User.objects.create_user(password=password, **validated_data)


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
    category_name = serializers.SerializerMethodField()
    trade_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = ['id', 'provider', 'provider_name', 'provider_initials', 'provider_location',
                  'category', 'category_ref', 'category_name', 'trade_name', 'title', 'description', 'price_per_hour', 'experience_years',
                  'response_time', 'is_active', 'average_rating', 'review_count', 
                  'jobs_completed', 'reviews', 'created_at', 'updated_at']
        read_only_fields = ['id', 'provider', 'created_at', 'updated_at']
        extra_kwargs = {
            'category': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        if not attrs.get('category_ref') and not attrs.get('category'):
            raise serializers.ValidationError({'category_ref': 'Select a category.'})
        return attrs

    def get_category_name(self, obj):
        return obj.category_ref.name if obj.category_ref else obj.category.replace('_', ' ').title()

    def get_trade_name(self, obj):
        if obj.category_ref:
            return obj.category_ref.trade_name
        return obj.category.replace('_', ' ').title()


class ServiceListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing services without reviews"""
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    provider_initials = serializers.CharField(source='provider.avatar_initials', read_only=True)
    provider_location = serializers.CharField(source='provider.location', read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    jobs_completed = serializers.ReadOnlyField()
    category_name = serializers.SerializerMethodField()
    trade_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = ['id', 'provider', 'provider_name', 'provider_initials', 'provider_location',
                  'category', 'category_ref', 'category_name', 'trade_name', 'title', 'description', 'price_per_hour', 'experience_years',
                  'response_time', 'is_active', 'average_rating', 'review_count', 
                  'jobs_completed', 'created_at']
        read_only_fields = ['id', 'provider', 'created_at']

    def get_category_name(self, obj):
        return obj.category_ref.name if obj.category_ref else obj.category.replace('_', ' ').title()

    def get_trade_name(self, obj):
        if obj.category_ref:
            return obj.category_ref.trade_name
        return obj.category.replace('_', ' ').title()


class JobSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='assigned_provider.get_full_name', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)
    bids = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    trade_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = ['id', 'client', 'client_name', 'service', 'service_title', 
                  'assigned_provider', 'provider_name', 'title', 'category', 
                  'category_ref', 'category_name', 'trade_name', 'description', 'budget', 'location', 'deadline', 'status',
                  'created_at', 'updated_at', 'bids']
        read_only_fields = ['id', 'client', 'created_at', 'updated_at']
        extra_kwargs = {
            'category': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        if not attrs.get('category_ref') and not attrs.get('category'):
            raise serializers.ValidationError({'category_ref': 'Select a category.'})
        return attrs

    def get_bids(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []

        can_view = request.user == obj.client or request.user == obj.assigned_provider
        if not can_view and obj.bids.filter(provider=request.user).exists():
            can_view = True

        if can_view:
            bids = obj.bids.select_related('provider').all()
            return BidSerializer(bids, many=True, context=self.context).data
        return []

    def get_category_name(self, obj):
        return obj.category_ref.name if obj.category_ref else obj.category.replace('_', ' ').title()

    def get_trade_name(self, obj):
        if obj.category_ref:
            return obj.category_ref.trade_name
        return obj.category.replace('_', ' ').title()


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    sender_initials = serializers.CharField(source='sender.avatar_initials', read_only=True)
    recipient_initials = serializers.CharField(source='recipient.avatar_initials', read_only=True)
    is_sent_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'sender_initials', 'recipient',
                  'recipient_name', 'recipient_initials', 'service', 'job',
                  'content', 'is_read', 'created_at', 'is_sent_by_user']
        read_only_fields = ['id', 'sender', 'created_at']

    def get_is_sent_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False


class BidSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    provider_initials = serializers.CharField(source='provider.avatar_initials', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_status = serializers.CharField(source='job.get_status_display', read_only=True)
    
    class Meta:
        model = Bid
        fields = ['id', 'provider', 'provider_name', 'provider_initials', 'job', 'job_title',
                  'job_status', 'amount', 'proposal_message', 'timeline', 'is_accepted',
                  'withdrawn', 'created_at', 'updated_at']
        read_only_fields = ['id', 'provider', 'is_accepted', 'withdrawn', 'created_at', 'updated_at']

    def validate_proposal_message(self, value):
        if len(value.strip()) < 50:
            raise serializers.ValidationError('Proposal must be at least 50 characters long.')
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Bid amount must be greater than zero.')
        return value


class RFQSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)
    service_category = serializers.SerializerMethodField()
    invoice_count = serializers.IntegerField(source='invoices.count', read_only=True)

    class Meta:
        model = RFQ
        fields = [
            'id', 'client', 'client_name', 'provider', 'provider_name', 'service', 'service_title',
            'service_category', 'title', 'requirements', 'quantity', 'target_budget',
            'preferred_start_date', 'status', 'invoice_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'client', 'provider', 'created_at', 'updated_at', 'invoice_count']

    def get_service_category(self, obj):
        if obj.service and obj.service.category_ref:
            return obj.service.category_ref.name
        return obj.service.category.replace('_', ' ').title() if obj.service else ''


class InvoiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    rfq_title = serializers.CharField(source='rfq.title', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'provider', 'provider_name', 'client', 'client_name', 'rfq', 'rfq_title',
            'service', 'service_title', 'title', 'scope_of_work', 'line_items', 'subtotal',
            'tax_amount', 'total_amount', 'notes', 'due_date', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'provider', 'client', 'service', 'total_amount', 'created_at', 'updated_at']

    def validate_subtotal(self, value):
        if value < 0:
            raise serializers.ValidationError('Subtotal cannot be negative.')
        return value

    def validate_tax_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Tax amount cannot be negative.')
        return value


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'description', 'actor_name',
                  'related_object_id', 'related_model', 'is_read', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor else None


class TradeCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    trade_name = serializers.CharField(read_only=True)

    class Meta:
        model = TradeCategory
        fields = ['id', 'name', 'slug', 'parent', 'trade_name', 'children']

    def get_children(self, obj):
        children = obj.children.filter(is_active=True).order_by('sort_order', 'name')
        return TradeCategorySerializer(children, many=True).data
