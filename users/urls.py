from django.urls import path

from .views import (PaymentListAPIView, UserRegistrationAPIView,
                    UserRetrieveUpdateDestroyAPIView, PaymentStatusAPIView,
                    payment_success, payment_cancel)

urlpatterns = [
    path("register/", UserRegistrationAPIView.as_view(), name="user_register"),
    path(
        "users/<int:pk>/",
        UserRetrieveUpdateDestroyAPIView.as_view(),
        name="user-detail",
    ),
    path("payments/", PaymentListAPIView.as_view(), name="payment-list"),
    path('payments/<int:pk>/status/', PaymentStatusAPIView.as_view(), name="payment-status"),
    path('payment/success/', payment_success, name='payment-success'),
    path('payment/cancel/', payment_cancel, name='payment-cancel')
]
