import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(
            username='tester'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='test_slug',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый текст',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в базе."""
        post_count = set(Post.objects.values_list('id', flat=True))
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': PostFormTests.user})
        )
        new_post_count = set(Post.objects.values_list('id', flat=True))
        difference_value = new_post_count.difference(post_count)
        self.assertEqual(len(difference_value), 1)
        post = Post.objects.get(
            id=difference_value.pop())
        self.assertEqual(form_data['text'], post.text)
        self.assertEqual(form_data['group'], post.group.id)
        self.assertEqual(form_data['image'], self.uploaded)
        self.assertEqual(self.user, post.author)

    def test_edit_post(self):
        """Валидная форма редактирования изменяет пост в базе данных."""
        form_data = {
            'text': 'Новый редактированный тестовый текст',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        current_post = Post.objects.get(id=self.post.id)
        self.assertEqual(current_post.text, form_data['text'])
        self.assertEqual(current_post.group.id, form_data['group'])
        self.assertEqual(current_post.author, self.post.author)

    def test_comment_only_for_authorized_client(self):
        """Гость не может добавить комент"""
        comments_count = Comment.objects.count()
        comment_form = {
            'text': 'Тестовый текс коментария'
        }
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data=comment_form,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse(
                'posts:add_comment', kwargs={'post_id': self.post.id}
            )
        )

    def test_comment_added_to_post(self):
        """Комментарий появляется на странице поста."""
        comments_count = set(Comment.objects.values_list('id', flat=True))
        comment_form = {
            'text': 'Тестовый текс коментария'
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data=comment_form,
            follow=True
        )
        new_comments_collection = set(
            Comment.objects.values_list('id',
                                        flat=True
                                        )
        )
        new_ids_collection = new_comments_collection.difference(
            comments_count
        )
        self.assertEqual(
            len(new_ids_collection),
            1
        )
        post = Comment.objects.get(
            id=new_ids_collection.pop())
        self.assertEqual(comment_form['text'], post.text)
        self.assertEqual(self.user, post.author)
        self.assertEqual(self.post.id, post.post.id)
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
