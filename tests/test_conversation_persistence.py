from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_on_message_sends_assistant_message(monkeypatch):
    """Ensure that the on_message handler sends (persists) an assistant message.

    This guards against the regression where only the user message and tool steps
    appear in the resumed thread history, but the assistant's answer is missing
    because `msg.send()` (or equivalent persistence call) was never invoked.
    """

    # Import after pytest collects so module-level decoration executes normally.
    from clinical_trials_assistant import chainlit as app_module

    # --- Stub Chainlit runtime objects we interact with ---
    # Provide a simple user_session implementation.
    session_store = {}

    class DummyUserSession:
        def get(self, key):
            return session_store.get(key)

        def set(self, key, value):
            session_store[key] = value

    monkeypatch.setattr(app_module.cl, "user_session", DummyUserSession())

    # Patch cl.Step to a no-op async context manager (Chainlit runtime not active in unit tests)
    class DummyStep:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):  # pragma: no cover - trivial
            return self

        def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
            return False

    monkeypatch.setattr(app_module.cl, "Step", DummyStep)

    # Stub cl.Text to simple container so sidebar creation code doesn't access context
    class DummyText:
        def __init__(self, content: str, name: str):  # pragma: no cover - trivial
            self.content = content
            self.name = name

    monkeypatch.setattr(app_module.cl, "Text", DummyText)

    # Track whether send was awaited.
    send_called = False
    streamed_tokens: list[str] = []

    class DummyMessage:
        def __init__(self, content: str = "", author: str | None = None):
            self.content = content
            self.author = author
            self.metadata = None

        async def stream_token(self, token: str):  # pragma: no cover - trivial
            # Simulate streaming by appending the token to content.
            self.content += token
            streamed_tokens.append(token)

        async def send(self):  # Mark persistence.
            nonlocal send_called
            send_called = True

        async def update(self):  # Some code paths might call update instead.
            # Treat update as persistence too.
            nonlocal send_called
            send_called = True

    monkeypatch.setattr(app_module.cl, "Message", DummyMessage)

    # Dummy ClinicalTrial dataclass instance (structure used for sidebar logic)
    class Trial:
        def __init__(self):
            self.nct_id = "NCT00000000"
            self.official_title = "Dummy Title"
            self.brief_summary = "Summary"

    # Patch ElementSidebar methods to no-ops.
    class DummySidebar:
        @staticmethod
        async def set_elements(elements):  # pragma: no cover - trivial
            return None

        @staticmethod
        async def set_title(title: str):  # pragma: no cover - trivial
            return None

    monkeypatch.setattr(app_module.cl, "ElementSidebar", DummySidebar)

    # Provide a minimal token object mimicking langchain token with content attribute.
    class Token:
        def __init__(self, content: str):
            self.content = content

    # Stub async generator returned by graph.astream.
    async def fake_astream(state, stream_mode=None):  # pragma: no cover - generator
        # Simulate a rerank update (so sidebar creation branch executes).
        yield (
            "updates",
            {
                "rerank": {
                    "retrieved_trials": [Trial()],
                    "top_reranked_results_ids": ["NCT00000000"],
                }
            },
        )
        # Then produce a single answer token.
        yield ("messages", (Token("Hello"), {"langgraph_node": "answer"}))

    # Monkeypatch graph.astream used inside the handler.
    fake_graph = SimpleNamespace(astream=fake_astream)
    monkeypatch.setattr(app_module, "graph", fake_graph)

    # Call the on_message handler with a dummy inbound user message object.
    class InboundMessage:
        def __init__(self, content: str):
            self.content = content

    await app_module.on_message(InboundMessage("Test query about ibuprofen"))

    # BEFORE FIX: This assertion fails (send_called is False) exposing bug.
    # AFTER FIX: It passes once the assistant message is properly persisted.
    assert send_called, (
        "Assistant message was not persisted (msg.send()/update not called)."
    )
    assert streamed_tokens == ["Hello"], (
        "Expected a single streamed token to build assistant content."
    )


@pytest.mark.asyncio
async def test_on_message_sets_metadata_for_resume(monkeypatch):
    """After fix, assistant message should carry metadata for reconstruction.

    This test will FAIL before the implementation adds `msg.metadata` and a call
    to `msg.send()`. It reuses much of the scaffolding from the previous test.
    """
    from clinical_trials_assistant import chainlit as app_module

    session_store = {}

    class DummyUserSession:
        def get(self, key):
            return session_store.get(key)

        def set(self, key, value):
            session_store[key] = value

    monkeypatch.setattr(app_module.cl, "user_session", DummyUserSession())

    class DummyStep:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):  # pragma: no cover - trivial
            return self

        def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
            return False

    monkeypatch.setattr(app_module.cl, "Step", DummyStep)

    class DummyText:
        def __init__(self, content: str, name: str):  # pragma: no cover - trivial
            self.content = content
            self.name = name

    monkeypatch.setattr(app_module.cl, "Text", DummyText)

    stored_message_refs = []

    class DummyMessage:
        def __init__(self, content: str = "", author: str | None = None):
            self.content = content
            self.author = author
            self.metadata = None

        async def stream_token(self, token: str):
            self.content += token

        async def send(self):
            stored_message_refs.append(self)

    monkeypatch.setattr(app_module.cl, "Message", DummyMessage)

    class Trial:
        def __init__(self):
            self.nct_id = "NCT00000000"
            self.official_title = "Dummy Title"
            self.brief_summary = "Summary"

    class DummySidebar:
        @staticmethod
        async def set_elements(elements):
            return None

        @staticmethod
        async def set_title(title: str):
            return None

    monkeypatch.setattr(app_module.cl, "ElementSidebar", DummySidebar)

    class Token:
        def __init__(self, content: str):
            self.content = content

    async def fake_astream(state, stream_mode=None):
        yield (
            "updates",
            {
                "rerank": {
                    "retrieved_trials": [Trial()],
                    "top_reranked_results_ids": ["NCT00000000"],
                }
            },
        )
        yield ("messages", (Token("Hi"), {"langgraph_node": "answer"}))

    monkeypatch.setattr(app_module, "graph", SimpleNamespace(astream=fake_astream))

    class InboundMessage:
        def __init__(self, content: str):
            self.content = content

    await app_module.on_message(InboundMessage("Any query"))

    assert stored_message_refs, "Assistant message not sent/persisted (no send call)."
    msg = stored_message_refs[0]
    assert isinstance(msg.metadata, dict), "Assistant message metadata not set as dict."
    assert "top_reranked_results_ids" in msg.metadata, (
        "Missing reranked IDs in metadata."
    )
    assert "retrieved_trials" in msg.metadata, (
        "Missing retrieved trials info in metadata."
    )
