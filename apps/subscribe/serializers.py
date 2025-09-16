from rest_framework import serializers
from django.utils import timezone
from .models import PinnedPost, SubscriptionHistory, SubscriptionPlan, Subscription

from apps.frontpage.models import Post


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Сериализатор для планов подписок"""
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'duration_days', 'features', 
                    'is_active', 'created_at'
                ]
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        """Переопределяем метод для преобразования данных"""
        data = super().to_representation(instance)
        
        if not data.get('features'):
            data['features'] = []
        return data

class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки"""
    plan_info = SubscriptionPlanSerializer(source='plan', read_only=True)
    user_info = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'user_info', 'plan_info', 'status', 
            'start_date', 'end_date', 'is_active', 'auto_renew', 
            'days_remaining', 'created_at', 'updated_at'
        ]
        
        read_only_fields = [
            'id', 'user', 'status', 'start_date', 'end_date', 
                'created_at', 'updated_at'
        ]
        
    def get_user_info(self, obj):
        """Возвращает информацию о пользователе"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            "full_name": obj.user.full_name,
            'email': obj.user.email
        }
    
class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписки"""
    
    class Meta:
        model = Subscription
        fields = ['plan']
        
        
    def validate_plan(self, value):
        """Валидация тарифного плана"""
        
        if not value.is_active:
            raise serializers.ValidationError('Выбраннный план неактивен')
        return value
    
    def validate(self, attrs):
        """Общая валидация"""
        
        user = self.context['request'].user
        if hasattr( user, 'subscription') and user.subscription.is_active():
            raise serializers.ValidationError({
                'none_field_errors': ['У пользователя уже есть активная подписка']
            })
        return attrs
    
    def create(self, validated_data):
        """Создание подписки"""
        validated_data = self.context['request'].user
        validated_data['status'] = 'pending'
        validated_data['start_date'] = timezone.now()
        validated_data['end_date'] = timezone.now() 
        return super().create(validated_data)

class PinnedPostSerializer(serializers.ModelSerializer):
    """Сериализатор для закрепленных постов"""
    post_info = serializers.SerializerMethodField()
    
    class Meta:
        model = PinnedPost
        fields = ['id', 'post', 'post_info', 'pinned_at']
        read_only_fields = ['id', 'pinned_at']
        
    def get_post_info(self, obj):
        return {
            'id': obj.post.id,
            'title': obj.post.title,
            'slug': obj.post.slug,
            'content': obj.post.content,
            "image": obj.post.image.url,
            "views_count": obj.post.views_count,
            'created_at': obj.post.created_at,
        }
    
    def validate_post(self, value):
        """Валидация закрепленного поста"""
        
        user = self.context['request'].user
        if value.author != user:
            raise serializers.ValidationError('Вы можете закрепить только свои посты')
        if value.status != 'published':
            raise serializers.ValidationError('Можно закрепить только опубликованные посты')
        
        return value
    def validate(self, attrs):
        """Общая валидация"""
        
        user = self.context['request'].user
        
        if not hasattr( user, 'subscription') or not user.subscription.is_active():
            raise serializers.ValidationError({
                'none_field_errors': ['Активная подписка требует закрепления постов']
            })
        return attrs
    
    def create(self, validated_data):
        validated_data = self.context['request'].user 
        return super().create(validated_data)
    
class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории подписок"""
    class Meta:
        model = SubscriptionHistory
        fields = ['id', 'action', 'description', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']
        
class UserSubscriptionStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса подписок"""
    has_subscription = serializers.BooleanField()
    is_active = serializers.BooleanField()
    subscription = SubscriptionSerializer(allow_null=True)
    pinned_post = PinnedPostSerializer(allow_null=True)
    can_pin_posts = serializers.BooleanField()
    
    def to_representation(self, instance):
        """Ответ с информацией о подписке пользователя"""
        
        user = instance
        has_subscription= hasattr(user, 'subscription')
        subscription= user.subscription if has_subscription else None
        is_active = subscription.is_active if subscription else False
        pinned_post = getattr(user, 'pinned_post', None) if is_active else None
        
        return {
            'has_subscription': has_subscription,
            'is_active': is_active,
            'subscription': SubscriptionSerializer(subscription).data if subscription else None,
            'pinned_post': PinnedPostSerializer(pinned_post).data if pinned_post else None,
            'can_pin_posts': is_active, 
        }
class PinPostSerializer(serializers.Serializer):
    """Сериализатор для закрепления постов"""
    
    post_id = serializers.IntegerField()

    def validate_post_id(self, value):
        """Валидация идентификатора поста"""
        
        try:
            post = Post.objects.get(id=value, status='published')
        except Post.DoesNotExist as e:
            raise serializers.ValidationError("Пост не найден или не опубликован") from e

        user = self.context['request'].user
        if post.author != user:
            raise serializers.ValidationError("Вы можете закрепить только свой пост")

        return value
    def validate(self, attrs):
        """Общая валидация"""
        
        user = self.context['request'].user
        
        if not hasattr( user, 'subscription') or not user.subscription.is_active():
            raise serializers.ValidationError({
                'none_field_errors': ['Активная подписка требует закрепления постов']
            })
        return attrs
    
class UnpinPostSerializer(serializers.Serializer):
    """Сериализатор для открепления постов"""
    
    def validate(self, attrs):
        """Валидация открепления постов"""
        
        user = self.context['request'].user
        
        if not hasattr( user, 'pinned_post'):
            raise serializers.ValidationError({
                'none_field_errors': ['Закрепленный пост не найден']
            })
        return attrs
    
    