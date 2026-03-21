from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import pytest
import requests
from requests import exceptions as req_exc


@dataclass(frozen=True, slots=True)
class QuickCartConfig:
    base_url: str
    roll_number: str


class QuickCartClient:
    def __init__(self, config: QuickCartConfig):
        self._base_url = config.base_url.rstrip("/")
        self._roll_number = config.roll_number
        self._session = requests.Session()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        user_id: int | None = None,
        headers: Dict[str, str] | None = None,
        params: Dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> requests.Response:
        req_headers: Dict[str, str] = {"X-Roll-Number": str(self._roll_number)}
        if user_id is not None:
            req_headers["X-User-ID"] = str(user_id)
        if headers:
            req_headers.update(headers)

        try:
            resp = self._session.request(
                method=method,
                url=self._url(path),
                headers=req_headers,
                params=params,
                json=json,
                timeout=15,
            )
            return resp
        except req_exc.RequestException as exc:
            raise RuntimeError(
                "QuickCart server is not reachable. "
                f"base_url={self._base_url!r} path={path!r}. "
                "Start the Docker container (port 8080) or set QUICKCART_BASE_URL. "
                f"Original error: {exc}"
            ) from exc

    def get_json(self, resp: requests.Response) -> Any:
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"Response was not valid JSON. status={resp.status_code} text={resp.text[:300]!r}") from exc


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


@pytest.fixture(scope="session")
def qc_config() -> QuickCartConfig:
    return QuickCartConfig(
        base_url=_env("QUICKCART_BASE_URL", "http://localhost:8080"),
        roll_number=_env("QUICKCART_ROLL_NUMBER", "1"),
    )


@pytest.fixture(scope="session")
def qc(qc_config: QuickCartConfig) -> QuickCartClient:
    return QuickCartClient(qc_config)


@pytest.fixture(scope="session", autouse=True)
def qc_server_is_up(qc: QuickCartClient):
    """Fail fast with a clear message if the server is not running."""
    try:
        resp = qc.request("GET", "/api/v1/admin/users")
    except RuntimeError as exc:
        pytest.exit(str(exc), returncode=2)

    # If server is up but roll-number/header rules reject, show that too.
    if resp.status_code not in (200, 400, 401):
        pytest.exit(
            f"Unexpected status from /api/v1/admin/users: {resp.status_code} body={resp.text[:300]!r}",
            returncode=2,
        )


def _extract_first_int(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _iter_dicts(value: Any) -> Iterable[dict]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
    elif isinstance(value, dict):
        # common patterns: {"data": [...]} or {"items": [...]}
        for maybe in value.values():
            if isinstance(maybe, list):
                for item in maybe:
                    if isinstance(item, dict):
                        yield item


@pytest.fixture(scope="session")
def qc_user_id(qc: QuickCartClient) -> int:
    """Discover a valid user id via admin endpoint (does not require X-User-ID)."""
    resp = qc.request("GET", "/api/v1/admin/users")
    if resp.status_code != 200:
        raise RuntimeError(
            "QuickCart server is not reachable or admin/users is failing. "
            f"status={resp.status_code} url={resp.url} text={resp.text[:300]!r}"
        )

    payload = qc.get_json(resp)
    for row in _iter_dicts(payload):
        for key in ("user_id", "id"):
            if key in row:
                user_id = _extract_first_int(row.get(key))
                if user_id is not None and user_id > 0:
                    return user_id

    raise RuntimeError(f"Could not discover a user_id from /api/v1/admin/users payload keys={list(payload) if isinstance(payload, dict) else type(payload)}")


@pytest.fixture(scope="session")
def qc_product(qc: QuickCartClient) -> dict:
    """Pick a product from admin/products to avoid guessing ids."""
    resp = qc.request("GET", "/api/v1/admin/products")
    if resp.status_code != 200:
        raise RuntimeError(f"admin/products failed status={resp.status_code} text={resp.text[:300]!r}")

    payload = qc.get_json(resp)
    for row in _iter_dicts(payload):
        # Try to pick something that looks purchasable and has stock.
        stock = row.get("stock")
        active = row.get("active") if "active" in row else row.get("is_active")
        if isinstance(stock, int) and stock > 0:
            if active is None or active is True:
                return row

    # fallback: return first dict
    for row in _iter_dicts(payload):
        return row

    raise RuntimeError("No products found in admin/products")


@pytest.fixture(scope="session")
def qc_coupon(qc: QuickCartClient) -> dict | None:
    """Return a coupon row from admin/coupons if available."""
    resp = qc.request("GET", "/api/v1/admin/coupons")
    if resp.status_code != 200:
        return None
    payload = qc.get_json(resp)
    for row in _iter_dicts(payload):
        if any(k in row for k in ("code", "coupon_code")):
            return row
    return None


@pytest.fixture()
def qc_clean_cart(qc: QuickCartClient, qc_user_id: int):
    """Clear cart before/after a test to reduce test coupling."""
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    yield
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
