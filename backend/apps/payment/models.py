from django.db import models
from django.conf import settings
from django.utils import timezone

class Payment(models.Model):
    """ Модель оплаты """
    
    STATUS_CHOICES = (
        ("pending", "Ожидает оплаты"),
        ("processeing", "Обработка"),
        ("succeeded", "Успешно"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменен"),
        ("refunded", "Возвращен"),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("manual", "Ручная оплата"),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments', verbose_name='Пользователь')
    subscription = models.ForeignKey('subscribe.Subscription', on_delete=models.CASCADE, related_name='payments', null=True, blank=True, verbose_name='Подписка')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма оплаты')
    currency = models.CharField(max_length=3, default="USD", verbose_name='Валюта')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name='Статус оплаты')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="stripe", verbose_name='Способ оплаты')
    
    # Stripe 
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID платежного намерения Stripe')
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID сессии Stripe')
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID клиента Stripe')
    
    # Метаданные
    description = models.TextField(blank=True, verbose_name='Описание')
    metadata = models.JSONField(default=dict, verbose_name='Метаданные')
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата обработки')
    
    class Meta:
        db_table = 'payment'
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплаты'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']), 
            models.Index(fields=['stripe_payment_intent_id']), 
            models.Index(fields=['stripe_session_id']), 
            models.Index(fields=['-created_at']), 
        ]
        
    def __str__(self):
        return f"Оплата {self.id} - {self.user.username} - ${self.amount} ({self.status})"
    
    @property
    def is_successful(self):
        return self.status == "successful"
    
    @property
    def is_pending(self):
        return self.status in ['pending', 'processing']
    
    @property
    def can_be_refunded(self):
        return self.status == 'succeeded' and self.payment_method == "stripe"
    
    def mark_as_succeeded(self):
        self.status = "succeeded"
        self.processed_at = timezone.now()
        self.save()
        
    def mark_as_failed(self, reason=None):
        self.status = "failed"
        self.processed_at = timezone.now()
        if reason:
            self.metadata['failure_reason'] = reason
        self.save()
        
class PaymentAttempt(models.Model):
    """ Попытка оплаты """

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='attempts', verbose_name='Попытка оплаты')
    stripe_charge_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID платежа Stripe')
    status = models.CharField(max_length=20, verbose_name='Статус попытки')
    error_message = models.TextField(blank=True, null=True, verbose_name='Сообщение об ошибке') 
    metadata = models.JSONField(default=dict, verbose_name='Метаданные')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        db_table = 'payment_attempt'
        verbose_name = 'Попытка оплаты'
        verbose_name_plural = 'Попытки оплаты'
        ordering = ['-created_at']
        
        def __str__(self):
            return f"Попытка оплаты {self.payment.id}  - {self.status}"
class Refund(models.Model):
    STATUS_CHOICES = (
        ("pending", "Ожидает оплаты"),
        ("processeing", "Обработка"),
        ("succeeded", "Успешно"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменен"),
        ("refunded", "Возвращен"),
    )
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds', verbose_name='Оплата')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма возврата')
    reason = models.TextField(blank=True, verbose_name='Причина возврата')       
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name='Статус возврата')
    stripe_refund_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID возврата Stripe')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_refunds', verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата обработки')
    
    class Meta:
        db_table = 'refund'
        verbose_name = 'Возврат'
        verbose_name_plural = 'Возвраты'
        ordering = ['-created_at']
    

    def __str__(self):
        return f"Возврат {self.id} - ${self.amount} для оплаты {self.payment.id}" 
    @property
    def is_partial(self):
        return self.amount < self.payment.amount
    
    
    def process_refund(self):
        self.status = "succeeded"
        self.processed_at = timezone.now()
        self.save()
    
class WebhookEvent(models.Model):
    PROVIDER_CHOICES = (
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
    )
    
    STATUS_CHOICES = (
        ("pending", "Ожидает оплаты"),
        ("processed", "Обработан"),
        ("failed", "Ошибка"),
        ("ignored", "Игнорирован"),
    )
    
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, verbose_name='Провайдер')
    event_id = models.CharField(max_length=255, unique=True, verbose_name='ID события')
    event_type = models.CharField(max_length=100, verbose_name='Тип события')        
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name='Статус возврата')
    
    data = models.JSONField(verbose_name='Данные события')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата обработки')
    error_message = models.TextField(blank=True, null=True, verbose_name='Сообщение об ошибке') 
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        db_table = 'webhook_event'
        verbose_name = 'Вебхук события'
        verbose_name_plural = 'Вебхук события'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'event_type']),
            models.Index(fields=['status']),
        ]
    

    def __str__(self):
        return f"{self.provider} - {self.event_type} - ({self.status})" 
    
    def mark_as_processed(self):
        self.status = "processed"
        self.processed_at = timezone.now()
        self.save()
        
    def mark_as_failed(self, error_message=None):
        self.status = "failed"
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.save()    
    