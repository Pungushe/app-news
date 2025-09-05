from rest_framework import serializers
from .models import Comment
from apps.frontpage.models import Post


class CommentSerializer(serializers.ModelSerializer):
    """Сериализатор для комментариев"""
    author_info = serializers.SerializerMethodField()
    replies_count = serializers.ReadOnlyField()
    is_reply = serializers.ReadOnlyField()

    class Meta:
        model = Comment
        fields = [
            'id', 'parent', 'author', 'author_info', 'content', 'is_active',
            'created_at', 'updated_at', 'replies_count', 'is_reply']
        read_only_fields = ['author', 'is_active']

    def get_author_info(self, obj):
        return {
            'id': obj.author.id,
            'username': obj.author.username,
            'full_name': obj.author.full_name,
            'avatar': obj.author.avatar.url if obj.author.avatar else None,
        }
    
    
class CommentCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания комментариев"""
    
    class Meta:
        model = Comment
        fields = ['post', 'parent', 'content']

    def validated_post(self, value):
        if not Post.objects.filter(id=value.id, status='published').exists():
            raise serializers.ValidationError('Пост не найден')
        return value
    def validated_parent(self, value):
        if value and value.post != self.initial_data.get("post"):
            raise serializers.ValidationError('Комментарий должен относится к тому же посту')
        return value
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

class CommentUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления комментариев"""
    
    class Meta:
        model = Comment
        fields = ['content']

class CommentDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для комментариев c ответами"""
    replies = serializers.SerializerMethodField()
    class Meta(CommentSerializer.Meta):
        fields = CommentSerializer.Meta.fields + ['replies']
        
    def get_replies(self, obj):
        if obj.parent is None:
            replies = obj.replies.filter(is_active=True).order_by('created_at')
            return CommentSerializer(replies, many=True, context = self.context).data
        return []
    
