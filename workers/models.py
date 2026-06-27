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
    ACCOUNT_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    current_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='individual')
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar_initials = models.CharField(max_length=2, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    company_website = models.URLField(blank=True)
    vat_number = models.CharField(max_length=80, blank=True)
    country = models.ForeignKey('Country', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    verification_document = models.FileField(upload_to='verification_documents/', blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_accounts')
    
    def save(self, *args, **kwargs):
        if not self.avatar_initials and self.first_name and self.last_name:
            self.avatar_initials = f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.account_type == 'company' and self.company_name:
            words = [word for word in self.company_name.split() if word]
            if words:
                self.avatar_initials = ''.join(word[0] for word in words[:2]).upper()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name()

    def get_full_name(self):
        full_name = super().get_full_name().strip()
        if full_name:
            return full_name
        if self.account_type == 'company' and self.company_name:
            return self.company_name
        return self.username

    @property
    def can_access_platform(self):
        return self.verification_status == 'approved'

    @property
    def currency_code(self):
        return self.country.currency_code if self.country else 'USD'

    @property
    def currency_symbol(self):
        return self.country.currency_symbol if self.country else '$'
    
    def __str__(self):
        return f"{self.display_name} ({self.current_role})"


class Country(models.Model):
    """African country and currency reference data."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=2, unique=True)
    currency_code = models.CharField(max_length=10)
    currency_name = models.CharField(max_length=120)
    currency_symbol = models.CharField(max_length=10, default='$')
    phone_code = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Countries'

    def __str__(self):
        return self.name


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
        return f"{self.title} by {self.provider.display_name}"

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
        return f"{self.title} - {self.client.display_name}"

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
        return f"Message from {self.sender.display_name} to {self.recipient.display_name}"


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
        return f"Bid by {self.provider.display_name} on {self.job.title}"


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
        return f"RFQ {self.title} from {self.client.display_name} to {self.provider.display_name}"


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
        subtotal = self.subtotal if isinstance(self.subtotal, Decimal) else Decimal(str(self.subtotal or '0.00'))
        tax_amount = self.tax_amount if isinstance(self.tax_amount, Decimal) else Decimal(str(self.tax_amount or '0.00'))
        self.total_amount = subtotal + tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.title} for {self.client.display_name}"


class ProjectTracker(models.Model):
    """Project planning and milestone tracking for an awarded job."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_client_approval', 'Pending Client Approval'),
        ('active', 'Active'),
        ('in_review', 'In Review'),
        ('disputed', 'Disputed'),
        ('completed', 'Completed'),
    ]

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='project_tracker')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_trackers_owned')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_trackers_assigned')
    title = models.CharField(max_length=200)
    overview = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    client_signature = models.CharField(max_length=200, blank=True)
    provider_signature = models.CharField(max_length=200, blank=True)
    client_signed_at = models.DateTimeField(null=True, blank=True)
    provider_signed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Project Tracker for {self.job.title}"

    @property
    def released_total(self):
        return sum(phase.planned_amount for phase in self.phases.filter(fund_release_status='released'))


class ProjectPhase(models.Model):
    """Client-defined project phase with provider delivery plan and release control."""

    PLAN_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_client_approval', 'Pending Client Approval'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
    ]
    EXECUTION_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted For Review'),
        ('approved', 'Approved'),
        ('disputed', 'Disputed'),
    ]
    FUND_RELEASE_STATUS_CHOICES = [
        ('locked', 'Locked'),
        ('pending_release', 'Pending Release'),
        ('payment_submitted', 'Payment Proof Submitted'),
        ('released', 'Released'),
        ('held', 'Held'),
    ]

    tracker = models.ForeignKey(ProjectTracker, on_delete=models.CASCADE, related_name='phases')
    sequence = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    client_scope = models.TextField(help_text='What the client expects in this phase.')
    provider_plan = models.TextField(blank=True)
    provider_notes = models.TextField(blank=True)
    planned_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    plan_status = models.CharField(max_length=30, choices=PLAN_STATUS_CHOICES, default='draft')
    execution_status = models.CharField(max_length=30, choices=EXECUTION_STATUS_CHOICES, default='not_started')
    fund_release_status = models.CharField(max_length=30, choices=FUND_RELEASE_STATUS_CHOICES, default='locked')
    provider_evidence_image = models.FileField(upload_to='project_phase_evidence/', blank=True)
    provider_evidence_notes = models.TextField(blank=True)
    payment_proof_file = models.FileField(upload_to='project_phase_payment_proofs/', blank=True)
    payment_proof_notes = models.TextField(blank=True)
    payment_proof_uploaded_at = models.DateTimeField(null=True, blank=True)
    payment_acknowledgement_signature = models.CharField(max_length=200, blank=True)
    payment_acknowledgement_notes = models.TextField(blank=True)
    payment_acknowledged_at = models.DateTimeField(null=True, blank=True)
    client_approval_signature = models.CharField(max_length=200, blank=True)
    provider_submission_signature = models.CharField(max_length=200, blank=True)
    provider_submitted_at = models.DateTimeField(null=True, blank=True)
    client_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence', 'id']

    def __str__(self):
        return f"{self.tracker.title} - Phase {self.sequence}: {self.title}"


class ProjectTask(models.Model):
    """Task builder under each project phase."""

    STATUS_CHOICES = [
        ('client_defined', 'Client Defined'),
        ('planned', 'Planned By Provider'),
        ('approved_to_start', 'Approved To Start'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted For Review'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
    ]

    phase = models.ForeignKey(ProjectPhase, on_delete=models.CASCADE, related_name='tasks')
    sequence = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    customer_definition = models.TextField()
    provider_execution_plan = models.TextField(blank=True)
    provider_description = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='client_defined')
    client_plan_signature = models.CharField(max_length=200, blank=True)
    client_completion_signature = models.CharField(max_length=200, blank=True)
    provider_updated_at = models.DateTimeField(null=True, blank=True)
    client_approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence', 'id']

    def __str__(self):
        return f"{self.phase.title} - {self.title}"


class ProjectDispute(models.Model):
    """Conflict raised by client or provider for admin resolution."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    tracker = models.ForeignKey(ProjectTracker, on_delete=models.CASCADE, related_name='disputes')
    phase = models.ForeignKey(ProjectPhase, null=True, blank=True, on_delete=models.SET_NULL, related_name='disputes')
    task = models.ForeignKey(ProjectTask, null=True, blank=True, on_delete=models.SET_NULL, related_name='disputes')
    raised_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_disputes_raised')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='project_disputes_resolved')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute on {self.tracker.title} ({self.status})"


class Notification(models.Model):
    """System notifications for users"""

    MESSAGE = 'message'
    BID = 'bid'
    STATUS = 'status_change'
    REVIEW = 'review'
    RFQ = 'rfq'
    INVOICE = 'invoice'
    DISPUTE = 'dispute'
    NOTIFICATION_TYPES = [
        (MESSAGE, 'Message'),
        (BID, 'Bid'),
        (STATUS, 'Status Change'),
        (REVIEW, 'Review'),
        (RFQ, 'RFQ'),
        (INVOICE, 'Invoice'),
        (DISPUTE, 'Dispute'),
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
