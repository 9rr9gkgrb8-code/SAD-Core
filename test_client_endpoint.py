import unittest

from client_endpoint import endpoint_profile, validate_client_endpoint


class ClientEndpointTests(unittest.TestCase):
    def test_loopback_http_is_allowed(self):
        self.assertEqual(validate_client_endpoint("http://127.0.0.1:8765"), "http://127.0.0.1:8765")

    def test_remote_https_is_allowed(self):
        self.assertEqual(validate_client_endpoint("https://sad.example.com/"), "https://sad.example.com")

    def test_remote_http_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_client_endpoint("http://sad.example.com")

    def test_embedded_credentials_fail_closed(self):
        with self.assertRaises(ValueError):
            validate_client_endpoint("https://user:pass@sad.example.com")

    def test_profile_builds_api_urls(self):
        profile = endpoint_profile("temporary-cloud", "https://sad.example.com")
        self.assertEqual(profile.api_url("/health"), "https://sad.example.com/health")


if __name__ == "__main__":
    unittest.main()
