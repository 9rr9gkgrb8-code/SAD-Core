import unittest
from datetime import datetime, timedelta, timezone

from mobile_gateway import PairAttemptLimiter, create_mobile_server, mobile_host_allowed, mobile_route_allowed


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 27, 22, 0, tzinfo=timezone.utc)

    def now(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class MobileGatewayTests(unittest.TestCase):
    def test_gateway_rejects_public_wildcard_loopback_and_hostnames(self):
        for host in ("0.0.0.0", "127.0.0.1", "8.8.8.8", "example.com", "::1"):
            self.assertFalse(mobile_host_allowed(host), host)
        for host in ("192.168.1.20", "10.0.0.9", "172.16.4.5", "100.64.0.20"):
            self.assertTrue(mobile_host_allowed(host), host)

    def test_learning_mode_cannot_reach_owner_or_development_routes(self):
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/auth/login"))
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/study/plan"))
        self.assertTrue(mobile_route_allowed("learning", "GET", "/v1/forge/progress"))
        for method, path in (
            ("GET", "/v1/dashboard"),
            ("GET", "/v1/accounts"),
            ("GET", "/v1/students"),
            ("POST", "/v1/mobile/pairings"),
            ("POST", "/v1/jobs/abc/decision"),
        ):
            self.assertFalse(mobile_route_allowed("learning", method, path), path)

    def test_full_role_mode_still_defers_to_normal_rbac(self):
        self.assertTrue(mobile_route_allowed("full_role", "GET", "/v1/dashboard"))
        self.assertTrue(mobile_route_allowed("full_role", "POST", "/v1/mobile/pairings"))
        self.assertFalse(mobile_route_allowed("unknown", "POST", "/v1/auth/login"))

    def test_pairing_attempts_are_rate_limited(self):
        clock = Clock()
        limiter = PairAttemptLimiter(now=clock.now)
        for _ in range(10):
            limiter.require_available("192.168.1.50")
            limiter.failed("192.168.1.50")
        with self.assertRaises(PermissionError):
            limiter.require_available("192.168.1.50")
        clock.advance(minutes=6)
        limiter.require_available("192.168.1.50")

    def test_mobile_server_refuses_to_start_without_tls_material(self):
        with self.assertRaises(ValueError):
            create_mobile_server("192.168.1.20", certfile=None, keyfile=None)


if __name__ == "__main__":
    unittest.main()
