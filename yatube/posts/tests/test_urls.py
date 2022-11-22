from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()


class PostsEditURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='tester_urls')
        cls.no_author_of_post = User.objects.create_user(
            username='no_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_response_staus_code(self):
        """URL-адрес ответ статуса страниц для
        неавторизированного/авторизированного пользователя."""
        list_of_slug = [
            ('/', HTTPStatus.OK, False),
            (f'/group/{self.group.slug}/', HTTPStatus.OK, False),
            (f'/profile/{self.user.username}/', HTTPStatus.OK, False),
            (f'/posts/{self.post.id}/', HTTPStatus.OK, False),
            ('/create/', HTTPStatus.OK, True),
            (f'/posts/{self.post.id}/edit/', HTTPStatus.OK, True),
            ('/unexisting_page/', HTTPStatus.NOT_FOUND, False),
        ]
        for url, status_code, flag in list_of_slug:
            if flag:
                response = self.authorized_client.get(url)
            else:
                response = self.guest_client.get(url)
            self.assertEqual(response.status_code, status_code)

    def test_redirect_not_authorized(self):
        """шаблоны Edit, create перенаправят анонимного пользователя"""
        templates_pages_names = [
            (reverse(
                'users:login') + '?next=' + reverse(
                    'posts:post_edit', kwargs={'post_id': self.post.id}),
                (reverse('posts:post_edit', kwargs={'post_id': self.post.id})),
             ),
            (reverse('users:login') + '?next=' + reverse('posts:post_create'),
                reverse('posts:post_create'),)
        ]
        for reverse_name, expected_address in templates_pages_names:
            with self.subTest(expected_address=expected_address):
                response = self.guest_client.get(expected_address, follow=True)
                self.assertRedirects(response, reverse_name)

    def test_urls_no_author_redirect_client(self):
        """Шаблон post_edit перенаправит не автора поста
        на страницу post_detail.
        """
        self.authorized_client.force_login(self.no_author_of_post)
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
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

    def test_urls_posts_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = [
            (reverse('posts:index'), 'posts/index.html'),
            (reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}), 'posts/group_list.html'),
            (reverse(
                'posts:profile',
                kwargs={'username': self.user}), 'posts/profile.html'),
            (reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}), 'posts/post_detail.html'),
            (reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}), 'posts/create_post.html'),
            (reverse('posts:post_create'), 'posts/create_post.html')
        ]
        for reverse_name, template in templates_url_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
