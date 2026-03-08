"""
CyberBridge - Server Entry Point
Launches the dashboard UI which also starts the session beacon listener.
"""

import os
import sys
import logging

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ─── Path setup ───────────────────────────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, _ROOT)

from server.ui.dashboard import Dashboard


def main():
    app = Dashboard()
    app.run()


if __name__ == "__main__":
    main()
