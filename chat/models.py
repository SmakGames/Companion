from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import phonenumbers


class UserProfile(models.Model):
    ACCOUNT_ACTIVE = 'A'
    ACCOUNT_SUSPENDED = 'S'

    ACCOUNT_CHOICES = [
        (ACCOUNT_ACTIVE, 'Active'),
        (ACCOUNT_SUSPENDED, 'Suspended'),
    ]

    GENDER_CHOICES = [
        ('', 'Select Gender'),  # Optional for forms
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        # Removed primary_key=True
    )
    account_status = models.CharField(
        max_length=1,
        choices=ACCOUNT_CHOICES,
        default=ACCOUNT_ACTIVE,
        help_text="Status of the user account."
    )
    account_create_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the account was created."
    )
    subscription_expiry = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when the subscription expires."
    )
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=6,  # Reduced from 10
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
    )
    preferred_name = models.CharField(max_length=100, blank=True)
    details = models.TextField(max_length=1000, blank=True)
    voice_profile = models.BinaryField(
        null=True,
        blank=True,
        help_text="Voice recognition data for user identification."
    )

    class Meta:
        indexes = [
            models.Index(fields=['account_status']),
            models.Index(fields=['account_create_date']),
        ]
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile of {self.user.username}"

    def clean(self):
        # Validate account_status
        if self.account_status not in [self.ACCOUNT_ACTIVE, self.ACCOUNT_SUSPENDED]:
            raise ValidationError("Invalid account status.")
        # Validate phone_number
        if self.phone_number:
            try:
                parsed = phonenumbers.parse(self.phone_number, None)
                if not phonenumbers.is_valid_number(parsed):
                    raise ValidationError("Invalid phone number format.")
            except phonenumbers.NumberParseException:
                raise ValidationError("Invalid phone number format.")
        # Check subscription status
        if self.subscription_expiry and self.subscription_expiry < timezone.now():
            self.account_status = self.ACCOUNT_SUSPENDED

    def save(self, *args, **kwargs):
        self.clean()  # Run validation
        super().save(*args, **kwargs)


class ChatHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_history",
    )
    message = models.TextField(max_length=5001)  # Added limit
    timestamp = models.DateTimeField(auto_now_add=True)
    is_user_message = models.BooleanField()

    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
        ]
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"

    def clean(self):
        if not self.message.strip():
            raise ValidationError("Message cannot be empty.")
