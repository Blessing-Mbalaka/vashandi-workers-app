from django.db import models
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """Extended user model with role support"""
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('provider', 'Service Provider'),
        ('both', 'Both'),
    ]
    
    current_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar_initials = models.CharField(max_length=2, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.avatar_initials and self.first_name and self.last_name:
            self.avatar_initials = f"{self.first_name[0]}{self.last_name[0]}".upper()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.current_role})"


class TradeCategory(models.Model):
    """Admin-managed trade and subtrade taxonomy."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Trade categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def trade_name(self):
        return self.parent.name if self.parent else self.name


class Service(models.Model):
    """Service offerings by providers"""
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.CharField(max_length=100)
    category_ref = models.ForeignKey(TradeCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='services')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    experience_years = models.IntegerField(default=0)
    response_time = models.CharField(max_length=50, default='24h')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.provider.get_full_name()}"

    def save(self, *args, **kwargs):
        if self.category_ref:
            self.category = self.category_ref.slug
        elif self.category and not self.category_ref_id:
            self.category_ref = TradeCategory.objects.filter(slug=self.category).first()
        super().save(*args, **kwargs)
    
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0.0
    
    @property
    def review_count(self):
        return self.reviews.count()
    
    @property
    def jobs_completed(self):
        return self.jobs.filter(status='completed').count()


class Job(models.Model):
    """Jobs posted by clients"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    assigned_provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    category_ref = models.ForeignKey(TradeCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs')
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=100)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.client.get_full_name()}"

    def save(self, *args, **kwargs):
        if self.category_ref:
            self.category = self.category_ref.slug
        elif self.category and not self.category_ref_id:
            self.category_ref = TradeCategory.objects.filter(slug=self.category).first()
        super().save(*args, **kwargs)


class Review(models.Model):
    """Reviews for services"""
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='review')
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='neutral')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['service', 'reviewer', 'job']
    
    def __str__(self):
        return f"Review by {self.reviewer.get_full_name()} - {self.rating}⭐"
    
    def save(self, *args, **kwargs):
        # Auto-detect sentiment based on rating if not set
        if not self.sentiment:
            if self.rating >= 4:
                self.sentiment = 'positive'
            elif self.rating == 3:
                self.sentiment = 'neutral'
            else:
                self.sentiment = 'negative'
        super().save(*args, **kwargs)


class Message(models.Model):
    """Messages between users"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender.get_full_name()} to {self.recipient.get_full_name()}"


class Bid(models.Model):
    """Bid submitted by a provider for a job"""

    TIMELINE_CHOICES = [
        ('asap', 'ASAP'),
        ('1_week', 'Within 1 week'),
        ('2_weeks', 'Within 2 weeks'),
        ('30_days', 'Within 30 days'),
        ('custom', 'Custom date'),
    ]

    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    proposal_message = models.TextField()
    timeline = models.CharField(max_length=20, choices=TIMELINE_CHOICES)
    is_accepted = models.BooleanField(default=False)
    withdrawn = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['provider', 'job']

    def __str__(self):
        return f"Bid by {self.provider.get_full_name()} on {self.job.title}"


class RFQ(models.Model):
    """Request for quote sent by a client to a provider."""

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('quoted', 'Quoted'),
        ('accepted', 'Accepted'),
        ('closed', 'Closed'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rfqs_sent')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rfqs_received')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='rfqs')
    title = models.CharField(max_length=200)
    requirements = models.TextField()
    quantity = models.PositiveIntegerField(default=1)
    target_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    preferred_start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"RFQ {self.title} from {self.client.get_full_name()} to {self.provider.get_full_name()}"


class Invoice(models.Model):
    """Invoice or quote generated by a provider for a client."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices_created')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices_received')
    rfq = models.ForeignKey(RFQ, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    title = models.CharField(max_length=200)
    scope_of_work = models.TextField()
    line_items = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    notes = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.total_amount = (self.subtotal or Decimal('0.00')) + (self.tax_amount or Decimal('0.00'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.title} for {self.client.get_full_name()}"


class Notification(models.Model):
    """System notifications for users"""

    MESSAGE = 'message'
    BID = 'bid'
    STATUS = 'status_change'
    REVIEW = 'review'
    RFQ = 'rfq'
    INVOICE = 'invoice'
    NOTIFICATION_TYPES = [
        (MESSAGE, 'Message'),
        (BID, 'Bid'),
        (STATUS, 'Status Change'),
        (REVIEW, 'Review'),
        (RFQ, 'RFQ'),
        (INVOICE, 'Invoice'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=150)
    description = models.TextField()
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_model = models.CharField(max_length=100, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
