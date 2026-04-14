from __future__ import annotations

import hashlib


def request_hash(*, method: str, path: str, body: str = "") -> str:
    payload = f"{method.upper()}:{path}:{body}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
