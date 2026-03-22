from __future__ import annotations

import pytest


def _paths(product_id: int) -> list[tuple[str, str]]:
    # Only endpoints that should be user-scoped and safe to call with GET.
    return [
        ("GET", "/api/v1/products"),
        ("GET", "/api/v1/profile"),
        ("GET", "/api/v1/addresses"),
        ("GET", "/api/v1/cart"),
        ("GET", "/api/v1/wallet"),
        ("GET", "/api/v1/loyalty"),
        ("GET", "/api/v1/orders"),
        ("GET", "/api/v1/support/tickets"),
        ("GET", f"/api/v1/products/{product_id}/reviews"),
    ]


@pytest.mark.parametrize("bad_user_id", ["-1", "0", "abc"])
def test_user_scoped_endpoints_reject_invalid_x_user_id(qc, qc_product, bad_user_id: str):
    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)

    for method, path in _paths(pid):
        resp = qc.request(method, path, headers={"X-User-ID": bad_user_id})
        assert resp.status_code == 400, (
            f"{method} {path} expected 400 for invalid X-User-ID={bad_user_id!r}; "
            f"got {resp.status_code} body={resp.text[:200]!r}"
        )


def test_user_scoped_endpoints_reject_missing_x_user_id(qc, qc_product):
    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)

    for method, path in _paths(pid):
        resp = qc.request(method, path)
        assert resp.status_code == 400, (
            f"{method} {path} expected 400 when missing X-User-ID; got {resp.status_code} body={resp.text[:200]!r}"
        )


def test_user_scoped_endpoints_reject_nonexistent_positive_x_user_id(qc, qc_product):
    """Spec says non-existent positive user id is still 'invalid' => 400.

    This is expected to expose Bug 19 (observed: 404) and check if other endpoints differ.
    """

    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)
    missing_uid = 99999999

    mismatches: list[str] = []
    for method, path in _paths(pid):
        resp = qc.request(method, path, headers={"X-User-ID": str(missing_uid)})
        if resp.status_code != 400:
            mismatches.append(
                f"{method} {path} -> {resp.status_code} body={resp.text[:200]!r}"
            )

    assert not mismatches, (
        "Expected 400 for non-existent positive X-User-ID on all user-scoped endpoints, but got:\n"
        + "\n".join(mismatches)
    )
