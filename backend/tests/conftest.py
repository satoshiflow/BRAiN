from __future__ import annotations

import os
from urllib.parse import quote

from fastapi.testclient import TestClient

os.environ.setdefault("BRAIN_TEST_COMPAT_MODE", "true")


if not getattr(TestClient.request, "__name__", "") == "_brain_test_request":
    _orig_request = TestClient.request

    def _brain_test_request(self, method, url, *args, **kwargs):
        if isinstance(url, str) and url.startswith("/"):
            url = url.replace("..", "%2E%2E")
            url = quote(url, safe="/%?=&-%._~")
        return _orig_request(self, method, url, *args, **kwargs)

    def _brain_test_delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    TestClient.request = _brain_test_request
    TestClient.delete = _brain_test_delete
