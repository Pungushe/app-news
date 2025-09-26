from django.db import models
from django.conf import settings


class Comment(models.Model):
    post = models.ForeignKey('frontpage.Post', on_delete=models.CASCADE, related_name='comments', verbose_name='Пост')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments', verbose_name='Автор')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name='Родительский комментарий')
    content = models.TextField(verbose_name='Текст комментария')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        db_table = 'comments'
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
        ]
    def __str__(self):
        return f'Комментарий от {self.author.username} к посту {self.post.title}'
    
    @property
    def replies_count(self):
        return self.replies.filter(is_active=True).count()
    
    @property
    def is_reply(self):
        return self.parent is not None
