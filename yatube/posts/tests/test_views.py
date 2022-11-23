from math import ceil
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from posts.models import Group, Post, Follow, User
from posts.forms import PostForm

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create(
            username='tester_views',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='tester_slug',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def posts_check(self, post):
        """Проверка полей поста."""
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.group, self.post.group)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.image, self.post.image)

    def test_pages_show_correct_context(self):
        """Шаблон index, group, profile сформирован с правильным контекстом."""
        templates_pages_names = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.post.author.username}
            ),
        ]
        for template in templates_pages_names:
            with self.subTest(template=template):
                response = self.authorized_client.get(template)
                self.posts_check(response.context['page_obj'][0])

    def test_groups_profile_show_correct_context(self):
        """Шаблоны group_list, profile сформированs с правильным контекстом."""
        templates_pages_names = [
            (reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}),
                self.group, 'group'),
            (reverse(
                'posts:profile',
                kwargs={'username': self.post.author.username}),
                self.post.author, 'author'),
        ]
        for reverse_name, fixtures, context in templates_pages_names:
            response = self.guest_client.get(reverse_name)
            self.assertEqual(fixtures, response.context[context])

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id})
        )
        self.posts_check(response.context['post'])

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    )
        )
        self.assertIsInstance(response.context.get('form'), PostForm)
        self.assertEqual(response.context.get('form').instance, self.post)

    def test_post_not_get_another_group(self):
        """Созданный пост не попал в другую группу"""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        post_object = response.context['page_obj']
        self.assertNotIn(self.post.group, post_object)

    def test_index_page_cache(self):
        """Список записей в index хранится в кеше."""
        response_first = self.authorized_client.get(
            reverse('posts:index')
        )
        Post.objects.all().delete()
        response_second = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(
            response_first.content,
            response_second.content
        )
        cache.clear()
        self.assertEqual(Post.objects.count(), settings.ZERO_POST)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.POSTS_OF_PAGE: int = 13
        cls.user = User.objects.create_user(username='tester_paginator')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='tests_padginator',
            description='test description',
        )
        posts_list = []
        for post_count in range(cls.POSTS_OF_PAGE):
            posts_list.append(
                Post(
                    text=f'#{post_count} Тестовый текст .',
                    group=cls.group,
                    author=cls.user
                )
            )
        Post.objects.bulk_create(posts_list)
        cls.pages_names = (
            reverse('posts:index'),
            reverse(
                'posts:profile',
                kwargs={'username': cls.user}),
            reverse(
                'posts:group_list',
                kwargs={'slug': cls.group.slug})
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_first_page_contains_ten_posts(self):
        """Тестирование первой страницы паджинатора"""
        for url in self.pages_names:
            response = self.guest_client.get(url)
            self.assertEqual(
                len(response.context['page_obj']),
                settings.COUNT
            )

    def test_last_page_contains_three_records(self):
        '''Паджинатор переносит остальные записи на след стр'''
        page_number = ceil(self.POSTS_OF_PAGE / settings.COUNT)
        for url in self.pages_names:
            response = self.guest_client.get(
                url + '?page=' + str(page_number)
            )
            self.assertEqual(
                len(response.context['page_obj']),
                (self.POSTS_OF_PAGE - (
                    page_number - 1
                ) * settings.COUNT)
            )


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create(
            username='auth_author',
        )
        cls.user_follow = User.objects.create(
            username='auth_follow',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user_author,
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.user_follow)
        self.follow_client = Client()
        self.follow_client.force_login(self.user_author)

    def test_follow(self):
        """Тест подписки"""
        follow_count = Follow.objects.count()
        response = self.follow_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_follow}
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.user_follow}
            )
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user_author, author=self.user_follow
            ).exists()
        )

    def test_posts_on_followers(self):
        """Проверка оотписки."""
        post = Post.objects.create(
            author=self.user_author,
            text='Тестовый текст'
        )
        Follow.objects.create(
            user=self.user_follow,
            author=self.user_author
        )
        response = self.author_client.get(
            reverse('posts:follow_index')
        )
        post_object = response.context['page_obj']
        self.assertIn(post, post_object)

    def test_posts_on_unfollowers(self):
        """Проверка записей у тех кто не подписан на авторов."""
        post = Post.objects.create(
            author=self.user_author,
            text='Тестовый текст'
        )
        response = self.author_client.get(
            reverse('posts:follow_index')
        )
        post_object = response.context['page_obj']
        self.assertNotIn(post, post_object)
