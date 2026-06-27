from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    User, Service, Job, Review, Message, Bid, Notification, TradeCategory, Country,
    ProjectTracker, ProjectPhase, ProjectTask, ProjectDispute,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'display_name', 'current_role', 'account_type', 'country', 'verification_status', 'is_staff']
    list_filter = ['current_role', 'account_type', 'verification_status', 'country', 'is_staff', 'is_superuser']
    actions = ['approve_verification', 'reject_verification']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {'fields': ('current_role', 'account_type', 'phone', 'location', 'country', 'bio', 'avatar_initials')}),
        ('Company Details', {'fields': ('company_name', 'company_website', 'vat_number')}),
        ('Verification', {'fields': ('verification_status', 'verification_document_link', 'verification_document', 'verification_notes', 'verified_at', 'reviewed_by')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Profile', {'fields': ('current_role', 'account_type', 'phone', 'location', 'country')}),
    )
    readonly_fields = ['verification_document_link', 'verified_at', 'reviewed_by']

    def verification_document_link(self, obj):
        if obj.verification_document:
            return format_html('<a href="{}" target="_blank" rel="noopener">View uploaded document</a>', obj.verification_document.url)
        return 'No document uploaded'
    verification_document_link.short_description = 'Verification document'

    @admin.action(description='Approve selected verification documents')
    def approve_verification(self, request, queryset):
        queryset.update(
            verification_status='approved',
            verified_at=timezone.now(),
            reviewed_by_id=request.user.id,
        )

    @admin.action(description='Mark selected verification documents as rejected')
    def reject_verification(self, request, queryset):
        queryset.update(
            verification_status='rejected',
            reviewed_by_id=request.user.id,
            verified_at=None,
        )


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'currency_code', 'currency_symbol', 'phone_code', 'is_active']
    list_filter = ['is_active', 'currency_code']
    search_fields = ['name', 'code', 'currency_code']


@admin.register(TradeCategory)
class TradeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'slug', 'sort_order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug', 'parent__name']
    ordering = ['parent__name', 'sort_order', 'name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'category_ref', 'category', 'price_per_hour', 'is_active', 'average_rating', 'created_at']
    list_filter = ['category_ref', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'provider__username', 'provider__first_name', 'provider__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'client', 'category_ref', 'category', 'budget', 'status', 'created_at']
    list_filter = ['category_ref', 'status', 'created_at']
    search_fields = ['title', 'description', 'client__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['service', 'reviewer', 'rating', 'sentiment', 'created_at']
    list_filter = ['rating', 'sentiment', 'created_at']
    search_fields = ['comment', 'reviewer__username', 'service__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'service', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['content', 'sender__username', 'recipient__username']
    readonly_fields = ['created_at']


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['job', 'provider', 'amount', 'timeline', 'is_accepted', 'withdrawn', 'created_at']
    list_filter = ['timeline', 'is_accepted', 'withdrawn']
    search_fields = ['job__title', 'provider__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'description', 'recipient__username']
    readonly_fields = ['created_at']


@admin.register(ProjectTracker)
class ProjectTrackerAdmin(admin.ModelAdmin):
    list_display = ['title', 'job', 'client', 'provider', 'status', 'approved_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'job__title', 'client__username', 'provider__username']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'client_signed_at', 'provider_signed_at']


@admin.register(ProjectPhase)
class ProjectPhaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'tracker', 'sequence', 'plan_status', 'execution_status', 'fund_release_status', 'planned_amount']
    list_filter = ['plan_status', 'execution_status', 'fund_release_status']
    search_fields = ['title', 'tracker__title', 'tracker__job__title']
    readonly_fields = [
        'created_at', 'updated_at', 'provider_submitted_at', 'client_approved_at',
        'payment_proof_uploaded_at', 'payment_acknowledged_at'
    ]


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'phase', 'sequence', 'status', 'client_approved_at', 'completed_at']
    list_filter = ['status']
    search_fields = ['title', 'phase__title', 'phase__tracker__title']
    readonly_fields = ['created_at', 'updated_at', 'provider_updated_at', 'client_approved_at', 'completed_at']


@admin.register(ProjectDispute)
class ProjectDisputeAdmin(admin.ModelAdmin):
    list_display = ['tracker', 'phase', 'task', 'raised_by', 'status', 'resolved_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['tracker__title', 'reason', 'raised_by__username']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
