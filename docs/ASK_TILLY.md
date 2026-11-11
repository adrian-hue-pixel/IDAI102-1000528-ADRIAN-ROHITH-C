# Ask Tilly

Open Ask Tilly from Tilly's Home card or Impact Lab. The original eight sidebar pages remain unchanged.

## Connect Gemini

Create a dedicated ShopImpact key in [Google AI Studio](https://aistudio.google.com/apikey). Store it server-side in the ignored `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "replace locally with your key"
GEMINI_MODEL = "gemini-3.5-flash"
```

Environment variables with these names also work and take precedence. On Streamlit Community Cloud, configure the same entries through the deployment's Secrets settings. Never put a key in Git, a browser URL, a screenshot or a chat message. Model access depends on your account; change GEMINI_MODEL to an available compatible model if required. Restart the app after changing server secrets.

The adapter follows Google's [generateContent API](https://ai.google.dev/api/generate-content) and [API-key guidance](https://ai.google.dev/gemini-api/docs/api-key). It uses the authentication header and a fixed Google endpoint; no extra runtime dependency is required.

## Data and limitations

Each participant explicitly agrees before sending text to Google. Their question, up to six recent turns and app context are sent. Optional monthly context includes only selected-month counts, category totals and illustrative estimated emissions. Automatic context excludes brands, notes, prices, exact purchase dates, receipts and identifiers. A preview is available before consent. A participant can still put private information in their own typed question; the form does not claim automatic text anonymization.

Conversations live only in the Streamlit session and are never added to the journal or browser persistence. Changing context clears conversation history so opting out of a monthly summary removes it from subsequent requests. Clear conversation does not reset request limits.

The model explains supplied results; it cannot edit the journal or run calculations/tools. It receives explicit distinctions between the illustrative journal, EPA research estimates and mapping sensitivity. Displayed source links are controlled by the app, not the model. Responses are not guaranteed factual or verified sentence by sentence.

Limits: 2,000 question characters, twelve stored messages, bounded answer length, 40-second timeout, 20 requests/session/hour, ten-second session cooldown, and 100 requests/process/hour. Failed requests count. These local guards are not durable account-wide quotas or billing caps: configure limits and monitor usage in Google Cloud/AI Studio before a public deployment. No claim of a completed chatbot accuracy evaluation is made.

Tests use a simulated API response, verify opt-in data minimization, authentication-header placement, safe error messages and missing-key UI. A live reply must also be verified with a real key before declaring the integration connected.
