"""Test isolation for the ai-assistant suite.

The chat endpoints read their configuration from the environment. A developer
shell that exports DATABASE_URL and JWT_SECRET_KEY would silently switch
authentication on and break every HTTP test, so the environment is pinned
here. Individual tests re-enable a behaviour explicitly with monkeypatch.
"""

import os

os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("RBAC_ENABLED", "true")
