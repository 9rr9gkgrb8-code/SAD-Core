import platform
import unittest

from windows_crypto import dpapi_available, protect_data, unprotect_data


class WindowsCryptoTests(unittest.TestCase):
    def test_availability_matches_platform(self):
        self.assertEqual(dpapi_available(), platform.system() == "Windows")

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_dpapi_round_trip_is_purpose_bound_and_not_plaintext(self):
        secret = b"SAD-DPAPI-secret-round-trip"
        protected = protect_data(secret, purpose="test:round-trip")
        self.assertIsInstance(protected, bytes)
        self.assertNotEqual(protected, secret)
        self.assertNotIn(secret, protected)
        self.assertEqual(unprotect_data(protected, purpose="test:round-trip"), secret)
        with self.assertRaises(OSError):
            unprotect_data(protected, purpose="test:wrong-purpose")

    @unittest.skipUnless(platform.system() == "Windows", "Windows DPAPI test")
    def test_dpapi_detects_tampering(self):
        protected = bytearray(protect_data(b"tamper-target", purpose="test:tamper"))
        protected[len(protected) // 2] ^= 0x01
        with self.assertRaises(OSError):
            unprotect_data(bytes(protected), purpose="test:tamper")

    @unittest.skipIf(platform.system() == "Windows", "non-Windows behavior")
    def test_non_windows_fails_closed(self):
        with self.assertRaises(OSError):
            protect_data(b"secret", purpose="test:non-windows")
        with self.assertRaises(OSError):
            unprotect_data(b"secret", purpose="test:non-windows")


if __name__ == "__main__":
    unittest.main()
