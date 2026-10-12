"""Settings read from the environment (.env via Compose env_file). Invalid values refuse startup."""

from collections.abc import Mapping
from dataclasses import dataclass

EXAMPLE_PASSWORD = "CHANGE_ME_BEFORE_FIRST_START"
MIN_PASSWORD_LENGTH = 12


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    password: str
    cookie_secure: bool = True


def load_settings(environ: Mapping[str, str]) -> Settings:
    password = environ.get("APP_PASSWORD", "")
    if not password.strip() or password == EXAMPLE_PASSWORD:
        raise ConfigError("APP_PASSWORD must be set to a non-example value")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ConfigError(f"APP_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters")
    secure = environ.get("COOKIE_SECURE", "true").strip().lower()
    if secure not in {"true", "false"}:
        raise ConfigError("COOKIE_SECURE must be true or false")
    return Settings(password=password, cookie_secure=secure == "true")
