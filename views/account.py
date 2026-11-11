"""Optional, managed email/password accounts inside the ShopImpact workspace."""
import streamlit as st

from account_auth import AuthError, session_from_response
from ui.account import attempt_allowed, clear_session, client, current_session
from ui.common import page_header


def render():
    page_header('Your account', 'A familiar place to return to.',
                action_label='Continue to Home', action_page='views/home.py')
    intro, form = st.columns([1, 1.1], gap='large')
    with intro:
        st.markdown('<div class="account-intro"><span class="account-kicker">YOUR NEXT CHAPTER</span>'
                    '<h2>Small choices.<br>A little more personal.</h2>'
                    '<p>One account for your ShopImpact visits.</p></div>', unsafe_allow_html=True)
        st.caption('Your journal currently stays in this browser. Account login does not upload or sync purchase records. On a shared device, other users of this browser can still access its local journal.')
        st.page_link('views/home.py', label='Explore as a guest', icon=':material/arrow_forward:')
    with form, st.container(border=True, key='account-form'):
        try:
            api = client()
            session = current_session()
        except AuthError as exc:
            st.error(str(exc))
            return
        if session:
            st.subheader('Welcome back')
            st.write(session['email'])
            st.success('You are signed in.')
            st.caption('This sign-in lasts for this browser session. Passwords and session tokens are never saved in the purchase journal.')
            if st.button('Log out', type='primary'):
                try:
                    if api:
                        api.logout(session['access_token'])
                except AuthError:
                    st.session_state.account_logout_notice = 'Signed out here. The account service could not confirm token revocation.'
                clear_session()
                st.rerun()
            return
        if st.session_state.get('account_logout_notice'):
            st.info(st.session_state.pop('account_logout_notice'))
        mode = st.radio('Account access', ['Log in', 'Sign up'], horizontal=True,
                        label_visibility='collapsed', key='account_mode')
        st.subheader('Welcome back' if mode == 'Log in' else 'Create your account')
        st.caption('Your next small step starts here.' if mode == 'Log in' else 'Use your email and a strong, unique password.')
        if api is None:
            st.info('Account setup is in progress. You can keep exploring as a guest.')
        with st.form('account_credentials', clear_on_submit=True):
            email = st.text_input('Email', placeholder='you@example.com', max_chars=254)
            password = st.text_input('Password', type='password', max_chars=128,
                                     help='At least 12 characters for a new account.')
            confirmation = st.text_input('Confirm password', type='password', max_chars=128) if mode == 'Sign up' else None
            consent = st.checkbox('I agree to send my email and password securely to ShopImpact’s account provider, Supabase.')
            submitted = st.form_submit_button('Log in' if mode == 'Log in' else 'Create account',
                                             type='primary', use_container_width=True, disabled=api is None)
        if submitted and api:
            try:
                if not consent:
                    raise AuthError('Please agree to the account provider before continuing.')
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
                    st.success('Check your email for a confirmation link, then return here to log in. If you already have an account, use Log in.')
            except AuthError as exc:
                st.error(str(exc))
        st.caption('Email confirmation helps protect your account. You can use ShopImpact without creating one.')


render()
