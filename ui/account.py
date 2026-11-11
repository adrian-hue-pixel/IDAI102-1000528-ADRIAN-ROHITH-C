"""Account configuration and session lifecycle, separate from browser journal data."""
import os
import time

import streamlit as st

from account_auth import AuthClient, AuthConfig, AuthError, session_from_response


def client():
    try:
        url = os.environ.get('SUPABASE_URL') or st.secrets.get('SUPABASE_URL', '')
        key = os.environ.get('SUPABASE_PUBLISHABLE_KEY') or st.secrets.get('SUPABASE_PUBLISHABLE_KEY', '')
    except (FileNotFoundError, KeyError):
        return None
    if not url or not key:
        return None
    return AuthClient(AuthConfig(str(url), str(key)))


def current_session():
    session = st.session_state.get('account_session')
    if session and session['expires_at'] <= time.time() + 60:
        try:
            api = client()
            if api is None:
                raise AuthError('Account service unavailable.')
            session = session_from_response(api.refresh(session['refresh_token']))
            st.session_state.account_session = session
        except AuthError:
            clear_session()
            return None
    return session


def clear_session():
    # Authentication and optional shared AI context never cross account boundaries.
    for key in list(st.session_state):
        if key in {'account_session', 'tilly_messages', 'tilly_scope', 'tilly_share', 'tilly_consent'} or key.startswith('auth_'):
            del st.session_state[key]


def attempt_allowed():
    now = time.time()
    attempts = [t for t in st.session_state.get('account_attempts', []) if now-t < 300]
    if len(attempts) >= 10:
        raise AuthError('Please wait five minutes before trying again.')
    attempts.append(now)
    st.session_state.account_attempts = attempts
