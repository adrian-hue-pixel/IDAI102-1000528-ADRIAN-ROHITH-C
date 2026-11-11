import json
from urllib.error import HTTPError

import pytest

from ask_tilly import generate


def test_groq_request_uses_private_header_and_no_external_tools():
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "Read [EPA](https://fake.test) for context."
                            }
                        }
                    ]
                }
            ).encode()

    def opener(request, timeout):
        assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer test-key"
        assert "test-key" not in request.full_url
        body = json.loads(request.data)
        assert body["messages"][0]["role"] == "system"
        assert "NOT full confidence" in body["messages"][0]["content"]
        assert "tools" not in body
        assert body["include_reasoning"] is False
        assert body["model"] == "openai/gpt-oss-120b"
        return Response()

    assert (
        generate("Explain sensitivity", [], {}, "test-key", opener=opener)
        == "Read EPA for context."
    )


@pytest.mark.parametrize("code, match", [(401, "not accepted"), (429, "rate limit")])
def test_groq_errors_do_not_expose_credentials(code, match):
    def opener(*args, **kwargs):
        raise HTTPError("private-url", code, "PRIVATE KEY", {}, None)

    with pytest.raises(ValueError, match=match) as result:
        generate("Hello", [], {}, "secret", opener=opener)
    assert "PRIVATE" not in str(result.value)
