# Future
from __future__ import annotations

# Standard libraries
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = "NOTASECRET"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test_db.sqlite",
        "ATOMIC_REQUESTS": True,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = ["tests"]

USE_TZ = True
