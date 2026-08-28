import unittest

from sad_sdk import SadLocalClient, SadSdkError


class SadSdkTests(unittest.TestCase):
    def test_sdk_accepts_only_loopback_core_urls(self):
        SadLocalClient("http://127.0.0.1:8765")
        SadLocalClient("http://localhost:8765")
        with self.assertRaises(ValueError):
            SadLocalClient("http://192.168.1.20:8765")
        with self.assertRaises(ValueError):
            SadLocalClient("https://example.com")
        with self.assertRaises(ValueError):
            SadLocalClient("http://user:pass@127.0.0.1:8765")

    def test_sdk_does_not_confuse_user_and_app_credentials(self):
        user = SadLocalClient(session_token="user-token")
        self.assertEqual(user._authorization(), "Bearer user-token")
        with self.assertRaises(SadSdkError):
            user._authorization(machine=True)

        app = SadLocalClient(client_id="client", client_secret="secret")
        self.assertEqual(app._authorization(machine=True), "SAD-App client.secret")
        with self.assertRaises(SadSdkError):
            app._authorization()


if __name__ == "__main__":
    unittest.main()
