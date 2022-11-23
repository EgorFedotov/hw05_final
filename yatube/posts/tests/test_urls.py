from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='auth'
        )
        cls.no_author_cl = User.objects.create_user(
            username='auth_no_author'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый текст',
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.no_author = Client()
        self.no_author.force_login(self.no_author_cl)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse(
                'posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user}): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}): 'posts/post_detail.html',
            reverse(
                'posts:edit',
                kwargs={'post_id': self.post.id}): 'posts/post_create.html',
            reverse(
                'posts:post_create'): 'posts/post_create.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_url_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_public_pages_guest_client_status_code(self):
        """Страницы, доступные всем пользователям."""
        namespace_url_names = {
            reverse('posts:index'): HTTPStatus.OK,
            '/page404/': HTTPStatus.NOT_FOUND,
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ): HTTPStatus.OK,
            reverse(
                'posts:profile',
                kwargs={'username': self.user}
            ): HTTPStatus.OK,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ): HTTPStatus.OK,
        }
        for url, response_code in namespace_url_names.items():
            with self.subTest(url=url):
                status_code = self.guest_client.get(url).status_code
                self.assertEqual(status_code, response_code)

    def test_private_pages_authorized_client_status_code(self):
        """Страницы, доступные авторизованным пользователям."""
        namespace_url_names = {
            reverse(
                'posts:edit',
                kwargs={'post_id': self.post.id}
            ),
            reverse('posts:post_create'),
            reverse('posts:follow_index')
        }
        for url in namespace_url_names:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_create_list_redirect_guest_client(self):
        """Шаблон create, edit и follow перенаправит анонимного
        пользователя на страницу логина.
        """
        response_list = {
            reverse('posts:post_create'),
            reverse(
                'posts:edit',
                kwargs={'post_id': self.post.id}
            ),
            reverse(
                'posts:follow_index',
            ),
        }
        for url in response_list:
            with self.subTest(url=url):
                response = self.guest_client.get(
                    url,
                    follow=True
                )
                self.assertRedirects(
                    response,
                    reverse('login') + '?next=' + url
                )

    def test_urls_no_author_redirect_client(self):
        """Шаблон edit перенаправит не автора поста
        на страницу post_detail.
        """
        response = self.no_author.get(
            reverse(
                'posts:edit',
                kwargs={'post_id': self.post.id}
            ),
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ))

    def test_error_page_template(self):
        """Страница 404 выдает кастомный шаблон."""
        response = self.authorized_client.get('/page404/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
