"""Supabase email authentication. No passwords or tokens are persisted locally."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class AuthError(ValueError):
    """A safe message suitable for the account screen."""


@dataclass(frozen=True)
class AuthConfig:
    url: str
    public_key: str

    def __post_init__(self):
        parsed = urlparse(self.url)
        if (parsed.scheme != 'https' or not re.fullmatch(r'[a-z0-9-]+\.supabase\.co', parsed.netloc)
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise AuthError('Account service configuration needs attention.')
        if not self.public_key or self.public_key.startswith('sb_secret_'):
            raise AuthError('Use the Supabase publishable key, never a secret service key.')
        if self.public_key.count('.') == 2:
            try:
                import base64
                payload = self.public_key.split('.')[1]
                claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
                if claims.get('role') != 'anon':
                    raise AuthError('Use the public anon key, never a service-role key.')
            except (ValueError, KeyError, TypeError) as exc:
                raise AuthError('Use a valid Supabase publishable or anon key.') from exc


def validate(email: str, password: str, *, signup=False):
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise AuthError('Enter a valid email address.')
    if not password or len(password) > 128:
        raise AuthError('Enter your password (up to 128 characters).')
    if signup and len(password) < 12:
        raise AuthError('Choose a password with at least 12 characters.')
    return email


class AuthClient:
    def __init__(self, config: AuthConfig):
        self.config = config

    def request(self, path, payload=None, *, token=None, method='POST'):
        headers = {'apikey': self.config.public_key, 'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(self.config.url.rstrip('/') + '/auth/v1/' + path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers=headers, method=method)
        try:
            with urlopen(req, timeout=20) as response:
                body = response.read(1_000_000)
                return json.loads(body) if body else {}
        except HTTPError as exc:
            # Provider messages can reveal whether an email exists. Keep errors generic.
            if exc.code == 429:
                raise AuthError('Too many attempts. Wait a little and try again.') from None
            if exc.code >= 500:
                raise AuthError('The account service is unavailable. Please try again later.') from None
            raise AuthError('Could not complete this request. Check your details and confirm your email, then try again.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise AuthError('Unable to reach the account service. Please try again.') from None

    def signup(self, email, password):
        email = validate(email, password, signup=True)
        return self.request('signup', {'email': email, 'password': password})

    def login(self, email, password):
        email = validate(email, password)
        return self.request('token?grant_type=password', {'email': email, 'password': password})

    def refresh(self, refresh_token):
        return self.request('token?grant_type=refresh_token', {'refresh_token': refresh_token})

    def user(self, token):
        return self.request('user', token=token, method='GET')

    def logout(self, token):
        self.request('logout?scope=local', token=token)


def session_from_response(response):
    user = response.get('user') or {}
    if not response.get('access_token') or not response.get('refresh_token') or not user.get('id'):
        raise AuthError('Sign-in could not be verified. Please try again.')
    return {'access_token': response['access_token'], 'refresh_token': response['refresh_token'],
            'expires_at': time.time() + int(response.get('expires_in', 3600)),
            'user_id': user['id'], 'email': user.get('email', '')}
