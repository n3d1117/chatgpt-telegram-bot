import http.client
import re
import unittest
from unittest.mock import MagicMock, call, patch
from urllib.parse import urlencode

from bot.manager_dashboard import BotDashboard, DashboardError


class BotDashboardTests(unittest.TestCase):
    def setUp(self):
        self.dashboard = BotDashboard('a-unique-dashboard-password')
        self.bot_id = 'managed-bot'
        self.dashboard.bots[self.bot_id] = {
            'name': 'My bot',
            'token': '123456:secret-token-never-rendered',
            'telegram_id': 123456,
            'username': 'my_bot',
        }

    def test_password_must_be_long_enough(self):
        with self.assertRaises(ValueError):
            BotDashboard('short')

    @patch.object(BotDashboard, '_api_request')
    def test_dashboard_login_adds_bot_without_rendering_its_token(self, api_request):
        api_request.return_value = {'id': 42, 'is_bot': True, 'username': 'new_bot'}
        dashboard = BotDashboard('a-unique-dashboard-password', port=0)
        thread = dashboard.start()
        connection = http.client.HTTPConnection('127.0.0.1', dashboard.server.server_address[1])
        try:
            connection.request('GET', '/')
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn(b'Sign in', response.read())

            body = urlencode({'password': dashboard.password})
            connection.request('POST', '/login', body, {'Content-Type': 'application/x-www-form-urlencoded'})
            response = connection.getresponse()
            self.assertEqual(response.status, 303)
            cookie = response.getheader('Set-Cookie').split(';', 1)[0]

            connection.request('GET', '/', headers={'Cookie': cookie})
            response = connection.getresponse()
            page = response.read()
            self.assertEqual(response.status, 200)
            csrf = re.search(rb'name="csrf" value="([^"]+)"', page).group(1).decode('ascii')

            body = urlencode({
                'csrf': csrf,
                'name': 'New bot',
                'token': '42:abcdefghijklmnopqrstuvwxyz',
            })
            connection.request('POST', '/add', body, {'Cookie': cookie, 'Content-Type': 'application/x-www-form-urlencoded'})
            response = connection.getresponse()
            page = response.read()
            self.assertEqual(response.status, 200)
            self.assertIn(b'@new_bot', page)
            self.assertNotIn(b'42:abcdefghijklmnopqrstuvwxyz', page)
        finally:
            connection.close()
            dashboard.server.shutdown()
            dashboard.server.server_close()
            thread.join(timeout=2)

    @patch('bot.manager_dashboard.urllib.request.urlopen')
    def test_api_request_sends_protection_flag_in_multipart_upload(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"ok":true,"result":{"message_id":1}}'
        urlopen.return_value = response

        result = BotDashboard._api_request(
            '123456:abcdefghijklmnopqrstuvwxyz',
            'sendDocument',
            {'chat_id': '-100123', 'protect_content': 'true'},
            {'document': ('file.pdf', b'contents', 'application/pdf')},
        )

        request = urlopen.call_args.args[0]
        self.assertEqual(result, {'message_id': 1})
        self.assertEqual(request.full_url, 'https://api.telegram.org/bot123456:abcdefghijklmnopqrstuvwxyz/sendDocument')
        self.assertIn(b'name="protect_content"\r\n\r\ntrue', request.data)
        self.assertIn(b'name="document"; filename="file.pdf"', request.data)
        self.assertIn(b'contents', request.data)

    @patch.object(BotDashboard, '_api_request')
    def test_add_bot_validates_token_and_keeps_token_out_of_rendered_page(self, api_request):
        api_request.return_value = {'id': 42, 'is_bot': True, 'username': 'new_bot'}
        bot_id = self.dashboard.add_bot('new bot', '42:abcdefghijklmnopqrstuvwxyz')
        self.assertIn(bot_id, self.dashboard.bots)
        self.assertNotIn('42:abcdefghijklmnopqrstuvwxyz', self.dashboard._render({'csrf': 'csrf'}))
        api_request.assert_called_once_with('42:abcdefghijklmnopqrstuvwxyz', 'getMe')

    @patch.object(BotDashboard, '_api_request')
    def test_verify_chat_requires_admin_permissions(self, api_request):
        api_request.side_effect = [
            {'type': 'supergroup', 'title': 'My group'},
            {'status': 'member'},
        ]
        with self.assertRaisesRegex(DashboardError, 'administrator'):
            self.dashboard.verify_chat(self.bot_id, '-100123')

    @patch.object(BotDashboard, '_api_request')
    def test_upload_rechecks_admin_and_applies_protection_flag(self, api_request):
        api_request.side_effect = [
            {'type': 'channel', 'title': 'My channel'},
            {'status': 'administrator', 'can_post_messages': True},
            {'message_id': 77},
        ]
        result, chat = self.dashboard.upload_media(
            self.bot_id, '@my_channel', 'clip.mp4', b'video bytes', True)
        self.assertEqual(result['message_id'], 77)
        self.assertEqual(chat['title'], 'My channel')
        self.assertEqual(api_request.call_args_list, [
            call(self.dashboard.bots[self.bot_id]['token'], 'getChat', {'chat_id': '@my_channel'}),
            call(self.dashboard.bots[self.bot_id]['token'], 'getChatMember', {
                'chat_id': '@my_channel', 'user_id': 123456}),
            call(
                self.dashboard.bots[self.bot_id]['token'],
                'sendVideo',
                {'chat_id': '@my_channel', 'protect_content': 'true'},
                {'video': ('clip.mp4', b'video bytes', 'video/mp4')},
            ),
        ])

    @patch.object(BotDashboard, '_api_request')
    def test_upload_rejects_chat_where_bot_cannot_post(self, api_request):
        api_request.side_effect = [
            {'type': 'channel', 'title': 'Read-only channel'},
            {'status': 'administrator', 'can_post_messages': False},
        ]
        with self.assertRaisesRegex(DashboardError, 'permission to post'):
            self.dashboard.upload_media(self.bot_id, '@channel', 'file.pdf', b'data', False)
        self.assertEqual(api_request.call_count, 2)


if __name__ == '__main__':
    unittest.main()
