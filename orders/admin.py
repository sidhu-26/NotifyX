from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "amount", "status", "razorpay_order_id", "razorpay_payment_id", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "razorpay_order_id", "razorpay_payment_id"]
    readonly_fields = ["created_at"]
