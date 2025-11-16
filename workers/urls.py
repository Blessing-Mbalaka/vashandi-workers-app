from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'jobs', views.JobViewSet, basename='job')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    # Template views
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/register/', views.register_api, name='api-register'),
    path('api/login/', views.login_api, name='api-login'),
    path('api/user/', views.current_user_api, name='api-current-user'),
    path('api/toggle-role/', views.toggle_role_api, name='api-toggle-role'),
    path('api/stats/', views.dashboard_stats_api, name='api-stats'),
]
