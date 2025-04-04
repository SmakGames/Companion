from rest_framework import serializers
from .models import User, UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'user_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested User Data (Optional)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'street_address', 'city', 'state',
                  'zip_code', 'phone_number', 'date_of_birth', 'gender']


class UserProfileCreateSerializer(serializers.ModelSerializer):
    """ Serializer for creating/updating user profiles """

    class Meta:
        model = UserProfile
        fields = ['user', 'street_address', 'city', 'state',
                  'zip_code', 'phone_number', 'date_of_birth', 'gender']
