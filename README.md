# agent-utils-sdk

Reusable building blocks for message-driven AI agents: NATS messaging, LLM chat, WhatsApp and speech.
The core depends only on `pydantic`; every integration is an optional extra.

## Features

- `agent_utils_sdk.config`: `EnvReader`, a prefix-aware reader for typed environment variables.
- `agent_utils_sdk.logs`: `get_logger` and `configure_logging` helpers.
- `agent_utils_sdk.messaging`: `Envelope`, `SubjectBuilder` and `MessageHandler` (no NATS dependency).
- `agent_utils_sdk.nats`: async `NatsClient` with JetStream and key-value helpers.
- `agent_utils_sdk.llm`: streaming `OpenAIChat` client.
- `agent_utils_sdk.whatsapp`: async WhatsApp Cloud API client and webhook models.
- `agent_utils_sdk.speech`: Google speech-to-text and text-to-speech.

## Installation

The package is not published on PyPI. Install it straight from GitHub:

```bash
pip install "agent-utils-sdk @ git+https://github.com/marcusstinghel/agent-utils-sdk.git"
```

Or from a local checkout, for development:

```bash
git clone https://github.com/marcusstinghel/agent-utils-sdk.git
cd agent-utils-sdk
pip install -e .
```

Optional integrations are installed as extras:

```bash
pip install -e ".[nats]"
pip install -e ".[openai]"
pip install -e ".[whatsapp]"
pip install -e ".[google]"
pip install -e ".[all]"
```

Python 3.11 or newer is required.

## Configuration

Settings objects are plain pydantic models. They only read the environment when you call
`from_env()`; secrets are stored as `SecretStr` and never appear in `repr()`.

| Variable | Used by | Notes |
|---|---|---|
| `NATS_URL` | `NatsSettings` | Required, comma-separated for several servers |
| `NATS_USER`, `NATS_PASSWORD`, `NATS_TOKEN` | `NatsSettings` | Optional credentials |
| `NATS_MAX_RECONNECT`, `NATS_RECONNECT_TIME_WAIT` | `NatsSettings` | Optional, default 60 and 2.0 |
| `NATS_STREAM` | `NatsSettings` | Optional default JetStream stream |
| `OPENAI_API_KEY` | `OpenAISettings` | Required |
| `OPENAI_MODEL`, `OPENAI_BASE_URL` | `OpenAISettings` | Optional, default model `gpt-4o-mini` |
| `WHATSAPP_ACCESS_TOKEN` | `WhatsAppSettings` | Required |
| `WHATSAPP_PHONE_NUMBER_ID` | `WhatsAppSettings` | Required |
| `WHATSAPP_API_VERSION`, `WHATSAPP_BASE_URL` | `WhatsAppSettings` | Optional |
| `GOOGLE_SPEECH_LANGUAGE_CODE`, `GOOGLE_SPEECH_VOICE_NAME` | `GoogleSpeechSettings` | Optional, default `en-US` |
| `GOOGLE_SPEECH_SAMPLE_RATE_HERTZ`, `GOOGLE_SPEECH_CREDENTIALS_FILE` | `GoogleSpeechSettings` | Optional |

Every `from_env` accepts a `prefix` so several instances can live in the same process:

```python
from agent_utils_sdk.nats import NatsSettings

settings = NatsSettings.from_env(prefix="MYAPP_NATS_")  # reads MYAPP_NATS_URL, ...
```

## Usage

Parse a message and build its subject:

```python
from agent_utils_sdk.messaging import MessageHandler, SubjectBuilder

handler = MessageHandler(SubjectBuilder(prefix="acme", fields=("user_id", "event_type")))
envelope = handler.parse(b'{"user_id": "u1", "message_id": "m1", "event_type": "greet"}')
print(handler.to_subject(envelope))  # acme.u1.greet
```

Publish and subscribe with NATS:

```python
import asyncio

from agent_utils_sdk.nats import NatsClient, NatsSettings


async def main() -> None:
    settings = NatsSettings.from_env()
    async with NatsClient(settings) as client:
        async def on_message(msg):
            print(msg.subject, msg.data)

        await client.subscribe("acme.>", cb=on_message)
        await client.publish("acme.u1.greet", {"text": "hello"})
        await asyncio.sleep(1)


asyncio.run(main())
```

Ask an LLM:

```python
import asyncio

from agent_utils_sdk.llm import OpenAIChat, OpenAISettings


async def main() -> None:
    chat = OpenAIChat(OpenAISettings.from_env())
    print(await chat.respond("Say hello", system="Be brief."))


asyncio.run(main())
```

Send a WhatsApp message:

```python
import asyncio

from agent_utils_sdk.whatsapp import WhatsAppClient, WhatsAppSettings


async def main() -> None:
    client = WhatsAppClient(WhatsAppSettings.from_env())
    try:
        await client.send_text("15551234567", "Hello from the SDK")
    finally:
        await client.aclose()


asyncio.run(main())
```

Transcribe and synthesize speech:

```python
import asyncio

from agent_utils_sdk.speech import GoogleSpeech, GoogleSpeechSettings


async def main() -> None:
    speech = GoogleSpeech(GoogleSpeechSettings.from_env())
    mp3 = await speech.text_to_speech("Hello & welcome")
    print(len(mp3), "bytes of MP3")


asyncio.run(main())
```

## Development

```bash
pip install -e ".[dev]"
pytest                    # unit tests, no network required
pytest -m integration     # needs a running NATS server (set NATS_URL)
python -m build
twine check dist/*
```

## License

MIT. See `LICENSE`.
