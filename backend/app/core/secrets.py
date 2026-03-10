from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time

import requests

from app.core.config import settings

try:
    from google.cloud import secretmanager
except Exception:  # pragma: no cover
    secretmanager = None

logger = logging.getLogger("secret_resolver")


@dataclass
class _CacheEntry:
    value: str
    expires_at: float


class SecretResolver:
    def __init__(self) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    def get_secret(
        self,
        *,
        logical_name: str,
        inline_value: str | None,
        secret_ref: str | None,
    ) -> str | None:
        inline = _strip_or_none(inline_value)
        provider = settings.secret_provider.strip().upper()
        if provider == "ENV":
            return inline

        ref = _strip_or_none(secret_ref)
        if not ref:
            return inline

        try:
            return self._fetch_with_cache(provider=provider, ref=ref, logical_name=logical_name)
        except Exception as exc:  # noqa: BLE001
            if settings.secret_fail_open:
                logger.warning(
                    "secret fetch failed for %s (%s), falling back to env inline value",
                    logical_name,
                    provider,
                )
                logger.debug("secret fetch error for %s: %s", logical_name, exc)
                return inline
            raise RuntimeError(f"secret fetch failed for {logical_name}: {exc}") from exc

    def _fetch_with_cache(self, *, provider: str, ref: str, logical_name: str) -> str:
        ttl = max(0, settings.secret_cache_ttl_seconds)
        if ttl <= 0:
            return self._fetch(provider=provider, ref=ref, logical_name=logical_name)

        now = time.time()
        with self._lock:
            cached = self._cache.get(ref)
            if cached and cached.expires_at > now:
                return cached.value

        value = self._fetch(provider=provider, ref=ref, logical_name=logical_name)
        with self._lock:
            self._cache[ref] = _CacheEntry(value=value, expires_at=now + ttl)
        return value

    def _fetch(self, *, provider: str, ref: str, logical_name: str) -> str:
        if provider == "VAULT":
            return self._fetch_from_vault(ref=ref, logical_name=logical_name)
        if provider == "GCP":
            return self._fetch_from_gcp(ref=ref)
        raise RuntimeError(f"Unsupported SECRET_PROVIDER: {provider}")

    def _fetch_from_vault(self, *, ref: str, logical_name: str) -> str:
        addr = _strip_or_none(settings.vault_addr)
        token = _strip_or_none(settings.vault_token)
        mount = settings.vault_mount.strip().strip("/")
        kv_version = settings.vault_kv_version
        if not addr or not token:
            raise RuntimeError("VAULT_ADDR/VAULT_TOKEN are required for SECRET_PROVIDER=VAULT")
        if "#" not in ref:
            raise RuntimeError(
                f"Vault secret ref for {logical_name} must be in format '<path>#<field>'"
            )
        path, field = ref.split("#", 1)
        path = path.strip().strip("/")
        field = field.strip()
        if not path or not field:
            raise RuntimeError("Vault secret ref path/field cannot be empty")

        if kv_version == 2:
            url = f"{addr.rstrip('/')}/v1/{mount}/data/{path}"
        else:
            url = f"{addr.rstrip('/')}/v1/{mount}/{path}"

        resp = requests.get(
            url,
            headers={"X-Vault-Token": token},
            timeout=settings.secret_fetch_timeout_seconds,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Vault status={resp.status_code} body={resp.text[:200]}")

        payload = resp.json()
        if kv_version == 2:
            data = (((payload or {}).get("data") or {}).get("data") or {})
        else:
            data = (payload or {}).get("data") or {}
        value = data.get(field)
        if value is None:
            raise RuntimeError(f"Vault field '{field}' not found at path '{path}'")
        value = str(value).strip()
        if not value:
            raise RuntimeError(f"Vault field '{field}' is empty at path '{path}'")
        return value

    def _fetch_from_gcp(self, *, ref: str) -> str:
        if secretmanager is None:
            raise RuntimeError("google-cloud-secret-manager dependency is missing")

        name = ref.strip()
        if not name:
            raise RuntimeError("GCP secret ref cannot be empty")
        if not name.startswith("projects/"):
            project_id = _strip_or_none(settings.gcp_project_id)
            if not project_id:
                raise RuntimeError("GCP_PROJECT_ID is required when secret ref is short name")
            name = f"projects/{project_id}/secrets/{name}/versions/latest"

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("utf-8").strip()
        if not value:
            raise RuntimeError(f"GCP secret payload is empty for {name}")
        return value


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


resolver = SecretResolver()


def get_secret(logical_name: str, inline_value: str | None, secret_ref: str | None) -> str | None:
    return resolver.get_secret(logical_name=logical_name, inline_value=inline_value, secret_ref=secret_ref)
