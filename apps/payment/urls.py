from django.urls import path
from . import views

urlpatterns = [
    # Платежи пользователя
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/<int:payment_id>/status/', views.payment_status, name='payment-status'),
    path('payments/<int:payment_id>/cancel/', views.cancel_payment, name='cancel-payment'),
    path('payments/<int:payment_id>/retry/', views.retry_payment, name='retry-payment'),
    path('payments/history/', views.user_payment_history, name='user-payment-history'),

    # Создание checkout сессии
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),

    # Возвраты (только для администраторов)
    path('refunds/', views.RefundListView.as_view(), name='refund-list'),
    path('refunds/<int:pk>/', views.RefundDetailView.as_view(), name='refund-detail'),
    path('payments/<int:payment_id>/refund/', views.create_refund, name='create-refund'),

    # Аналитика (только для администраторов)
    path('analytics/', views.payment_analytics, name='payment-analytics'),

    # Webhook для Stripe
    path('webhooks/stripe/', views.stripe_webhook, name='stripe-webhook'),
]