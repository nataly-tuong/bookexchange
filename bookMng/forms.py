from django import forms
from django.forms import ModelForm
from .models import Book, Comment


class BookForm(ModelForm):
    class Meta:
        model = Book
        fields = [
            'name',
            'web',
            'price',
            'picture',
        ]

# Like BookForm but for comments
# Connects to Comment model
class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
