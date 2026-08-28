"""Bounded threaded HTTP server for SAD's local/private listeners.

This is availability hardening, not a public-internet server. It limits concurrent
request threads and applies a per-connection socket timeout so slow or abusive LAN
clients cannot grow server work without a fixed ceiling.
"""

from __future__ import annotations

from http.server import ThreadingHTTPServer
import threading


DEFAULT_MAX_CONCURRENT_REQUESTS = 64
DEFAULT_CONNECTION_TIMEOUT_SECONDS = 15


class RequestAdmission:
    """Small fail-fast concurrency gate used by the HTTP listener."""

    def __init__(self, limit=DEFAULT_MAX_CONCURRENT_REQUESTS):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("HTTP request concurrency limit must be a positive integer.")
        self.limit = limit
        self._semaphore = threading.BoundedSemaphore(limit)

    def try_enter(self):
        return self._semaphore.acquire(blocking=False)

    def leave(self):
        self._semaphore.release()


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer with bounded admission and slow-client timeout."""

    daemon_threads = True
    request_queue_size = 64

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        *,
        max_concurrent_requests=DEFAULT_MAX_CONCURRENT_REQUESTS,
        connection_timeout=DEFAULT_CONNECTION_TIMEOUT_SECONDS,
        bind_and_activate=True,
    ):
        if not isinstance(connection_timeout, (int, float)) or connection_timeout <= 0:
            raise ValueError("HTTP connection timeout must be positive.")
        self.connection_timeout = float(connection_timeout)
        self.admission = RequestAdmission(max_concurrent_requests)
        super().__init__(server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)

    def process_request(self, request, client_address):
        try:
            request.settimeout(self.connection_timeout)
        except OSError:
            self.shutdown_request(request)
            return
        if not self.admission.try_enter():
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.admission.leave()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.admission.leave()
