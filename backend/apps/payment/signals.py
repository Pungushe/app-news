from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Payment
from .services import PaymentService


@receiver(pre_save, sender=Payment)
def payment_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Payment.objects.get(pk=instance.pk)
            instance._previous.status = instance.status
        except Payment.DoesNotExist:
            instance._previous.status = None

@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_previous_status'):
        if (instance._previous_status in ['pending', 'processing'] and 
            instance.status == 'succeeded'):
            PaymentService.process_successful_payment(instance)
        elif (instance._previous_status in ['pending', 'processing'] and 
            instance.status == 'failed'):
            PaymentService.process_failed_payment(instance)
            