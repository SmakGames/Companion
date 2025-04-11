from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet, talk, talk_api

# Router for REST ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'user-profiles', UserProfileViewSet)

# URL patterns for the api and web
urlpatterns = [
    path("talk/", talk, name="talk"),
    path('', talk, name='talk'),  # Root for HTML chat
    path('talk_api/', talk_api, name='talk_api'),  # REST endpoint
    path('api/', include(router.urls)),  # REST API routes
]
