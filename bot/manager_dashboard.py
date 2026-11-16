import html
import http.cookies
import http.server
import json
import mimetypes
import os
import re
import secrets
import threading
import time
import urllib.parse
import urllib.error
import urllib.request


MAX_UPLOAD_SIZE = 50 * 1024 * 1024
SESSION_LIFETIME = 8 * 60 * 60
TOKEN_PATTERN = re.compile(r'^\d+:[A-Za-z0-9_-]{20,}$')
ALLOWED_CHAT_TYPES = {'group', 'supergroup', 'channel'}


class DashboardError(Exception):
    pass


class BotDashboard:
    def __init__(self, password, host='127.0.0.1', port=8765):
        if not password or len(password) < 16:
            raise ValueError('BOT_DASHBOARD_PASSWORD must be at least 16 characters')
        self.password = password
        self.host = host
        self.port = int(port)
        self.bots = {}
        self.sessions = {}
        self.lock = threading.RLock()
        self.server = None

    @staticmethod
    def _api_request(token, method, data=None, files=None):
        body = None
        headers = {}
        if files:
            boundary = secrets.token_hex(16)
            parts = []
            for key, value in (data or {}).items():
                parts.extend((
                    '--{}\r\n'.format(boundary).encode('ascii'),
                    'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(key).encode('ascii'),
                    str(value).encode('utf-8'),
                    b'\r\n',
                ))
            for key, (filename, content, mime_type) in files.items():
                safe_filename = os.path.basename(filename.replace('\\', '/'))
                safe_filename = safe_filename.replace('"', '_').replace('\r', '_').replace('\n', '_')
                parts.extend((
                    '--{}\r\n'.format(boundary).encode('ascii'),
                    'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'.format(
                        key, safe_filename).encode('utf-8'),
                    'Content-Type: {}\r\n\r\n'.format(mime_type).encode('ascii'),
                    content,
                    b'\r\n',
                ))
            parts.append('--{}--\r\n'.format(boundary).encode('ascii'))
            body = b''.join(parts)
            headers['Content-Type'] = 'multipart/form-data; boundary={}'.format(boundary)
        else:
            body = urllib.parse.urlencode(data or {}).encode('ascii')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = urllib.request.Request(
            'https://api.telegram.org/bot{}/{}'.format(token, method),
            data=body,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=60 if files else 20) as response:
                result = json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, OSError, ValueError):
            raise DashboardError('Telegram could not be reached. Check the connection and try again.')
        if not isinstance(result, dict) or not result.get('ok'):
            if not isinstance(result, dict):
                raise DashboardError('Telegram returned an invalid response.')
            description = result.get('description', 'Telegram rejected the request.')
            raise DashboardError(str(description)[:250])
        return result.get('result')

    def add_bot(self, name, token):
        name = name.strip()
        token = token.strip()
        if not name or len(name) > 60:
            raise DashboardError('Enter a bot name between 1 and 60 characters.')
        if not TOKEN_PATTERN.fullmatch(token):
            raise DashboardError('That does not look like a Telegram Bot API token.')

        bot_info = self._api_request(token, 'getMe')
        if not bot_info or not bot_info.get('is_bot') or not bot_info.get('id'):
            raise DashboardError('Telegram did not identify this token as a bot.')

        bot_id = secrets.token_urlsafe(12)
        with self.lock:
            self.bots[bot_id] = {
                'name': name,
                'token': token,
                'telegram_id': bot_info['id'],
                'username': bot_info.get('username', ''),
            }
        return bot_id

    def remove_bot(self, bot_id):
        with self.lock:
            if bot_id not in self.bots:
                raise DashboardError('That bot is not registered in this dashboard.')
            del self.bots[bot_id]

    def _bot(self, bot_id):
        with self.lock:
            bot = self.bots.get(bot_id)
            if bot is None:
                raise DashboardError('That bot is not registered in this dashboard.')
            return dict(bot)

    def verify_chat(self, bot_id, chat_id):
        bot = self._bot(bot_id)
        if not chat_id or len(chat_id) > 128:
            raise DashboardError('Enter a numeric chat ID or a public @channel username.')

        chat = self._api_request(bot['token'], 'getChat', {'chat_id': chat_id})
        if not chat or chat.get('type') not in ALLOWED_CHAT_TYPES:
            raise DashboardError('Only groups, supergroups, and channels are supported.')
        member = self._api_request(bot['token'], 'getChatMember', {
            'chat_id': chat_id,
            'user_id': bot['telegram_id'],
        })
        if not member or member.get('status') not in {'administrator', 'creator'}:
            raise DashboardError('Add this bot as an administrator in that chat before continuing.')
        if (chat.get('type') == 'channel' and member.get('status') != 'creator'
                and member.get('can_post_messages') is not True):
            raise DashboardError('This bot does not have permission to post in that channel.')
        return chat

    def upload_media(self, bot_id, chat_id, filename, content, protect_content):
        if not content:
            raise DashboardError('Choose a non-empty media file.')
        if len(content) > MAX_UPLOAD_SIZE:
            raise DashboardError('Files must be 50 MB or smaller.')

        chat = self.verify_chat(bot_id, chat_id)
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        if mime_type in {'image/jpeg', 'image/png'}:
            method = 'sendPhoto'
            field_name = 'photo'
        elif mime_type == 'video/mp4':
            method = 'sendVideo'
            field_name = 'video'
        else:
            method = 'sendDocument'
            field_name = 'document'

        bot = self._bot(bot_id)
        result = self._api_request(
            bot['token'],
            method,
            {
                'chat_id': chat_id,
                'protect_content': 'true' if protect_content else 'false',
            },
            {field_name: (os.path.basename(filename.replace('\\', '/')), content, mime_type)},
        )
        return result, chat

    @staticmethod
    def _escape(value):
        return html.escape(str(value), quote=True)

    def _render(self, session, notice=''):
        with self.lock:
            bots = list(self.bots.items())
        csrf = self._escape(session['csrf'])
        cards = []
        for bot_id, bot in bots:
            safe_id = self._escape(bot_id)
            cards.append(
                '<section><h2>{name}</h2><p>@{username}</p>'
                '<form method="post" action="/verify">'
                '<input type="hidden" name="csrf" value="{csrf}">'
                '<input type="hidden" name="bot_id" value="{bot_id}">'
                '<label>Chat ID or public @channel <input name="chat_id" required maxlength="128"></label>'
                '<button>Check chat access</button></form>'
                '<form method="post" action="/upload" enctype="multipart/form-data">'
                '<input type="hidden" name="csrf" value="{csrf}">'
                '<input type="hidden" name="bot_id" value="{bot_id}">'
                '<label>Chat ID or public @channel <input name="chat_id" required maxlength="128"></label>'
                '<label>Media file <input type="file" name="media" required></label>'
                '<label><input type="checkbox" name="protect_content" value="yes">'
                'Ask Telegram to restrict forwarding and saving this message</label>'
                '<button>Upload media</button></form>'
                '<form method="post" action="/remove">'
                '<input type="hidden" name="csrf" value="{csrf}">'
                '<input type="hidden" name="bot_id" value="{bot_id}">'
                '<button class="remove">Remove bot from this dashboard</button></form></section>'.format(
                    name=self._escape(bot['name']),
                    username=self._escape(bot.get('username') or 'no username'),
                    csrf=csrf,
                    bot_id=safe_id,
                )
            )
        notice_html = '<p class="notice">{}</p>'.format(self._escape(notice)) if notice else ''
        return (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Telegram bot manager</title><style>'
            'body{{font:16px system-ui;max-width:780px;margin:2rem auto;padding:0 1rem;background:#f4f6fa;color:#172033}}'
            'section,main{{background:white;padding:1.2rem;margin:1rem 0;border-radius:12px;box-shadow:0 2px 12px #18243a12}}'
            'label{{display:block;margin:.8rem 0}}input{{max-width:100%;padding:.55rem;border:1px solid #aeb8c8;border-radius:6px}}'
            'button{{padding:.6rem 1rem;margin:.3rem 0;background:#2563eb;color:white;border:0;border-radius:6px;cursor:pointer}}'
            'button.remove{{background:#9f1239}}.notice{{padding:.8rem;background:#e8f4ff;border-radius:8px}}'
            '</style><body><h1>Telegram bot manager</h1>{notice}'
            '<p>Tokens are held in memory only and are discarded when the process stops. '
            'The Bot API cannot create chats or add members.</p>'
            '<main><h2>Add a bot</h2><form method="post" action="/add">'
            '<input type="hidden" name="csrf" value="{csrf}">'
            '<label>Display name <input name="name" required maxlength="60"></label>'
            '<label>BotFather token <input name="token" type="password" required autocomplete="off"></label>'
            '<button>Add bot</button></form></main>{cards}'
            '<form method="post" action="/logout"><input type="hidden" name="csrf" value="{csrf}">'
            '<button>Log out</button></form></body></html>'
        ).format(notice=notice_html, csrf=csrf, cards=''.join(cards))

    def _handler_class(self):
        dashboard = self

        class Handler(http.server.BaseHTTPRequestHandler):
            server_version = 'LocalTelegramManager'

            def log_message(self, _format, *args):
                return

            def _respond(self, status, body, content_type='text/html; charset=utf-8', headers=None):
                data = body.encode('utf-8') if isinstance(body, str) else body
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def _session(self):
                cookie = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
                morsel = cookie.get('manager_session')
                if not morsel:
                    return None
                session_id = morsel.value
                with dashboard.lock:
                    session = dashboard.sessions.get(session_id)
                    if session and session['expires'] > time.time():
                        session['expires'] = time.time() + SESSION_LIFETIME
                        return session_id, session
                    dashboard.sessions.pop(session_id, None)
                return None

            def _login_page(self, message=''):
                alert = '<p>{}</p>'.format(dashboard._escape(message)) if message else ''
                self._respond(
                    200,
                    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                    '<title>Sign in</title><style>body{{font:16px system-ui;max-width:420px;margin:3rem auto;padding:0 1rem}}'
                    'label{{display:block;margin:1rem 0}}input,button{{padding:.7rem;max-width:100%}}</style>'
                    '<h1>Telegram bot manager</h1>{alert}<form method="post" action="/login">'
                    '<label>Dashboard password <input type="password" name="password" required autofocus></label>'
                    '<button>Sign in</button></form>'.format(alert=alert),
                )

            def _body(self):
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    raise DashboardError('Invalid request length.')
                if length <= 0 or length > MAX_UPLOAD_SIZE + 1024 * 1024:
                    raise DashboardError('The request is empty or larger than the 50 MB upload limit.')
                body = self.rfile.read(length)
                content_type = self.headers.get('Content-Type', '')
                if content_type.startswith('multipart/form-data'):
                    from email.message import Message
                    content_header = Message()
                    content_header['content-type'] = content_type
                    if not content_header.get_boundary():
                        raise DashboardError('Invalid form submission.')
                    from email.parser import BytesParser
                    from email.policy import default
                    raw = ('Content-Type: {}\r\nMIME-Version: 1.0\r\n\r\n'.format(content_type)).encode('ascii') + body
                    parsed = BytesParser(policy=default).parsebytes(raw)
                    fields = {}
                    for part in parsed.iter_parts():
                        name = part.get_param('name', header='content-disposition')
                        if not name:
                            continue
                        value = part.get_payload(decode=True) or b''
                        if part.get_filename() is not None:
                            fields[name] = (part.get_filename(), value)
                        else:
                            charset = part.get_content_charset() or 'utf-8'
                            fields[name] = value.decode(charset, errors='replace')
                    return fields
                if content_type.startswith('application/x-www-form-urlencoded'):
                    parsed_fields = urllib.parse.parse_qs(body.decode('utf-8'), keep_blank_values=True)
                    return {key: values[-1] for key, values in parsed_fields.items()}
                raise DashboardError('Unsupported form encoding.')

            def do_GET(self):
                if self.path not in {'/', '/login'}:
                    self._respond(404, 'Not found', 'text/plain; charset=utf-8')
                    return
                session = self._session()
                if not session:
                    self._login_page()
                    return
                self._respond(200, dashboard._render(session[1]))

            def do_POST(self):
                if self.path not in {'/login', '/add', '/remove', '/verify', '/upload', '/logout'}:
                    self._respond(404, 'Not found', 'text/plain; charset=utf-8')
                    return
                try:
                    fields = self._body()
                    if self.path == '/login':
                        if not secrets.compare_digest(str(fields.get('password', '')), dashboard.password):
                            self._login_page('Incorrect password.')
                            return
                        session_id = secrets.token_urlsafe(32)
                        session = {'csrf': secrets.token_urlsafe(24), 'expires': time.time() + SESSION_LIFETIME}
                        with dashboard.lock:
                            dashboard.sessions[session_id] = session
                        self._respond(
                            303, '',
                            headers={'Location': '/', 'Set-Cookie': 'manager_session={}; HttpOnly; SameSite=Strict; Path=/; Max-Age={}'.format(
                                session_id, SESSION_LIFETIME)},
                        )
                        return

                    current = self._session()
                    if not current:
                        self._login_page('Sign in to continue.')
                        return
                    if not secrets.compare_digest(str(fields.get('csrf', '')), current[1]['csrf']):
                        self._respond(403, 'Invalid form token.', 'text/plain; charset=utf-8')
                        return

                    notice = ''
                    if self.path == '/add':
                        dashboard.add_bot(fields.get('name', ''), fields.get('token', ''))
                        notice = 'Bot added. Its token remains in memory only.'
                    elif self.path == '/remove':
                        dashboard.remove_bot(fields.get('bot_id', ''))
                        notice = 'Bot removed from this dashboard.'
                    elif self.path == '/verify':
                        chat = dashboard.verify_chat(fields.get('bot_id', ''), fields.get('chat_id', '').strip())
                        notice = 'Access verified for {} ({})'.format(chat.get('title', 'chat'), chat.get('type', 'chat'))
                    elif self.path == '/upload':
                        media = fields.get('media')
                        if not isinstance(media, tuple):
                            raise DashboardError('Choose a media file.')
                        result, chat = dashboard.upload_media(
                            fields.get('bot_id', ''),
                            fields.get('chat_id', '').strip(),
                            media[0],
                            media[1],
                            fields.get('protect_content') == 'yes',
                        )
                        notice = 'Uploaded to {}. Telegram message ID: {}'.format(
                            chat.get('title', 'chat'), result.get('message_id', 'sent'))
                    elif self.path == '/logout':
                        with dashboard.lock:
                            dashboard.sessions.pop(current[0], None)
                        self._respond(
                            303, '',
                            headers={'Location': '/login', 'Set-Cookie': 'manager_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'},
                        )
                        return
                    self._respond(200, dashboard._render(current[1], notice))
                except DashboardError as error:
                    current = self._session()
                    if current:
                        self._respond(400, dashboard._render(current[1], str(error)))
                    else:
                        self._login_page(str(error))

        return Handler

    def start(self):
        self.server = http.server.ThreadingHTTPServer((self.host, self.port), self._handler_class())
        self.server.daemon_threads = True
        thread = threading.Thread(target=self.server.serve_forever, name='telegram-manager-dashboard', daemon=True)
        thread.start()
        return thread
