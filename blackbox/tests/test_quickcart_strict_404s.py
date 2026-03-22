import pytest


def test_cart_add_unknown_product_returns_404(qc, qc_user_id, qc_clean_cart):
    resp = qc.request(
        "POST",
        "/api/v1/cart/add",
        user_id=qc_user_id,
        json={"product_id": 99999999, "quantity": 1},
    )
    assert resp.status_code == 404, f"status={resp.status_code} body={resp.text[:200]!r}"


def test_cart_remove_missing_item_returns_404(qc, qc_user_id, qc_clean_cart):
    # Ensure cart is empty
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    resp = qc.request(
        "POST",
        "/api/v1/cart/remove",
        user_id=qc_user_id,
        json={"product_id": 99999999},
    )
    assert resp.status_code == 404, f"status={resp.status_code} body={resp.text[:200]!r}"


def test_delete_nonexistent_address_returns_404_strict(qc, qc_user_id):
    resp = qc.request("DELETE", "/api/v1/addresses/99999999", user_id=qc_user_id)
    assert resp.status_code == 404, f"status={resp.status_code} body={resp.text[:200]!r}"
