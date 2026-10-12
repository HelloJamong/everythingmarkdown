"""Settings read from the environment (.env via Compose env_file). Invalid values refuse startup."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

EXAMPLE_PASSWORD = "CHANGE_ME_BEFORE_FIRST_START"
MIN_PASSWORD_LENGTH = 12
MIB = 1024 * 1024


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    password: str
    cookie_secure: bool = True
    # False: no login; each browser gets an anonymous ID and sees only its own jobs.
    auth_enabled: bool = True
    data_dir: Path = Path("/data")
    log_dir: Path = Path("/logs")
    # Retention TTLs in seconds, snapshotted per job. None = keep N (delete after use).
    upload_ttl: int | None = None
    markdown_ttl: int | None = None
    temp_result_ttl: int = 60 * 60
    cleanup_interval: int = 300
    log_max_bytes: int = 10 * MIB
    log_backup_count: int = 10
    # Proposed limits; not env-tunable until measured on real hardware.
    max_file_bytes: int = 25 * MIB
    max_request_bytes: int = 26 * MIB
    max_active_jobs: int = 3
    conversion_workers: int = 1
    conversion_timeout: float = 120.0


def _positive_int(environ: Mapping[str, str], name: str, default: int | None = None) -> int:
    raw = environ.get(name, "").strip()
    if not raw and default is not None:
        return default
    if not raw.isdigit() or int(raw) <= 0:
        raise ConfigError(f"{name} must be a positive integer")
    return int(raw)


def _keep_ttl(environ: Mapping[str, str], prefix: str) -> int | None:
    keep = environ.get(f"{prefix}_KEEP", "N").strip().upper()
    if keep not in {"Y", "N"}:
        raise ConfigError(f"{prefix}_KEEP must be Y or N")
    if keep == "N":
        return None
    return _positive_int(environ, f"{prefix}_RETENTION_DAYS") * 24 * 60 * 60


def _bool(environ: Mapping[str, str], name: str, default: str) -> bool:
    value = environ.get(name, default).strip().lower()
    if value not in {"true", "false"}:
        raise ConfigError(f"{name} must be true or false")
    return value == "true"


def load_settings(environ: Mapping[str, str]) -> Settings:
    auth_enabled = _bool(environ, "AUTH_ENABLED", "true")
    password = environ.get("APP_PASSWORD", "")
    if auth_enabled:
        if not password.strip() or password == EXAMPLE_PASSWORD:
            raise ConfigError("APP_PASSWORD must be set to a non-example value")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ConfigError(f"APP_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters")
    return Settings(
        password=password if auth_enabled else "",
        cookie_secure=_bool(environ, "COOKIE_SECURE", "true"),
        auth_enabled=auth_enabled,
        max_active_jobs=_positive_int(environ, "MAX_ACTIVE_JOBS", 3),
        conversion_workers=_positive_int(environ, "CONVERSION_WORKERS", 1),
        data_dir=Path(environ.get("DATA_DIR", "/data")),
        log_dir=Path(environ.get("LOG_DIR", "/logs")),
        upload_ttl=_keep_ttl(environ, "UPLOAD"),
        markdown_ttl=_keep_ttl(environ, "MARKDOWN"),
        temp_result_ttl=_positive_int(environ, "TEMP_RESULT_TTL_MINUTES", 60) * 60,
        cleanup_interval=_positive_int(environ, "CLEANUP_INTERVAL_SECONDS", 300),
        log_max_bytes=_positive_int(environ, "LOG_MAX_BYTES", 10 * MIB),
        log_backup_count=_positive_int(environ, "LOG_BACKUP_COUNT", 10),
    )
