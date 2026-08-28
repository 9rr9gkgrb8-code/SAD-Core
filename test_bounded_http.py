import unittest
from pathlib import Path

from api import create_server
from bounded_http import BoundedThreadingHTTPServer, RequestAdmission


ROOT = Path(__file__).parent


class BoundedHttpTests(unittest.TestCase):
    def test_admission_is_fail_fast_and_recovers(self):
        gate = RequestAdmission(2)
        self.assertTrue(gate.try_enter())
        self.assertTrue(gate.try_enter())
        self.assertFalse(gate.try_enter())
        gate.leave()
        self.assertTrue(gate.try_enter())
        gate.leave()
        gate.leave()

    def test_invalid_limits_fail_closed(self):
        for value in (0, -1, None, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RequestAdmission(value)

    def test_core_listener_uses_bounded_server_and_timeout(self):
        server = create_server("127.0.0.1", 0, service=object())
        try:
            self.assertIsInstance(server, BoundedThreadingHTTPServer)
            self.assertEqual(server.admission.limit, 64)
            self.assertEqual(server.connection_timeout, 15.0)
            self.assertEqual(server.request_queue_size, 64)
        finally:
            server.server_close()

    def test_mobile_listener_has_tighter_admission_limit(self):
        source = (ROOT / "mobile_gateway.py").read_text(encoding="utf-8")
        self.assertIn("BoundedThreadingHTTPServer", source)
        self.assertIn("max_concurrent_requests=32", source)
        self.assertIn("connection_timeout=15", source)
        self.assertNotIn("ThreadingHTTPServer((host, port)", source)


if __name__ == "__main__":
    unittest.main()
