from __future__ import annotations

from agent.transports.codex_app_server_session import CodexAppServerSession
from run_agent import AIAgent


class CloseRecorder:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def test_release_clients_closes_codex_app_server_session():
    agent = AIAgent.__new__(AIAgent)
    agent._active_children = []
    agent._active_children_lock = type(
        "Lock",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda self, *args: None},
    )()
    agent.client = None
    codex_session = CloseRecorder()
    agent._codex_session = codex_session

    agent.release_clients()

    assert codex_session.closed == 1
    assert agent._codex_session is None


def test_close_closes_codex_app_server_session():
    agent = AIAgent.__new__(AIAgent)
    agent.session_id = "session"
    agent._active_children = []
    agent._active_children_lock = type(
        "Lock",
        (),
        {"__enter__": lambda self: self, "__exit__": lambda self, *args: None},
    )()
    agent.client = None
    codex_session = CloseRecorder()
    agent._codex_session = codex_session

    agent.close()

    assert codex_session.closed == 1
    assert agent._codex_session is None


class CloseDuringTurnClient:
    def __init__(self, session: CodexAppServerSession) -> None:
        self.session = session

    def request(self, _method, _params, timeout=None):
        self.session._client = None
        return {"turn": {"id": "turn-1"}}

    def stderr_tail(self, _lines):
        return []


class CompletingClient:
    def __init__(self) -> None:
        self.closed = False

    def request(self, _method, _params, timeout=None):
        return {"turn": {"id": "turn-1"}}

    def is_alive(self):
        return True

    def take_server_request(self, timeout=0):
        return None

    def take_notification(self, timeout=0):
        return {
            "method": "turn/completed",
            "params": {"turn": {"status": "completed"}},
        }

    def close(self):
        self.closed = True


class RespawnClient(CompletingClient):
    instances = []

    def __init__(self, **_kwargs) -> None:
        super().__init__()
        self.initialized = 0
        self.requests = []
        RespawnClient.instances.append(self)

    def initialize(self, **_kwargs) -> None:
        self.initialized += 1

    def request(self, method, params, timeout=None):
        self.requests.append((method, params))
        if method == "thread/start":
            return {"thread": {"id": "new-thread"}}
        return super().request(method, params, timeout=timeout)


def test_codex_app_server_turn_handles_client_closed_during_shutdown():
    session = CodexAppServerSession(cwd="/tmp")
    session._thread_id = "thread-1"
    session._client = CloseDuringTurnClient(session)

    result = session.run_turn("hello", turn_timeout=0.05, notification_poll_timeout=0)

    assert result.interrupted is True
    assert result.should_retire is True
    assert result.error == "codex app-server session closed during turn"


def test_codex_app_server_turn_does_not_close_client_on_success():
    session = CodexAppServerSession(cwd="/tmp")
    client = CompletingClient()
    session._thread_id = "thread-1"
    session._client = client

    result = session.run_turn("hello", turn_timeout=0.05, notification_poll_timeout=0)

    assert result.error is None
    assert client.closed is False


def test_close_process_preserving_thread_keeps_logical_context():
    session = CodexAppServerSession(cwd="/tmp")
    client = CompletingClient()
    session._thread_id = "thread-1"
    session._client = client

    session.close_process_preserving_thread()

    assert client.closed is True
    assert session._client is None
    assert session._thread_id == "thread-1"
    assert session._closed is False


def test_next_turn_respawns_client_and_reuses_preserved_thread():
    RespawnClient.instances = []
    session = CodexAppServerSession(cwd="/tmp", client_factory=RespawnClient)
    session._thread_id = "thread-1"
    old_client = RespawnClient()
    session._client = old_client

    session.close_process_preserving_thread()
    result = session.run_turn("continue", turn_timeout=0.05, notification_poll_timeout=0)

    new_client = RespawnClient.instances[-1]
    assert old_client.closed is True
    assert new_client is not old_client
    assert new_client.initialized == 1
    assert ("thread/start", {"cwd": "/tmp"}) not in new_client.requests
    assert new_client.requests[0][0] == "turn/start"
    assert new_client.requests[0][1]["threadId"] == "thread-1"
    assert result.thread_id == "thread-1"
    assert result.error is None
