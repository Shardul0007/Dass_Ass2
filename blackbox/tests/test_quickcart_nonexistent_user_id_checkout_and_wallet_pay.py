from __future__ import annotations

import pytest


NONEXISTENT_UID = 99999999


def _iter_dicts(payload):
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        yield item


def _find_order(payload, order_id: int) -> dict | None:
    for row in _iter_dicts(payload):
        oid = row.get("order_id") or row.get("id")
        if oid == order_id:
            return row
        if isinstance(oid, str) and oid.isdigit() and int(oid) == order_id:
            return row
    return None


def test_checkout_rejects_nonexistent_user_id(qc, qc_product):
    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)

    # Best-effort cleanup: even a non-existent user should not have a cart.
    qc.request("DELETE", "/api/v1/cart/clear", headers={"X-User-ID": str(NONEXISTENT_UID)})

    add = qc.request(
        "POST",
        "/api/v1/cart/add",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"product_id": pid, "quantity": 1},
    )
    assert add.status_code in (200, 201), add.text

    resp = qc.request(
        "POST",
        "/api/v1/checkout",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"payment_method": "CARD"},
    )

    assert resp.status_code == 400, (
        f"Expected 400 for checkout with non-existent user; got {resp.status_code} body={resp.text[:200]!r}"
    )


def test_wallet_pay_rejects_nonexistent_user_id(qc):
    resp = qc.request(
        "POST",
        "/api/v1/wallet/pay",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"amount": 1},
    )
    assert resp.status_code == 400, (
        f"Expected 400 for wallet pay with non-existent user; got {resp.status_code} body={resp.text[:200]!r}"
    )


def test_product_review_rejects_nonexistent_user_id(qc, qc_product):
    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)
    resp = qc.request(
        "POST",
        f"/api/v1/products/{pid}/reviews",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"rating": 5, "comment": "ok"},
    )
    assert resp.status_code == 400, (
        f"Expected 400 for posting review with non-existent user; got {resp.status_code} body={resp.text[:200]!r}"
    )


def test_loyalty_redeem_rejects_nonexistent_user_id(qc):
    resp = qc.request(
        "POST",
        "/api/v1/loyalty/redeem",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"amount": 1},
    )
    assert resp.status_code == 400, (
        f"Expected 400 for loyalty redeem with non-existent user; got {resp.status_code} body={resp.text[:200]!r}"
    )


def test_if_checkout_succeeds_order_is_not_attached_to_nonexistent_user(qc, qc_product):
    """If server wrongly allows checkout for non-existent user, ensure it doesn't silently attach to a different user.

    This is diagnostic: it will skip unless checkout unexpectedly returns 200/201.
    """

    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)
    qc.request("DELETE", "/api/v1/cart/clear", headers={"X-User-ID": str(NONEXISTENT_UID)})
    qc.request(
        "POST",
        "/api/v1/cart/add",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"product_id": pid, "quantity": 1},
    )

    chk = qc.request(
        "POST",
        "/api/v1/checkout",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"payment_method": "CARD"},
    )
    if chk.status_code not in (200, 201):
        pytest.skip(f"Checkout did not succeed (status={chk.status_code}); diagnostic not applicable")

    payload = qc.get_json(chk)
    order_id = None
    if isinstance(payload, dict):
        oid = payload.get("order_id") or payload.get("id")
        if isinstance(oid, int):
            order_id = oid
        elif isinstance(oid, str) and oid.isdigit():
            order_id = int(oid)

    if order_id is None:
        pytest.skip(f"Checkout succeeded but did not return an order id. payload_keys={list(payload) if isinstance(payload, dict) else type(payload)}")

    admin = qc.request("GET", "/api/v1/admin/orders")
    if admin.status_code != 200:
        pytest.skip("admin/orders not available")

    row = _find_order(qc.get_json(admin), order_id)
    if not isinstance(row, dict):
        pytest.skip("Could not locate created order in admin/orders")

    # If user_id is present in admin schema, it must not be remapped to some other user.
    uid = row.get("user_id") or row.get("user")
    if uid is None:
        pytest.skip("admin/orders schema did not expose user id")

    assert str(uid) == str(NONEXISTENT_UID), f"Order attached to unexpected user_id={uid!r}"
