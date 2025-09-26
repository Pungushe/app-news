from django.core.management.base import BaseCommand
from apps.subscribe.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Создать планы подписки по умолчанию'

    def handle(self, *args, **options):
        # Создаем базовый план подписки
        plan, created = SubscriptionPlan.objects.get_or_create(
            name='Premium ежемесячно',
            defaults={
                'price': 12.00,
                'duration_days': 30,
                'stripe_price_id': 'price_premium_monthly',  # Замените на реальный ID из Stripe
                'features': {
                    'pin_posts': True,
                    'priority_support': True,
                    'analytics': True
                },
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Создан план подписки: {plan.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'План подписки уже существует: {plan.name}')
            )