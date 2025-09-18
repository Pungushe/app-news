from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Subscription, SubscriptionHistory, PinnedPost

@receiver(post_save, sender=Subscription)
def subscription_post_save(sender, instance, created, **kwargs):
    """ Обработка создания подписки """
    if created:
        SubscriptionHistory.objects.create(
            subscription=instance,
            action='created',
            description=f'Подписка создана для плана {instance.plan.name}',
        )
    else:
        if hasattr(instance, '_previous_status'):
            if instance._previous_status != instance.status:
                SubscriptionHistory.objects.create(
                    subscription=instance,
                    action=instance.status,
                    description=f'Статус подписки изменен с {instance._previous_status} на {instance.status}',
                )

@receiver(pre_delete, sender=Subscription)
def subscription_pre_delete(sender, instance, **kwargs):
    """ Обработка удаления подписки """
    
    try:
        instance.user.planned_post.delete()
    except PinnedPost.DoesNotExist:
        pass

@receiver(post_save, sender=PinnedPost)
def pinned_post_post_save(sender, instance, created, **kwargs):
    """ Обработка сохранения закрепленного поста """
    
    if created:
        if not hasattr(instance.user, 'subscription') or not instance.user.subscription.is_active():
            instance.delete()
            return

    SubscriptionHistory.objects.create(
        subscription=instance.user.subscription,
        action='pinned_post',
        description=f'Пост {instance.post.title} закреплен',
        metadata={
            'post_id': instance.post.id,
            'post_title': instance.post.title,
        }
    )

@receiver(pre_delete, sender=PinnedPost)
def pinned_post_pre_delete(sender, instance, **kwargs):
    """ Обработка удаления закрепленного поста """
    
    
    if hasattr(instance.user, 'subscription'):
        SubscriptionHistory.objects.create(
            subscription=instance.user.subscription,
            action='unpinned_post',
            description=f'Пост {instance.post.title} откреплен',
            metadata={
                'post_id': instance.post.id,
                'post_title': instance.post.title,
            }
    )
