from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import SubscriptionPlan, Subscription, PinnedPost, SubscriptionHistory


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'price', 'duration_days', 'is_active', 
        'subscriptions_count', 'created_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'stripe_price_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'price', 'duration_days', 'stripe_price_id')
        }),
        ('Функции', {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Время', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def subscriptions_count(self, obj):
        """Количество подписок на план"""
        return obj.subscriptions.count()
    subscriptions_count.short_description = 'Подписки'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('subscriptions')


class SubscriptionHistoryInline(admin.TabularInline):
    model = SubscriptionHistory
    extra = 0
    readonly_fields = ('action', 'description', 'metadata', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user_link', 'plan', 'status', 'is_active_display', 
        'days_remaining_display', 'start_date', 'end_date'
    )
    list_filter = ('status', 'plan', 'auto_renew', 'created_at')
    search_fields = ('user__username', 'user__email', 'plan__name')
    readonly_fields = ('created_at', 'updated_at', 'is_active', 'days_remaining')
    raw_id_fields = ('user',)
    inlines = [SubscriptionHistoryInline]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'plan', 'status')
        }),
        ('Даты', {
            'fields': ('start_date', 'end_date', 'auto_renew')
        }),
        ('Stripe', {
            'fields': ('stripe_subscription_id',),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active', 'days_remaining'),
            'classes': ('collapse',)
        }),
        ('Время', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:accounts_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'Пользователь'

    def is_active_display(self, obj):
        """Отображение активности подписки"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Активно</span>')
        else:
            return format_html('<span style="color: red;">✗ Неактивно</span>')
    is_active_display.short_description = 'Активность'

    def days_remaining_display(self, obj):
        """Отображение оставшихся дней"""
        days = obj.days_remaining
        if days > 7:
            color = 'green'
        elif days > 0:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{} дней</span>', 
            color, days
        )
    days_remaining_display.short_description = 'Days Remaining'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'plan')

    actions = ['activate_subscriptions', 'cancel_subscriptions', 'expire_subscriptions']

    def activate_subscriptions(self, request, queryset):
        """Активирует выбранные подписки"""
        count = 0
        for subscription in queryset:
            if subscription.status != 'active':
                subscription.activate()
                count += 1
        
        self.message_user(request, f'{count} подписки активированы.')
    activate_subscriptions.short_description = "Активировать выбранные подписки"

    def cancel_subscriptions(self, request, queryset):
        """Отменяет выбранные подписки"""
        count = 0
        for subscription in queryset:
            if subscription.status == 'active':
                subscription.cancel()
                count += 1
        
        self.message_user(request, f'{count} подписки отменены.')
    cancel_subscriptions.short_description = "Отменить выбранные подписки"

    def expire_subscriptions(self, request, queryset):
        """Помечает подписки как истекшие"""
        count = 0
        for subscription in queryset:
            if subscription.status == 'active':
                subscription.expire()
                count += 1
        
        self.message_user(request, f'{count} подписки истекли.')
    expire_subscriptions.short_description = "Пометить выбранные подписки как истекшие"


@admin.register(PinnedPost)
class PinnedPostAdmin(admin.ModelAdmin):
    list_display = (
        'user_link', 'post_link', 'subscription_status', 'pinned_at'
    )
    list_filter = ('pinned_at',)
    search_fields = ('user__username', 'post__title')
    readonly_fields = ('pinned_at',)
    raw_id_fields = ('user', 'post')

    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse('admin:accounts_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'

    def post_link(self, obj):
        """Ссылка на пост"""
        url = reverse('admin:main_post_change', args=[obj.post.pk])
        return format_html('<a href="{}">{}</a>', url, obj.post.title[:50])
    post_link.short_description = 'Post'

    def subscription_status(self, obj):
        """Статус подписки пользователя"""
        if hasattr(obj.user, 'subscription') and obj.user.subscription.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        else:
            return format_html('<span style="color: red;">✗ Inactive</span>')
    subscription_status.short_description = 'Статус подписки'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'user__subscription', 'post'
        )

    def has_add_permission(self, request):
        """Запрещаем создание через админку"""
        return False


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'subscription_link', 'action', 'description_short', 'created_at'
    )
    list_filter = ('action', 'created_at')
    search_fields = ('subscription__user__username', 'description')
    readonly_fields = ('subscription', 'action', 'description', 'metadata', 'created_at')
    
    def subscription_link(self, obj):
        """Ссылка на подписку"""
        url = reverse('admin:subscribe_subscription_change', args=[obj.subscription.pk])
        return format_html(
            '<a href="{}">{} - {}</a>', 
            url, 
            obj.subscription.user.username,
            obj.subscription.plan.name
        )
    subscription_link.short_description = 'Подписка'

    def description_short(self, obj):
        """Краткое описание"""
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'

    def has_add_permission(self, request):
        """Запрещаем создание через админку"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление"""
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subscription', 'subscription__user')


# Дополнительные настройки админки
admin.site.site_header = "Администрация новостного сайта"
admin.site.site_title = "Админ новостного сайта"
admin.site.index_title = "Добро пожаловать в административную панель новостного сайта"
