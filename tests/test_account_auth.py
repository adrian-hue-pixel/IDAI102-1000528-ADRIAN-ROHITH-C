import io
import json
import time
from urllib.error import HTTPError

import pytest

from account_auth import (
    AuthClient,
    AuthConfig,
    AuthError,
    session_from_response,
    validate,
)


@pytest.mark.parametrize('url', ['http://demo.supabase.co', 'https://evil.test', 'https://demo.supabase.co@evil.test', 'https://demo.supabase.co/path'])
def test_rejects_untrusted_provider(url):
    with pytest.raises(AuthError):
        AuthConfig(url, 'sb_publishable_test')


def test_rejects_privileged_keys():
    with pytest.raises(AuthError):
        AuthConfig('https://demo.supabase.co', 'sb_secret_test')
    import base64
    payload = base64.urlsafe_b64encode(json.dumps({'role': 'service_role'}).encode()).decode().rstrip('=')
    with pytest.raises(AuthError):
        AuthConfig('https://demo.supabase.co', 'header.' + payload + '.signature')


def test_validation():
    assert validate(' PERSON@EXAMPLE.COM ', 'a sufficiently long password', signup=True) == 'person@example.com'
    with pytest.raises(AuthError):
        validate('person@example.com', 'short', signup=True)
    with pytest.raises(AuthError):
        validate('not-an-email', 'password')


def test_login_transport_never_puts_password_in_url(monkeypatch):
    requests = []
    def fake(req, timeout):
        requests.append(req)
        return io.BytesIO(b'{"access_token":"test","refresh_token":"refresh","user":{"id":"one"}}')
    monkeypatch.setattr('account_auth.urlopen', fake)
    api = AuthClient(AuthConfig('https://demo.supabase.co', 'sb_publishable_test'))
    data = api.login('p@example.com', 'secret password')
    assert data['user']['id'] == 'one'
    assert 'secret' not in requests[0].full_url
    assert json.loads(requests[0].data)['password'] == 'secret password'
    assert requests[0].get_header('Apikey') == 'sb_publishable_test'


@pytest.mark.parametrize('code', [400, 401, 422, 429, 500])
def test_safe_errors_do_not_echo_provider_or_credentials(monkeypatch, code):
    def fail(*args, **kwargs):
        raise HTTPError('https://demo.supabase.co', code, 'person@example.com already exists', {}, None)
    monkeypatch.setattr('account_auth.urlopen', fail)
    with pytest.raises(AuthError) as error:
        AuthClient(AuthConfig('https://demo.supabase.co', 'sb_publishable_test')).login('p@example.com', 'secret')
    assert 'person@example.com' not in str(error.value)
    assert 'secret' not in str(error.value)


def test_incomplete_session_is_rejected():
    with pytest.raises(AuthError):
        session_from_response({'user': {'id': 'one'}})
    session = session_from_response({'access_token':'a', 'refresh_token':'r', 'expires_in':60, 'user':{'id':'one','email':'p@example.com'}})
    assert session['expires_at'] > time.time()
    assert 'password' not in session


def entry_app():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
    app.session_state['browser_storage_loaded'] = True
    app.session_state['storage_available'] = False
    return app.run()


@pytest.mark.parametrize('route', [
    'views/home.py', 'views/dashboard.py', 'views/purchases.py', 'views/swaps_plan.py',
    'views/impact_lab.py', 'views/garden_badges.py', 'views/month_review.py',
    'views/settings_about.py', 'views/ask_tilly.py', 'views/research.py', 'views/research_feedback.py',
])
def test_workspace_opens_without_account(route):
    app = entry_app().switch_page(route).run()
    assert not app.exception
    assert len(app.sidebar.get('page_link')) >= 8
    assert not any(button.label in ('Continue as guest', 'Log in', 'Create account') for button in app.button)
    assert 'account_session' not in app.session_state
    assert 'guest_access' not in app.session_state
