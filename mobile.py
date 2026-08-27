"""Launch SAD desktop loopback service and the paired TLS mobile gateway together."""

from __future__ import annotations

import os
from pathlib import Path
import threading

from api import SadApiService, create_server
from auth import AuthService
from failure_dashboard import FailureDashboard
from mobile_access import MobileAccessStore
from mobile_gateway import DEFAULT_MOBILE_PORT, create_mobile_server
from student_progress import ProgressStore


def build_shared_service():
    auth = AuthService()
    access = MobileAccessStore()
    dashboard = FailureDashboard(auth)
    progress = ProgressStore(Path(__file__).with_name("student_progress.json"))
    return SadApiService(auth=auth, dashboard=dashboard, progress=progress, mobile_access=access), access


def main():
    host = os.environ.get("SAD_MOBILE_HOST", "")
    certfile = os.environ.get("SAD_MOBILE_CERT", "")
    keyfile = os.environ.get("SAD_MOBILE_KEY", "")
    port = int(os.environ.get("SAD_MOBILE_PORT", str(DEFAULT_MOBILE_PORT)))

    service, access = build_shared_service()
    desktop = create_server(service=service)
    mobile = create_mobile_server(host, port, certfile, keyfile, service=service, access=access)

    desktop_thread = threading.Thread(target=desktop.serve_forever, daemon=True, name="sad-desktop")
    desktop_thread.start()
    print(f"SAD desktop is ready at http://127.0.0.1:{desktop.server_port}/")
    print(f"SAD Mobile is ready at https://{host}:{mobile.server_port}/")
    print("Generate a one-time phone code from Owner → Mobile Access, then pair the phone.")
    try:
        mobile.serve_forever()
    except KeyboardInterrupt:
        print("\nSAD desktop + mobile stopped.")
    finally:
        mobile.server_close()
        desktop.shutdown()
        desktop.server_close()
        desktop_thread.join(timeout=2)


if __name__ == "__main__":
    main()
