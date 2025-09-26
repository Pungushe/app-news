from rest_framework import generics, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from django.shortcuts import get_object_or_404

from apps.comments.serializers import CommentSerializer
from .models import Comment
from .serializers import (
    CommentSerializer, 
    CommentCreateSerializer,
    CommentUpdateSerializer,
    CommentDetailSerializer
)

from .permissions import IsAuthorOrReadOnly
from apps.frontpage.models import Post


class CommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['post', 'author', 'parent']
    search_fields = ['content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Comment.objects.filter(is_active=True).select_related(
            'post', 
            'author', 
            'parent'
            )
        
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.filter(is_active=True).select_related('post', 'author')
    serializer_class = CommentDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CommentUpdateSerializer
        return CommentDetailSerializer
    
    def perform_destroy(self, instance):
        """Магкое удаление - помечаем как неактивный """
        instance.is_active = False
        instance.save()

class MyCommentsView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['post', 'author', 'is_active']
    search_fields = ['content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Comment.objects.filter(is_active=True).select_related('post', 'parent')
    
    
@api_view(['GET'])
@permission_classes([permissions.AllowAny])        
def post_comments(request, post_id):
        """Комментарии к определенному посту """
        post = get_object_or_404(Post, id=post_id, status='published')
        
        """ Только основные комментарии """
        comments = Comment.objects.filter(
            post=post, 
            parent=None, 
            is_active=True
        ).select_related('author').prefetch_related(
            'replies__author'
        ).order_by('-created_at')
        
        serializer = CommentSerializer(comments, many=True, context = {'request': request})
        return Response({
            'post': {
                'id': post.id,
                'title': post.title,
                'slug': post.slug,
                },
                'comments': serializer.data,
                'comments_count': post.comments.filter(is_active=True).count()
                
            })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])        
def comment_replies(request, comment_id):
        """Ответы на комментарии """
        parent_comment = get_object_or_404(Comment, id=comment_id, is_active=True)
        
        replies = Comment.objects.filter(
            parent=parent_comment, 
            is_active=True
        ).select_related('author').order_by('-created_at')
        
        serializer = CommentSerializer(replies, many=True, context = {'request': request})
        return Response({
            'parent_comment': CommentSerializer(parent_comment, context = {'request': request}).data,
            'replies': serializer.data,
            'replies_count': replies.count()
        })
