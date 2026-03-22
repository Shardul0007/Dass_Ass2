from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest


def _as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def _parse_iso_z(dt: str):
    if not isinstance(dt, str) or not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except Exception:
        return None


def _pick_product(admin_products: list[dict]):
    for p in admin_products:
        if not isinstance(p, dict):
            continue
        if p.get("is_active") is not True:
            continue
        pid = p.get("product_id")
        price = p.get("price")
        stock = p.get("stock_quantity")
        if isinstance(pid, int) and isinstance(price, (int, float)) and price > 0 and isinstance(stock, int) and stock >= 150:
            return pid, float(price), stock
    return None


def _make_cart_reach_total(qc, user_id: int, *, pid: int, price: float, stock: int, target_total: float):
    qty = int(math.ceil(target_total / price))
    qty = max(qty, 1)
    if qty > stock:
        pytest.skip("Not enough stock to build required cart total")

    qc.request("DELETE", "/api/v1/cart/clear", user_id=user_id)
    add = qc.request("POST", "/api/v1/cart/add", user_id=user_id, json={"product_id": pid, "quantity": qty})
    assert add.status_code in (200, 201), add.text
    return qty


def _apply_coupon(qc, user_id: int, code: str):
    resp = qc.request("POST", "/api/v1/coupon/apply", user_id=user_id, json={"coupon_code": code})
    return resp


def _extract_discount_payload(qc, resp):
    payload = qc.get_json(resp)
    if not isinstance(payload, dict):
        pytest.skip("coupon/apply payload shape unknown")
    disc = payload.get("discount")
    new_total = payload.get("new_total")
    if not isinstance(disc, (int, float)) or not isinstance(new_total, (int, float)):
        pytest.skip("coupon/apply did not expose numeric discount/new_total")
    return payload, float(disc), float(new_total)


def test_coupon_expired_coupons_are_rejected(qc, qc_user_id):
    now = datetime.now(timezone.utc)

    coupons_resp = qc.request("GET", "/api/v1/admin/coupons")
    if coupons_resp.status_code != 200:
        pytest.skip("admin/coupons not available")
    coupons = [c for c in _as_list(qc.get_json(coupons_resp)) if isinstance(c, dict)]

    expired = None
    for c in coupons:
        exp = _parse_iso_z(c.get("expiry_date"))
        code = c.get("coupon_code")
        if isinstance(code, str) and code and exp is not None and exp < now:
            expired = c
            break
    if expired is None:
        pytest.skip("No expired coupon found")

    code = expired["coupon_code"]
    min_cart = float(expired.get("min_cart_value") or 0)

    prod_resp = qc.request("GET", "/api/v1/admin/products")
    assert prod_resp.status_code == 200
    picked = _pick_product([p for p in _as_list(qc.get_json(prod_resp)) if isinstance(p, dict)])
    if picked is None:
        pytest.skip("No suitable product")
    pid, price, stock = picked

    _make_cart_reach_total(qc, qc_user_id, pid=pid, price=price, stock=stock, target_total=max(min_cart, price))

    resp = _apply_coupon(qc, qc_user_id, code)
    assert resp.status_code == 400, f"Expected expired coupon rejected; got {resp.status_code} body={resp.text[:200]!r}"


def test_coupon_percent_discount_respects_max_cap(qc, qc_user_id):
    now = datetime.now(timezone.utc)

    coupons_resp = qc.request("GET", "/api/v1/admin/coupons")
    if coupons_resp.status_code != 200:
        pytest.skip("admin/coupons not available")
    coupons = [c for c in _as_list(qc.get_json(coupons_resp)) if isinstance(c, dict)]

    percent = None
    for c in coupons:
        code = c.get("coupon_code")
        if not (isinstance(code, str) and code):
            continue
        if str(c.get("discount_type") or "").upper() != "PERCENT":
            continue
        exp = _parse_iso_z(c.get("expiry_date"))
        if exp is not None and exp <= now:
            continue
        if c.get("is_active") is False:
            continue
        if not isinstance(c.get("discount_value"), (int, float)):
            continue
        if not isinstance(c.get("max_discount"), (int, float)):
            continue
        if not isinstance(c.get("min_cart_value"), (int, float)):
            continue
        percent = c
        break

    if percent is None:
        pytest.skip("No suitable percent coupon")

    code = percent["coupon_code"]
    pct = float(percent["discount_value"])
    cap = float(percent["max_discount"])
    min_cart = float(percent["min_cart_value"])

    prod_resp = qc.request("GET", "/api/v1/admin/products")
    assert prod_resp.status_code == 200
    picked = _pick_product([p for p in _as_list(qc.get_json(prod_resp)) if isinstance(p, dict)])
    if picked is None:
        pytest.skip("No suitable product")
    pid, price, stock = picked

    # Ensure raw percent discount would exceed the cap.
    # Need total such that total * pct/100 > cap.
    target_total = max(min_cart, (cap * 100.0 / max(pct, 0.01)) + price)

    _make_cart_reach_total(qc, qc_user_id, pid=pid, price=price, stock=stock, target_total=target_total)

    resp = _apply_coupon(qc, qc_user_id, code)
    assert resp.status_code in (200, 201), resp.text

    _, disc, new_total = _extract_discount_payload(qc, resp)
    original_total = new_total + disc

    expected_disc = min(original_total * (pct / 100.0), cap)

    assert disc <= cap + 0.01
    assert math.isclose(disc, expected_disc, rel_tol=0, abs_tol=0.05)


def test_coupon_fixed_discount_applied_correctly(qc, qc_user_id):
    now = datetime.now(timezone.utc)

    coupons_resp = qc.request("GET", "/api/v1/admin/coupons")
    if coupons_resp.status_code != 200:
        pytest.skip("admin/coupons not available")
    coupons = [c for c in _as_list(qc.get_json(coupons_resp)) if isinstance(c, dict)]

    fixed = None
    for c in coupons:
        code = c.get("coupon_code")
        if not (isinstance(code, str) and code):
            continue
        if str(c.get("discount_type") or "").upper() != "FIXED":
            continue
        exp = _parse_iso_z(c.get("expiry_date"))
        if exp is not None and exp <= now:
            continue
        if c.get("is_active") is False:
            continue
        if not isinstance(c.get("discount_value"), (int, float)):
            continue
        if not isinstance(c.get("max_discount"), (int, float)):
            continue
        if not isinstance(c.get("min_cart_value"), (int, float)):
            continue
        fixed = c
        break

    if fixed is None:
        pytest.skip("No suitable fixed coupon")

    code = fixed["coupon_code"]
    value = float(fixed["discount_value"])
    cap = float(fixed["max_discount"])
    min_cart = float(fixed["min_cart_value"])

    prod_resp = qc.request("GET", "/api/v1/admin/products")
    assert prod_resp.status_code == 200
    picked = _pick_product([p for p in _as_list(qc.get_json(prod_resp)) if isinstance(p, dict)])
    if picked is None:
        pytest.skip("No suitable product")
    pid, price, stock = picked

    _make_cart_reach_total(qc, qc_user_id, pid=pid, price=price, stock=stock, target_total=max(min_cart, price))

    resp = _apply_coupon(qc, qc_user_id, code)
    assert resp.status_code in (200, 201), resp.text

    _, disc, new_total = _extract_discount_payload(qc, resp)
    original_total = new_total + disc

    expected_disc = min(value, cap)
    assert math.isclose(disc, expected_disc, rel_tol=0, abs_tol=0.05)
    assert math.isclose(new_total, original_total - expected_disc, rel_tol=0, abs_tol=0.05)
