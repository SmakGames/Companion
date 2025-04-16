from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet, ChatHistoryViewSet, talk, talk_api, weather_api, user_profile, RegisterView, PasswordResetView, PasswordChangeView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Swagger setup
schema_view = get_schema_view(
    openapi.Info(
        title="Companion API",
        default_version='v1',
        description="API for virtual companion app",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Router
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'chat-history', ChatHistoryViewSet, basename='chat-history')

# URLs
urlpatterns = [
    # Web chat
    path('', talk, name='chat_root'),
    path('chat/', talk, name='chat'),
    # APIs
    path('api/v1/talk/', talk_api, name='talk_api'),
    path('api/v1/weather/', weather_api, name='weather_api'),
    path('api/v1/user_profile/', user_profile, name='user_profile'),
    path('api/v1/', include(router.urls)),
    # JWT authentication
    path('api/v1/auth/register/', RegisterView.as_view(), name='register'),  # New
    path('api/v1/auth/password_reset/',
         PasswordResetView.as_view(), name='password_reset'),
    path('api/v1/auth/password_change/',
         PasswordChangeView.as_view(), name='password_change'),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/',
         TokenRefreshView.as_view(), name='token_refresh'),
    # Swagger
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),
]
