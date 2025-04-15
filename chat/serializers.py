from rest_framework import serializers
from .models import User, UserProfile, ChatHistory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested User Data (Optional)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'account_status', 'account_create_date', 'subscription_expiry',
            'street_address', 'city', 'state', 'zip_code', 'phone_number',
            'date_of_birth', 'gender', 'preferred_name', 'details', 'voice_profile'
        ]


class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'message', 'timestamp', 'is_user_message']


class UserProfileCreateSerializer(serializers.ModelSerializer):
    """ Serializer for creating/updating user profiles for the project"""

    class Meta:
        model = UserProfile
        fields = ['user', 'street_address', 'city', 'state',
                  'zip_code', 'phone_number', 'date_of_birth', 'gender']

    def validate(self, data):
        instance = UserProfile(**data)
        instance.clean()
        return data
