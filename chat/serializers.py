from rest_framework import serializers
from django.contrib.auth.models import User
from .models import User, UserProfile, ChatHistory
import hashlib


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']


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


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    preferred_name = serializers.CharField(max_length=100)  # Required
    city = serializers.CharField(
        max_length=100, required=False, default='Boston')
    security_answer = serializers.CharField(write_only=True)  # Added

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )
        # Hash security answer
        answer_hash = hashlib.sha256(
            validated_data['security_answer'].lower().encode()).hexdigest()
        UserProfile.objects.create(
            user=user,
            city=validated_data.get('city', 'Boston'),
            account_status='A',
            preferred_name=validated_data['preferred_name'],
            security_answer_hash=answer_hash,
        )
        return user


class PasswordResetSerializer(serializers.Serializer):
    username = serializers.CharField()
    security_answer = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(username=data['username'])
            try:
                # profile = user.userprofile  # Standard reverse relation
                profile = user.profile
                if not profile.security_answer_hash:
                    raise serializers.ValidationError(
                        "No security answer set.")
                answer_hash = hashlib.sha256(
                    data['security_answer'].lower().encode()).hexdigest()
                if answer_hash != profile.security_answer_hash:
                    raise serializers.ValidationError(
                        "Incorrect security answer.")
                data['user'] = user
                return data
            except UserProfile.DoesNotExist:
                raise serializers.ValidationError("User profile not found.")
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError("Incorrect old password.")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested User Data (Optional)
    # user = UserSerializer()  # Nested User Data (Optional)
    preferred_name = serializers.CharField(
        source='userprofile.preferred_name')  # Add
    city = serializers.CharField(source='userprofile.city')
    account_status = serializers.CharField(source='userprofile.account_status')

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'account_status', 'account_create_date', 'subscription_expiry',
            'street_address', 'city', 'state', 'zip_code', 'phone_number',
            'date_of_birth', 'gender', 'preferred_name', 'details', 'voice_profile'
        ]
