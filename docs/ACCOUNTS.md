# ShopImpact accounts

Optional email sign-up and login use Supabase Auth. Guests retain the existing full app. The sidebar opens **Log in / Sign up**. New accounts require a password of at least 12 characters and provider-managed email confirmation. Log out revokes the current refresh session and clears local session credentials.

## Deployment

Add these root-level values to ignored `.streamlit/secrets.toml` locally and the deployed app's Streamlit Secrets:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_YOUR-PUBLIC-KEY"
```

Use a publishable or legacy anon key. Never use a service-role or `sb_secret_` key. Set Supabase Authentication's Site URL to `https://shopimpact-app.streamlit.app/account`. Keep email confirmation enabled. The default Supabase mail service restricts delivery to organization members and is for development; configure custom SMTP before opening public signups. The database Data API is unnecessary for this authentication-only integration.

## Current email connection

The ShopImpact deployment uses a dedicated SMTP2GO SMTP user configured in Supabase Authentication → Emails → SMTP Settings. Custom SMTP is enabled with TLS on port 587 at `mail.smtp2go.com`. The sending password stays in Supabase's encrypted SMTP configuration, outside the repository and Streamlit secrets. The sender address is individually verified. Email confirmation remains enabled, and billing stays on the free plans.

The default Supabase restriction to organization-member recipients no longer applies when custom SMTP is configured. SMTP2GO account limits and sender policies still apply. Verify the entire flow by signing up with an address you control, following the confirmation email, and logging in. A successful settings save alone does not prove inbox delivery.

[SMTP2GO setup guide](https://support.smtp2go.com/hc/en-gb/articles/12747932085145-Quick-Start-Guide)

## Data boundaries

Accounts authenticate identity only. Purchase journals, settings and research records remain browser-local and do not sync between devices or isolate themselves by login. A shared browser can expose its local journal to other users. The account page states this explicitly. Authentication is optional and does not claim to protect locally stored guest records.

Passwords are sent over HTTPS to the fixed configured Supabase project using POST bodies. The app does not persist passwords. Access and refresh tokens stay in Streamlit session state, outside journal persistence and AI context. Closing/reloading into a fresh session may require login again. Password forms clear after submission. Provider errors use generic text to reduce account enumeration. Session-level throttling supplements Supabase's own limits and is not an abuse-proof global limit.

References: [Supabase password authentication](https://supabase.com/docs/guides/auth/passwords), [Auth API](https://github.com/supabase/auth), [SMTP deployment requirements](https://supabase.com/docs/guides/auth/auth-smtp).
