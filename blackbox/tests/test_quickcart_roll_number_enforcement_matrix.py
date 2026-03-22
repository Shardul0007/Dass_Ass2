from __future__ import annotations

import pytest


def _raw_request(qc, method: str, path: str, *, headers: dict | None = None, json: object | None = None):
    hdrs = headers or {}
    return qc._session.request(method, qc._url(path), headers=hdrs, json=json, timeout=15)


@pytest.mark.parametrize(
    "method,path,needs_user",
    [
        ("GET", "/api/v1/products", True),
        ("GET", "/api/v1/profile", True),
        ("GET", "/api/v1/addresses", True),
        ("GET", "/api/v1/cart", True),
        ("GET", "/api/v1/wallet", True),
        ("GET", "/api/v1/loyalty", True),
        ("GET", "/api/v1/orders", True),
        ("GET", "/api/v1/support/tickets", True),
        # admin
        ("GET", "/api/v1/admin/users", False),
        ("GET", "/api/v1/admin/products", False),
        ("GET", "/api/v1/admin/orders", False),
        ("GET", "/api/v1/admin/coupons", False),
        ("GET", "/api/v1/admin/tickets", False),
        ("GET", "/api/v1/admin/addresses", False),
        ("GET", "/api/v1/admin/carts", False),
    ],
)
def test_missing_roll_number_header_returns_401_everywhere(qc, qc_user_id, method, path, needs_user):
    headers = {}
    if needs_user:
        headers["X-User-ID"] = str(qc_user_id)

    resp = _raw_request(qc, method, path, headers=headers)
    assert resp.status_code == 401, f"{method} {path} expected 401 when missing X-Roll-Number; got {resp.status_code} body={resp.text[:200]!r}"


@pytest.mark.parametrize(
    "method,path,needs_user",
    [
        ("GET", "/api/v1/products", True),
        ("GET", "/api/v1/profile", True),
        ("GET", "/api/v1/addresses", True),
        ("GET", "/api/v1/cart", True),
        ("GET", "/api/v1/wallet", True),
        ("GET", "/api/v1/loyalty", True),
        ("GET", "/api/v1/orders", True),
        ("GET", "/api/v1/support/tickets", True),
        # admin
        ("GET", "/api/v1/admin/users", False),
        ("GET", "/api/v1/admin/products", False),
        ("GET", "/api/v1/admin/orders", False),
        ("GET", "/api/v1/admin/coupons", False),
        ("GET", "/api/v1/admin/tickets", False),
        ("GET", "/api/v1/admin/addresses", False),
        ("GET", "/api/v1/admin/carts", False),
    ],
)
def test_non_integer_roll_number_header_returns_400_everywhere(qc, qc_user_id, method, path, needs_user):
    headers = {"X-Roll-Number": "abc"}
    if needs_user:
        headers["X-User-ID"] = str(qc_user_id)

    resp = _raw_request(qc, method, path, headers=headers)
    assert resp.status_code == 400, f"{method} {path} expected 400 for non-integer X-Roll-Number; got {resp.status_code} body={resp.text[:200]!r}"


@pytest.mark.parametrize(
    "roll_value",
    ["1.0", "1e3", "", "@"],
)
def test_roll_number_must_be_valid_integer_not_float_or_blank(qc, roll_value):
    # Using an admin endpoint to avoid needing X-User-ID.
    resp = _raw_request(qc, "GET", "/api/v1/admin/users", headers={"X-Roll-Number": roll_value})
    if roll_value.strip().isdigit():
        pytest.skip("Not an invalid roll number per this test")
    expected = 401 if roll_value == "" else 400
    assert resp.status_code == expected, f"roll={roll_value!r} expected {expected} got {resp.status_code} body={resp.text[:200]!r}"
