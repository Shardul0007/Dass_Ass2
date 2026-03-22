from __future__ import annotations

import pytest


NONEXISTENT_UID = 99999999


def test_cart_add_rejects_nonexistent_user_id(qc, qc_product):
    pid = int(qc_product.get("product_id") or qc_product.get("id") or 1)
    resp = qc.request(
        "POST",
        "/api/v1/cart/add",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"product_id": pid, "quantity": 1},
    )
    assert resp.status_code == 400, f"Expected 400 for non-existent user; got {resp.status_code} body={resp.text[:200]!r}"


def test_wallet_add_rejects_nonexistent_user_id(qc):
    resp = qc.request(
        "POST",
        "/api/v1/wallet/add",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"amount": 1},
    )
    assert resp.status_code == 400, f"Expected 400 for non-existent user; got {resp.status_code} body={resp.text[:200]!r}"


def test_loyalty_redeem_rejects_nonexistent_user_id(qc):
    resp = qc.request(
        "POST",
        "/api/v1/loyalty/redeem",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"amount": 1},
    )
    assert resp.status_code == 400, f"Expected 400 for non-existent user; got {resp.status_code} body={resp.text[:200]!r}"


def test_support_ticket_create_rejects_nonexistent_user_id(qc):
    resp = qc.request(
        "POST",
        "/api/v1/support/ticket",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={"subject": "subject-valid", "message": "hello"},
    )
    assert resp.status_code == 400, f"Expected 400 for non-existent user; got {resp.status_code} body={resp.text[:200]!r}"


def test_addresses_create_rejects_nonexistent_user_id(qc):
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        headers={"X-User-ID": str(NONEXISTENT_UID)},
        json={
            "label": "HOME",
            "street": "55555 Ghost Street",
            "city": "GhostCity",
            "pincode": "555555",
            "is_default": False,
        },
    )
    assert resp.status_code == 400, f"Expected 400 for non-existent user; got {resp.status_code} body={resp.text[:200]!r}"
