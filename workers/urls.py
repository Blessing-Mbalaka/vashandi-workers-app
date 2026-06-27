from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'jobs', views.JobViewSet, basename='job')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'bids', views.BidViewSet, basename='bid')
router.register(r'rfqs', views.RFQViewSet, basename='rfq')
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'project-trackers', views.ProjectTrackerViewSet, basename='project-tracker')
router.register(r'project-phases', views.ProjectPhaseViewSet, basename='project-phase')
router.register(r'project-tasks', views.ProjectTaskViewSet, basename='project-task')
router.register(r'project-disputes', views.ProjectDisputeViewSet, basename='project-dispute')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'categories', views.TradeCategoryViewSet, basename='category')
router.register(r'countries', views.CountryViewSet, basename='country')

urlpatterns = [
    # Template views
    path('', views.dashboard_view, name='dashboard'),
    path('admin-portal/', views.admin_portal_view, name='admin-portal'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profiles/<int:user_id>/', views.public_profile_view, name='public-profile'),
    path('we-hit-a-snag/', views.snag_view, name='snag'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/register/', views.register_api, name='api-register'),
    path('api/login/', views.login_api, name='api-login'),
    path('api/user/', views.current_user_api, name='api-current-user'),
    path('api/admin/overview/', views.admin_overview_api, name='api-admin-overview'),
    path('api/admin/users/', views.admin_users_api, name='api-admin-users'),
    path('api/admin/users/<int:user_id>/', views.admin_user_detail_api, name='api-admin-user-detail'),
    path('api/toggle-role/', views.toggle_role_api, name='api-toggle-role'),
    path('api/stats/', views.dashboard_stats_api, name='api-stats'),
    path('api/analytics/', views.analytics_api, name='api-analytics'),
]
