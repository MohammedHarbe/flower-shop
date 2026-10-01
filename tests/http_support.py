"""Real local HTTP requests with an isolated DB and no outgoing test emails."""

import json
import socket
import threading
import time
from contextlib import contextmanager
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import uvicorn
from sqlalchemy.orm import Session

from backend.admin_auth import require_admin_key
from backend.database import get_db
from backend.main import app


def request_json(base, path, payload=None, method=None):
    request = Request(
        base + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


@contextmanager
def order_api(engine):
    def test_db():
        with Session(engine) as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = test_db
    # Authentication itself is covered by the unchanged security tests.
    app.dependency_overrides[require_admin_key] = lambda: None
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    try:
        with patch("backend.routers.orders.send_order_notification") as notification:
            thread.start()
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            if not server.started:
                raise RuntimeError("Test HTTP server did not start")
            yield f"http://127.0.0.1:{port}", notification
    finally:
        server.should_exit = True
        thread.join(timeout=35)
        listener.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        if thread.is_alive():
            raise RuntimeError("Test HTTP server did not stop")
