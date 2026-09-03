import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parent
PRODUCTION_FILES = [path for path in ROOT.glob("*.py") if not path.name.startswith("test_")]


class SecuritySurfaceTests(unittest.TestCase):
    def test_no_dynamic_execution_or_shell_subprocess(self):
        forbidden_calls = {"eval", "exec"}
        for path in PRODUCTION_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls, path.name)
                if isinstance(node, ast.keyword) and node.arg == "shell":
                    self.assertFalse(isinstance(node.value, ast.Constant) and node.value.value is True, path.name)

    def test_process_and_network_modules_are_confined(self):
        process_files = set()
        network_files = set()
        for path in PRODUCTION_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                if any(name == "subprocess" for name in names):
                    process_files.add(path.name)
                if any(name.startswith(("urllib", "http", "socket", "requests")) for name in names):
                    network_files.add(path.name)
        self.assertEqual(process_files, {"app.py", "container_sandbox.py"})
        # Every network-capable production file is explicitly reviewed. bounded_http.py
        # is the fail-fast local/private listener boundary; sad_sdk.py is the Tier 2
        # local integration client; voice_runtime.py is the loopback-only STT/TTS adapter.
        # client_endpoint.py only parses and validates endpoint URLs; it performs no
        # network I/O and fails closed outside loopback HTTP or remote HTTPS.
        self.assertEqual(
            network_files,
            {
                "api.py", "bounded_http.py", "client_endpoint.py", "mobile_gateway.py", "model_adapter.py",
                "sad_clients.py", "sad_sdk.py", "voice_runtime.py",
            },
        )


if __name__ == "__main__":
    unittest.main()
