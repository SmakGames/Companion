from django.contrib import admin
from .models import UserProfile, ChatHistory

# Register your models here.


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user__first_name', 'user__last_name', 'preferred_name', 'city', 'state',
                    'account_status', 'subscription_expiry']
    search_fields = ['user__username', 'preferred_name', 'user__last_name']


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'message_preview', 'timestamp', 'is_user_message']
    list_filter = ['is_user_message']
    search_fields = ['message']

    def message_preview(self, obj):
        return obj.message[:50]
