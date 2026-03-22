from __future__ import annotations

import math

import pytest


def _pick_product_with_stock(products: list[dict], *, min_stock: int = 1) -> dict | None:
    for p in products:
        if not isinstance(p, dict):
            continue
        pid = p.get("product_id") or p.get("id")
        stock = p.get("stock")
        if not isinstance(stock, int):
            stock = p.get("stock_quantity")
        active = p.get("active") if "active" in p else p.get("is_active")
        if isinstance(pid, int) and isinstance(stock, int) and stock >= min_stock and (active is None or active is True):
            return p
    return None


def _get_price(p: dict) -> float | None:
    for k in ("price", "unit_price"):
        v = p.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


@pytest.mark.parametrize("idx", [0, 1])
def test_profile_phone_must_be_10_digits_only(qc, qc_user_ids, idx):
    if len(qc_user_ids) <= idx:
        pytest.skip("Not enough users for parametrization")
    uid = qc_user_ids[idx]

    resp = qc.request("PUT", "/api/v1/profile", user_id=uid, json={"name": "Valid Name", "phone": "01234A6789"})
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:200]!r}"


@pytest.mark.parametrize("idx", [0, 1])
def test_support_ticket_subject_message_length_rules(qc, qc_user_ids, idx):
    if len(qc_user_ids) <= idx:
        pytest.skip("Not enough users for parametrization")
    uid = qc_user_ids[idx]

    # subject too short (<5)
    r = qc.request("POST", "/api/v1/support/ticket", user_id=uid, json={"subject": "abcd", "message": "hi"})
    assert r.status_code == 400

    # subject too long (>100)
    r = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=uid,
        json={"subject": "s" * 101, "message": "hello"},
    )
    assert r.status_code == 400

    # message too long (>500)
    r = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=uid,
        json={"subject": "valid subject", "message": "m" * 501},
    )
    assert r.status_code == 400


@pytest.mark.parametrize("idx", [0, 1])
def test_cart_add_rejects_qty_above_stock(qc, qc_user_ids, qc_products, idx):
    if len(qc_user_ids) <= idx:
        pytest.skip("Not enough users for parametrization")
    uid = qc_user_ids[idx]

    p = _pick_product_with_stock(qc_products, min_stock=1)
    if p is None:
        pytest.skip("No product with known stock")

    pid = p.get("product_id") or p.get("id")
    stock = p.get("stock")
    if not isinstance(stock, int):
        stock = p.get("stock_quantity")
    assert isinstance(pid, int) and isinstance(stock, int)

    # Clear cart
    qc.request("DELETE", "/api/v1/cart/clear", user_id=uid)

    resp = qc.request("POST", "/api/v1/cart/add", user_id=uid, json={"product_id": pid, "quantity": stock + 1})
    assert resp.status_code == 400, f"stock={stock} status={resp.status_code} body={resp.text[:200]!r}"


@pytest.mark.parametrize("idx", [0, 1])
def test_checkout_wallet_insufficient_funds_rejected_best_effort(qc, qc_user_ids, qc_products, idx):
    if len(qc_user_ids) <= idx:
        pytest.skip("Not enough users for parametrization")
    uid = qc_user_ids[idx]

    # Read wallet balance
    bal = qc.request("GET", "/api/v1/wallet", user_id=uid)
    assert bal.status_code == 200
    payload = qc.get_json(bal)

    balance = None
    if isinstance(payload, dict):
        for k in ("wallet_balance", "balance", "amount"):
            if isinstance(payload.get(k), (int, float)):
                balance = float(payload[k])
                break

    if balance is None:
        pytest.skip("Wallet response did not expose numeric balance")

    # Pick a product and quantity such that subtotal will exceed balance.
    p = _pick_product_with_stock(qc_products, min_stock=1)
    if p is None:
        pytest.skip("No suitable product")

    pid = p.get("product_id") or p.get("id")
    stock = p.get("stock")
    if not isinstance(stock, int):
        stock = p.get("stock_quantity")
    price = _get_price(p)
    if not isinstance(pid, int) or not isinstance(stock, int) or price is None or price <= 0:
        pytest.skip("Product missing pid/stock/price")

    # Compute qty to exceed current balance, but cap at stock.
    qty = int(math.floor((balance / price))) + 2
    if qty <= 0:
        qty = 1
    if qty > stock:
        pytest.skip("Not enough stock to exceed wallet balance")

    qc.request("DELETE", "/api/v1/cart/clear", user_id=uid)
    add = qc.request("POST", "/api/v1/cart/add", user_id=uid, json={"product_id": pid, "quantity": qty})
    assert add.status_code in (200, 201)

    resp = qc.request("POST", "/api/v1/checkout", user_id=uid, json={"payment_method": "WALLET"})
    # Spec implies insufficient funds should be rejected (400).
    assert resp.status_code == 400, f"balance={balance} price={price} qty={qty} status={resp.status_code} body={resp.text[:200]!r}"


@pytest.mark.parametrize("idx", [0, 1])
def test_address_update_does_not_change_city_or_pincode_best_effort(qc, qc_user_ids, idx):
    if len(qc_user_ids) <= idx:
        pytest.skip("Not enough users for parametrization")
    uid = qc_user_ids[idx]

    # Create
    create = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=uid,
        json={"label": "HOME", "street": "55555 Delta Street", "city": "Delta", "pincode": "555555", "is_default": False},
    )
    assert create.status_code in (200, 201)
    created = qc.get_json(create)

    address = None
    if isinstance(created, dict) and isinstance(created.get("address"), dict):
        address = created["address"]
    elif isinstance(created, dict):
        address = created

    address_id = None
    if isinstance(address, dict) and isinstance(address.get("address_id"), int):
        address_id = address["address_id"]
    if address_id is None:
        pytest.skip("Could not determine address_id")

    # Update attempt includes forbidden fields
    upd = qc.request(
        "PUT",
        f"/api/v1/addresses/{address_id}",
        user_id=uid,
        json={"city": "CHANGED", "pincode": "000000", "street": "55555 Delta Street UPDATED", "is_default": True},
    )
    assert upd.status_code in (200, 201, 400)

    # Read back via GET to confirm city/pincode unchanged (if API supports GET list)
    lst = qc.request("GET", "/api/v1/addresses", user_id=uid)
    assert lst.status_code == 200
    payload = qc.get_json(lst)
    addrs = payload if isinstance(payload, list) else payload.get("addresses") or payload.get("data") or []
    if not isinstance(addrs, list):
        pytest.skip("addresses list shape unknown")

    target = None
    for a in addrs:
        if isinstance(a, dict) and a.get("address_id") == address_id:
            target = a
            break
    if target is None:
        pytest.skip("Could not find address in list")

    assert target.get("city") == "Delta"
    assert target.get("pincode") == "555555"
