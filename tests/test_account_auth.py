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


def test_account_ui_login_and_logout_clear_chat(monkeypatch):
    from streamlit.testing.v1 import AppTest

    import ui.account

    class FakeClient:
        def login(self, email, password):
            return {'access_token':'test', 'refresh_token':'test-refresh', 'expires_in':3600,
                    'user':{'id':'test-user','email':email}}

        def logout(self, token):
            assert token == 'test'

    monkeypatch.setattr(ui.account, 'client', lambda: FakeClient())
    from pathlib import Path
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
    at.session_state['browser_storage_loaded'] = True
    at.session_state['storage_available'] = False
    at.run().switch_page('views/account.py').run()
    at.session_state['tilly_messages'] = [{'role':'user','content':'private'}]
    at.text_input[0].set_value('test@example.com')
    at.text_input[1].set_value('test password only')
    next(b for b in at.button if b.label == 'Log in').click().run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert at.session_state['account_session']['user_id'] == 'test-user'
    assert 'tilly_messages' not in at.session_state
    at.switch_page('views/account.py').run()
    next(b for b in at.button if b.label == 'Log out').click().run()
    assert not at.exception
    assert 'account_session' not in at.session_state


def entry_app():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
    app.session_state['browser_storage_loaded'] = True
    app.session_state['storage_available'] = False
    return app.run().switch_page('views/account.py').run()


@pytest.mark.parametrize('route', [
    'views/home.py', 'views/dashboard.py', 'views/purchases.py', 'views/swaps_plan.py',
    'views/impact_lab.py', 'views/garden_badges.py', 'views/month_review.py',
    'views/settings_about.py', 'views/ask_tilly.py', 'views/research.py', 'views/research_feedback.py',
])
def test_every_route_requires_an_explicit_entry_choice(route):
    app = entry_app().switch_page(route).run()
    assert not app.exception
    assert any(button.label == 'Continue as guest' for button in app.button)
    assert any(heading.value == 'Welcome back' for heading in app.subheader)
    assert len(app.sidebar.get('page_link')) == 0
    assert len(app.chat_input) == 0
    assert 'guest_access' not in app.session_state
    assert 'account_session' not in app.session_state


def test_guest_choice_opens_requested_route_and_survives_internal_navigation():
    app = entry_app().switch_page('views/dashboard.py').run()
    app.switch_page('views/account.py').run()
    next(button for button in app.button if button.label == 'Continue as guest').click().run()
    assert not app.exception
    assert app.session_state['guest_access'] is True
    assert any(heading.value == 'Dashboard' for heading in app.title)
    app.switch_page('views/purchases.py').run()
    assert any(heading.value == 'Purchases' for heading in app.title)
    assert len(app.sidebar.get('page_link')) >= 8
    # A fresh visit cannot inherit guest admission from the journal or another session.
    fresh = entry_app()
    assert any(button.label == 'Continue as guest' for button in fresh.button)


def test_expired_session_returns_to_entry_screen(monkeypatch):
    import ui.account

    class ExpiredClient:
        def refresh(self, token):
            raise AuthError('Session expired.')

    monkeypatch.setattr(ui.account, 'client', lambda: ExpiredClient())
    app = entry_app()
    app.session_state['account_session'] = {'expires_at':0, 'refresh_token':'expired'}
    app.switch_page('views/dashboard.py').run()
    assert not app.exception
    assert 'account_session' not in app.session_state
    assert any(button.label == 'Continue as guest' for button in app.button)


def test_unconfirmed_signup_does_not_admit_user(monkeypatch):
    import ui.account

    class SignupClient:
        def signup(self, email, password):
            return {'user': {'id': 'pending'}}

    monkeypatch.setattr(ui.account, 'client', lambda: SignupClient())
    app = entry_app()
    next(r for r in app.radio if r.label == 'Account access').set_value('Sign up').run()
    app.text_input[0].set_value('test@example.com')
    app.text_input[1].set_value('a long test password')
    app.text_input[2].set_value('a long test password')
    next(button for button in app.button if button.label == 'Create account').click().run()
    assert not app.exception
    assert 'account_session' not in app.session_state
    assert 'guest_access' not in app.session_state
    assert len(app.sidebar.get('page_link')) == 0
    assert any('Check your email' in message.value for message in app.success)
