"""Minimal account access inside the existing ShopImpact shell."""
import streamlit as st

from account_auth import AuthError, session_from_response
from ui.account import attempt_allowed, clear_session, client, current_session


def render():
    with st.container(key='account-access'):
        st.markdown('<p class="account-eyebrow">SHOPIMPACT / YOUR ACCOUNT</p>', unsafe_allow_html=True)
        try:
            api = client()
            session = current_session()
        except AuthError as exc:
            st.error(str(exc))
            return
        with st.container(border=True, key='account-form'):
            if session:
                st.subheader('Welcome back')
                st.caption(session['email'])
                st.success('You are signed in.')
                if st.button('Log out', type='primary', use_container_width=True):
                    try:
                        if api:
                            api.logout(session['access_token'])
                    except AuthError:
                        st.session_state.account_logout_notice = 'Signed out here. The account service could not confirm token revocation.'
                    clear_session()
                    st.rerun()
            else:
                mode = st.radio('Account access', ['Log in', 'Sign up'], horizontal=True,
                                label_visibility='collapsed', key='account_mode')
                st.subheader('Welcome back' if mode == 'Log in' else 'Create your account')
                st.caption('A little awareness. Every day.')
                if api is None:
                    st.info('Account setup is in progress. You can keep exploring as a guest.')
                with st.form('account_credentials', clear_on_submit=True):
                    email = st.text_input('Email', placeholder='you@example.com', max_chars=254)
                    password = st.text_input('Password', type='password', max_chars=128,
                                             help='At least 12 characters for a new account.')
                    confirmation = st.text_input('Confirm password', type='password', max_chars=128) if mode == 'Sign up' else None
                    submitted = st.form_submit_button('Log in' if mode == 'Log in' else 'Create account',
                                                     type='primary', use_container_width=True, disabled=api is None)
                    st.caption('Secure sign-in with Supabase.')
                if submitted and api:
                    try:
                        if mode == 'Sign up' and password != confirmation:
                            raise AuthError('The passwords do not match.')
                        attempt_allowed()
                        with st.spinner('Connecting securely…'):
                            response = api.login(email, password) if mode == 'Log in' else api.signup(email, password)
                        if response.get('access_token'):
                            session = session_from_response(response)
                            clear_session()
                            st.session_state.account_session = session
                            st.rerun()
                        else:
                            st.success('Check your email to confirm your account, then return to log in. Already registered? Use Log in.')
                    except AuthError as exc:
                        st.error(str(exc))
        if st.session_state.get('account_logout_notice'):
            st.info(st.session_state.pop('account_logout_notice'))
        if st.button('Continue to app' if session else 'Continue as guest', type='tertiary', key='account_guest', use_container_width=True):
            st.switch_page('views/home.py')
        st.caption('Your journal stays in this browser.')
        with st.expander('Privacy and storage'):
            st.write('Accounts use Supabase for authentication. Purchase journals are stored in this browser and do not sync or become private by account. Other users of a shared browser can access its local journal.')
            st.caption('Passwords are not saved in your journal. Sign-in tokens stay in this session. Closing or reloading into a fresh session may require logging in again.')


render()
