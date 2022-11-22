from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].empty_label = 'Группа не выбрана'

    class Meta:
        model = Post
        labels = {
            'group': 'Группа', 'text': 'Сообщение',
            'image': 'Изображение'}
        help_texts = {
            'group': 'Выберите группу', 'text': 'Введите ссообщение',
            'image': 'Загрузите изображение'}
        fields = ['group', 'text', 'image']


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        labels = {'text': 'Добавить комментарий'}
        help_texts = {'text': 'Текст комментария'}
