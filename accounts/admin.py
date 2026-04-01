from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "username", "is_email_verified", "is_active", "created_at"]
    list_filter = ["is_email_verified", "is_active"]
    search_fields = ["email", "username"]
    readonly_fields = ["created_at"]
