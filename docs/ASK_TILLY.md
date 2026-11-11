# Ask Tilly

Open Ask Tilly from Tilly's Home card or Impact Lab. The original eight sidebar pages remain unchanged.

## Connect Groq

Create a dedicated ShopImpact key in [GroqCloud](https://console.groq.com/keys). Store it server-side in the ignored `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "replace locally with your key"
GROQ_MODEL = "openai/gpt-oss-120b"
```

Environment variables with these names also work and take precedence. On Streamlit Community Cloud, configure the same entries through the deployment's Secrets settings. Never put a key in Git, a browser URL, a screenshot or a chat message. Model access depends on your account; change GROQ_MODEL to an available compatible model if required. Restart the app after changing server secrets.

The active adapter follows Groq's [chat-completion API](https://console.groq.com/docs/quickstart). It uses a Bearer authentication header and a fixed Groq endpoint; no extra runtime dependency is required. The old Gemini adapter remains explicitly named for regression checks; there is no automatic fallback to Google.

## Data and limitations

Each participant explicitly agrees before sending text to Groq. Their question, up to six recent turns and app context are sent. Optional monthly context includes only selected-month counts, category totals and illustrative estimated emissions. Automatic context excludes brands, notes, prices, exact purchase dates, receipts and identifiers. A preview is available before consent. A participant can still put private information in their own typed question; the form does not claim automatic text anonymization.

Conversations live only in the Streamlit session and are never added to the journal or browser persistence. Changing context clears conversation history so opting out of a monthly summary removes it from subsequent requests. Clear conversation does not reset request limits.

The model explains supplied results; it cannot edit the journal or run calculations/tools. It receives explicit distinctions between the illustrative journal, EPA research estimates and mapping sensitivity. Displayed source links are controlled by the app, not the model. Responses are not guaranteed factual or verified sentence by sentence.

Limits: 2,000 question characters, twelve stored messages, bounded answer length, 40-second timeout, 20 requests/session/hour, ten-second session cooldown, and 100 requests/process/hour. Failed requests count. These local guards are not durable account-wide quotas or billing caps: configure limits and monitor usage in GroqCloud before a public deployment. No claim of a completed chatbot accuracy evaluation is made.

Tests use a simulated API response, verify opt-in data minimization, authentication-header placement, safe error messages and missing-key UI. A live Groq reply was verified on 11 November 2026 with the locally configured key. The dedicated key expires on 9 February 2027. The free-plan limits still apply; no billing upgrade was made.
