from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Service, Job, Review, Message, Bid, Notification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'current_role', 'is_staff']
    list_filter = ['current_role', 'is_staff', 'is_superuser']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {'fields': ('current_role', 'phone', 'location', 'bio', 'avatar_initials')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Profile', {'fields': ('current_role', 'phone', 'location')}),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'category', 'price_per_hour', 'is_active', 'average_rating', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'provider__username', 'provider__first_name', 'provider__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'client', 'category', 'budget', 'status', 'created_at']
    list_filter = ['category', 'status', 'created_at']
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
