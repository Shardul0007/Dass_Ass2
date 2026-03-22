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


def _get_product_id(p: dict) -> int | None:
    pid = p.get("product_id") or p.get("id")
    return pid if isinstance(pid, int) else None


def _get_price(p: dict) -> float | None:
    v = p.get("price")
    if isinstance(v, (int, float)):
        return float(v)
    v = p.get("unit_price")
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _parse_iso_z(dt: str) -> datetime | None:
    if not isinstance(dt, str) or not dt:
        return None
    try:
        # Example: 2026-04-04T00:00:00Z
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except Exception:
        return None


def _pick_coupon(coupons: list[dict], *, now: datetime, max_min_cart: float | None = None, want_type: str | None = None):
    for c in coupons:
        if not isinstance(c, dict):
            continue
        if c.get("is_active") is False:
            continue
        exp = _parse_iso_z(c.get("expiry_date"))
        if exp is not None and exp <= now:
            continue
        min_cart = c.get("min_cart_value")
        if max_min_cart is not None and isinstance(min_cart, (int, float)) and float(min_cart) > max_min_cart:
            continue
        if want_type is not None:
            dtype = c.get("discount_type")
            if not (isinstance(dtype, str) and dtype.upper() == want_type.upper()):
                continue
        code = c.get("coupon_code") or c.get("code")
        if isinstance(code, str) and code:
            return c
    return None


def _extract_cart_items(cart_payload: dict):
    items = cart_payload.get("items") or cart_payload.get("cart_items") or []
    return items if isinstance(items, list) else []


def _compute_cart_total_from_items(items: list[dict]) -> float:
    total = 0.0
    for it in items:
        if not isinstance(it, dict):
            continue
        qty = it.get("quantity")
        unit = it.get("unit_price")
        if isinstance(qty, int) and isinstance(unit, (int, float)):
            total += float(qty) * float(unit)
    return total


def _get_err(resp, qc):
    try:
        payload = qc.get_json(resp)
    except AssertionError:
        return resp.text[:200]
    if isinstance(payload, dict):
        return payload.get("error") or payload.get("message") or str(payload)[:200]
    return str(payload)[:200]


def test_products_price_matches_admin_database_for_sample(qc, qc_user_id):
    admin = qc.request("GET", "/api/v1/admin/products")
    assert admin.status_code == 200
    admin_rows = [r for r in _as_list(qc.get_json(admin)) if isinstance(r, dict)]

    user = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert user.status_code == 200
    user_rows = [r for r in _as_list(qc.get_json(user)) if isinstance(r, dict)]

    user_price_by_id = {}
    for r in user_rows:
        pid = _get_product_id(r)
        price = _get_price(r)
        if pid is not None and price is not None:
            user_price_by_id[pid] = price

    checked = 0
    for r in admin_rows:
        if checked >= 20:
            break
        if r.get("is_active") is not True:
            continue
        pid = _get_product_id(r)
        if pid is None:
            continue
        admin_price = _get_price(r)
        if admin_price is None:
            continue
        if pid not in user_price_by_id:
            # User list only returns active; if active product is missing, that's a defect.
            pytest.fail(f"Active product_id={pid} missing from /products")
        assert math.isclose(user_price_by_id[pid], float(admin_price), rel_tol=0, abs_tol=0.000001)
        checked += 1

    if checked == 0:
        pytest.skip("No comparable product prices found")


def test_cart_subtotals_and_total_match_math_and_include_last_item(qc, qc_user_id, qc_clean_cart):
    # Use two distinct products from the user-visible list (active products).
    resp = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(resp)) if isinstance(p, dict)]
    if len(products) < 2:
        pytest.skip("Not enough products")

    p1, p2 = products[0], products[1]
    pid1, pid2 = _get_product_id(p1), _get_product_id(p2)
    if pid1 is None or pid2 is None or pid1 == pid2:
        pytest.skip("Could not pick two distinct product ids")

    add1 = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid1, "quantity": 1})
    assert add1.status_code in (200, 201)
    add2 = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid2, "quantity": 1})
    assert add2.status_code in (200, 201)

    cart = qc.request("GET", "/api/v1/cart", user_id=qc_user_id)
    assert cart.status_code == 200
    payload = qc.get_json(cart)
    assert isinstance(payload, dict)

    items = _extract_cart_items(payload)
    assert isinstance(items, list) and len(items) >= 2

    # Each item subtotal must equal quantity * unit_price.
    computed_total = 0.0
    for it in items:
        if not isinstance(it, dict):
            continue
        qty = it.get("quantity")
        unit = it.get("unit_price")
        subtotal = it.get("subtotal")
        if not (isinstance(qty, int) and isinstance(unit, (int, float)) and isinstance(subtotal, (int, float))):
            pytest.fail(f"Cart item missing numeric fields: {it}")
        expected = float(qty) * float(unit)
        assert math.isclose(float(subtotal), expected, rel_tol=0, abs_tol=0.01)
        computed_total += float(subtotal)

    total = payload.get("total")
    assert isinstance(total, (int, float))
    # Total must be sum of all subtotals, including the last item.
    assert math.isclose(float(total), computed_total, rel_tol=0, abs_tol=0.01)


def test_cart_subtotal_no_overflow_for_larger_quantities(qc, qc_user_id, qc_clean_cart):
    # Pick a low-priced product so qty can be increased safely.
    resp = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(resp)) if isinstance(p, dict)]

    chosen = None
    for p in products:
        price = _get_price(p)
        if price is not None and 1 <= price <= 100:
            chosen = p
            break
    if chosen is None:
        pytest.skip("No low-priced product found")

    pid = _get_product_id(chosen)
    unit = _get_price(chosen)
    if pid is None or unit is None:
        pytest.skip("Could not determine pid/price")

    qty = 10
    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": qty})
    assert add.status_code in (200, 201)

    cart = qc.request("GET", "/api/v1/cart", user_id=qc_user_id)
    assert cart.status_code == 200
    payload = qc.get_json(cart)
    items = _extract_cart_items(payload)

    line = next((it for it in items if isinstance(it, dict) and it.get("product_id") == pid), None)
    if line is None:
        pytest.skip("Could not find cart line")

    subtotal = line.get("subtotal")
    assert isinstance(subtotal, (int, float))
    unit_price = line.get("unit_price")
    if not isinstance(unit_price, (int, float)):
        pytest.skip("Cart line missing numeric unit_price")
    expected = float(qty) * float(unit_price)
    assert math.isclose(float(subtotal), expected, rel_tol=0, abs_tol=0.01)


def test_coupon_apply_accepts_code_field_same_as_coupon_code(qc, qc_user_id, qc_clean_cart):
    now = datetime.now(timezone.utc)

    admin = qc.request("GET", "/api/v1/admin/coupons")
    if admin.status_code != 200:
        pytest.skip("admin/coupons not available")

    coupons = [c for c in _as_list(qc.get_json(admin)) if isinstance(c, dict)]
    coupon = _pick_coupon(coupons, now=now, max_min_cart=200)
    if coupon is None:
        pytest.skip("No suitable non-expired coupon with small min_cart_value")

    code = coupon.get("coupon_code")
    assert isinstance(code, str) and code

    # Build a cart meeting the chosen coupon's minimum cart value.
    # Use admin products to avoid guessing stock and to align with DB pricing.
    prod_admin = qc.request("GET", "/api/v1/admin/products")
    assert prod_admin.status_code == 200
    products = [p for p in _as_list(qc.get_json(prod_admin)) if isinstance(p, dict)]
    if not products:
        pytest.skip("No admin products")

    min_cart = coupon.get("min_cart_value")
    min_cart = float(min_cart) if isinstance(min_cart, (int, float)) else 0.0

    p = next(
        (
            x
            for x in products
            if x.get("is_active") is True
            and _get_product_id(x) is not None
            and (_get_price(x) or 0) > 0
            and isinstance(x.get("stock_quantity"), int)
            and x.get("stock_quantity") >= 5
        ),
        None,
    )
    if p is None:
        pytest.skip("No usable product")

    pid = _get_product_id(p)
    unit = _get_price(p)
    assert pid is not None and unit is not None

    qty = max(1, int(math.ceil((min_cart / unit))) if unit > 0 else 1)
    stock = p.get("stock_quantity")
    if isinstance(stock, int) and qty > stock:
        pytest.skip("Not enough stock to meet coupon minimum")

    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": qty})
    assert add.status_code in (200, 201)

    with_code = qc.request("POST", "/api/v1/coupon/apply", user_id=qc_user_id, json={"code": code})
    with_coupon_code = qc.request("POST", "/api/v1/coupon/apply", user_id=qc_user_id, json={"coupon_code": code})

    # Per doc, the request field is 'code'. The two requests should be treated equivalently.
    assert with_code.status_code == with_coupon_code.status_code, (
        f"Expected same behavior for code vs coupon_code. "
        f"code={with_code.status_code} err={_get_err(with_code, qc)!r} "
        f"coupon_code={with_coupon_code.status_code} err={_get_err(with_coupon_code, qc)!r}"
    )


def test_card_checkout_sets_paid_and_invoice_gst_math(qc, qc_user_id, qc_clean_cart):
    # Create a small order.
    prod_resp = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert prod_resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(prod_resp)) if isinstance(p, dict)]
    p = next((x for x in products if _get_product_id(x) is not None and (_get_price(x) or 0) > 0), None)
    if p is None:
        pytest.skip("No usable product")

    pid = _get_product_id(p)
    assert pid is not None

    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201)

    chk = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "CARD"})
    assert chk.status_code in (200, 201), chk.text
    chk_payload = qc.get_json(chk)
    assert isinstance(chk_payload, dict)

    order_id = chk_payload.get("order_id") or chk_payload.get("id")
    if not isinstance(order_id, int):
        pytest.skip("Checkout did not return numeric order_id")

    # CARD must start as PAID.
    pay_status = chk_payload.get("payment_status")
    if isinstance(pay_status, str):
        assert pay_status.upper() == "PAID"

    detail = qc.request("GET", f"/api/v1/orders/{order_id}", user_id=qc_user_id)
    assert detail.status_code == 200

    inv = qc.request("GET", f"/api/v1/orders/{order_id}/invoice", user_id=qc_user_id)
    assert inv.status_code == 200
    invoice = qc.get_json(inv)
    assert isinstance(invoice, dict)

    subtotal = invoice.get("subtotal") or invoice.get("sub_total")
    gst = invoice.get("gst") or invoice.get("gst_amount")
    total = invoice.get("total") or invoice.get("grand_total") or invoice.get("total_amount")

    if not all(isinstance(x, (int, float)) for x in (subtotal, gst, total)):
        pytest.skip(f"Invoice numeric fields missing: keys={list(invoice.keys())}")

    subtotal = float(subtotal)
    gst = float(gst)
    total = float(total)

    # Spec: GST is 5% and added once; total = subtotal + gst.
    assert math.isclose(gst, subtotal * 0.05, rel_tol=0, abs_tol=0.05)
    assert math.isclose(total, subtotal + gst, rel_tol=0, abs_tol=0.05)
