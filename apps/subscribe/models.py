from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название плана')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    duration_days = models.PositiveIntegerField(default=30, verbose_name='Срок действия')
    stripe_price_id = models.CharField(max_length=255, verbose_name='ID Stripe плана')
    features = models.JSONField(default=dict, verbose_name='Особенности', help_text='Список возможностей подписки')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        db_table = 'subscription_plans'
        verbose_name = 'План подписки'
        verbose_name_plural = 'Планы подписки'
        ordering = ['price']

    def __str__(self):
        return f'{self.name}' + f'({self.price} руб.)'
    
class Subscription(models.Model):
    STATUS_CHOICES = (
        ("active", "Ативен"),
        ("expired", "Срок истек"),
        ("canceled", "Отменен"),
        ("pending", "Ожидает оплаты"),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Пользователь')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscriptions', null=True, verbose_name='План подписки')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name='Статус подписки')
    start_date = models.DateTimeField(verbose_name='Дата начала подписки')
    end_date = models.DateTimeField(verbose_name='Дата окончания подписки')
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID Stripe подписки')
    auto_renew = models.BooleanField(default=True, verbose_name='Автоматическое продление')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['end_date', 'status']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.plan.name} ({self.status})'
    
    @property
    def is_active(self):
        return (
            self.status == 'active' and
            self.end_date > timezone.now()
        )
    
    @property
    def days_remaining(self):
        if not self.is_active:
            return 0
        
        delta = self.end_date - timezone.now()
        return max(0, delta.days)
    def extend_subscription(self, days=30):
        if self.is_active:
            self.end_date += timedelta(days=days)
        else:
            self.start_date = timezone.now()
            self.end_date = self.start_date + timedelta(days)
            self.status = 'active'
        
        self.save()
        
    def cancel(self):  
        self.status = 'canceled'
        self.auto_renew = False
        self.save()
        
    def expired(self):
        self.status = 'expired'
        self.auto_renew = False
        self.save()
    
    def activate(self):
        self.status = 'active'
        self.start_date = timezone.now()
        self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        self.save()
        

class PinnedPost(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pinned_post', verbose_name='Пользователь')
    post = models.ForeignKey('frontpage.Post', on_delete=models.CASCADE, related_name='pin_info', verbose_name='Пост')
    pinned_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата закрепления')
    
    class Meta:
        db_table = 'pinned_posts'
        verbose_name = 'Закрепленный пост'
        verbose_name_plural = 'Закрепленные посты'
        ordering = ['pinned_at']
        indexes = [
            models.Index(fields=['pinned_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - закрепленный{self.post.title}'
    
    def save(self, *args, **kwargs):
        if not hasattr(self.user, "subscription") or not self.user.subscription.is_active:
            raise ValueError("Пользователь не имеет активной подписки и не может закрепить пост.")
        if self.post.author != self.user:
            raise ValueError("Пользователь может закреплять только свои посты.")
    
        super().save(*args, **kwargs)


class SubscriptionHistory(models.Model):
    ACTION_CHOICES = (
        ("created", "Создан"),
        ("active", "Ативирован"),
        ("renewed", "Продлен"),
        ("canceled", "Отменен"),
        ("expired", "Истек"),
        ("payment_failed", "Ошибка оплаты"),
    )
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='history', verbose_name='Подписка')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Действие')
    description = models.TextField(blank=True, verbose_name='Описание')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Метаданные')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        db_table = 'subscription_history'
        verbose_name = 'История подписки'
        verbose_name_plural = 'История подписок'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.subscription.user.username} - {self.action}'