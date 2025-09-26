from celery import shared_task
from django.utils import timezone
    
from datetime import timedelta
from .models import Payment, WebhookEvent
from .services import WebhookService


@shared_task
def cleanup_old_payments():
    """ Очистка старых платежей """ 
    cutoff_date = timezone.now() - timedelta(days=90)  # 90 дней
    
    old_payments = Payment.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['failed', 'canceled'])
    delete_payments, _ = old_payments.delete()
    
    return {'delete_payments': delete_payments}

@shared_task
def cleanup_old__webhook_events():
    """ Очистка старых платежей """ 
    cutoff_date = timezone.now() - timedelta(days=90)  # 90 дней
    
    old_events = WebhookEvent.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['processed', 'ignored'])
    delete_events, _ = old_events.delete()
    
    return {'deleted_webhook_events': delete_events}

@shared_task
def retry_failed_webhook_events():  # sourcery skip: use-named-expression
    """ Очистка старых платежей """ 
    retry_cutoff = timezone.now() - timedelta(days=90)  # 90 дней
    
    failed_events = WebhookEvent.objects.filter(
        status='failed',
        created_at__gte=retry_cutoff,
    )[:50]
    
    processed_count = 0
    
    for event in failed_events:
        success = WebhookService.process_stripe_webhook(event.data)   
        
        if success:
            event.mark_as_processed()
            processed_count += 1
        
    return {'processed_events': processed_count}
