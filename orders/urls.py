"""
Order URL configuration.
"""

from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.CreateOrderView.as_view(), name="create-order"),
    path("list/", views.ListOrdersView.as_view(), name="list-orders"),
]
