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


def _pick_non_expired_coupon_with_min(coupons: list[dict], *, now: datetime) -> dict | None:
    for c in coupons:
        if not isinstance(c, dict):
            continue
        if c.get("is_active") is False:
            continue
        code = c.get("coupon_code")
        if not isinstance(code, str) or not code:
            continue
        min_cart = c.get("min_cart_value")
        if not isinstance(min_cart, (int, float)) or float(min_cart) <= 0:
            continue
        exp = _parse_iso_z(c.get("expiry_date"))
        if exp is not None and exp <= now:
            continue
        return c
    return None


def _pick_product_under_price(products: list[dict], *, max_price: float) -> dict | None:
    for p in products:
        if not isinstance(p, dict):
            continue
        if p.get("is_active") is not True:
            continue
        pid = p.get("product_id")
        price = p.get("price")
        stock = p.get("stock_quantity")
        if not (isinstance(pid, int) and isinstance(price, (int, float)) and isinstance(stock, int)):
            continue
        if stock < 1:
            continue
        if 0 < float(price) < float(max_price):
            return p
    return None


def _extract_ticket_id(payload: object) -> int | None:
    if isinstance(payload, dict):
        for key in ("ticket_id", "id"):
            v = payload.get(key)
            if isinstance(v, int) and v > 0:
                return v
        for v in payload.values():
            if isinstance(v, dict):
                for key in ("ticket_id", "id"):
                    vv = v.get(key)
                    if isinstance(vv, int) and vv > 0:
                        return vv
    return None


def _find_ticket_row(admin_payload: object, ticket_id: int) -> dict | None:
    for row in _as_list(admin_payload):
        if not isinstance(row, dict):
            continue
        tid = row.get("ticket_id") or row.get("id")
        if tid == ticket_id:
            return row
    if isinstance(admin_payload, dict):
        for v in admin_payload.values():
            if isinstance(v, list):
                for row in v:
                    if not isinstance(row, dict):
                        continue
                    tid = row.get("ticket_id") or row.get("id")
                    if tid == ticket_id:
                        return row
    return None


def _extract_first_str(row: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = row.get(k)
        if isinstance(v, str):
            return v
    return None


def _extract_first_float(row: dict, keys: tuple[str, ...]) -> float | None:
    for k in keys:
        v = row.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _extract_order_id(payload: object) -> int | None:
    if isinstance(payload, dict):
        for key in ("order_id", "id"):
            v = payload.get(key)
            if isinstance(v, int) and v > 0:
                return v
    return None


def _find_order_row(admin_payload: object, order_id: int) -> dict | None:
    for row in _as_list(admin_payload):
        if not isinstance(row, dict):
            continue
        oid = row.get("order_id") or row.get("id")
        if oid == order_id:
            return row
    if isinstance(admin_payload, dict):
        for v in admin_payload.values():
            if isinstance(v, list):
                for row in v:
                    if not isinstance(row, dict):
                        continue
                    oid = row.get("order_id") or row.get("id")
                    if oid == order_id:
                        return row
    return None


def _extract_order_ids_from_user_orders(payload: object) -> list[int]:
    orders: list[dict] = []
    if isinstance(payload, list):
        orders = [x for x in payload if isinstance(x, dict)]
    elif isinstance(payload, dict):
        for key in ("orders", "data", "items"):
            v = payload.get(key)
            if isinstance(v, list):
                orders = [x for x in v if isinstance(x, dict)]
                break
        if not orders:
            # fall back: first list-valued field
            for v in payload.values():
                if isinstance(v, list):
                    orders = [x for x in v if isinstance(x, dict)]
                    break

    ids: list[int] = []
    for row in orders:
        oid = row.get("order_id") or row.get("id")
        if isinstance(oid, int) and oid > 0:
            ids.append(oid)
    return ids


def test_coupon_rejected_when_cart_below_min_cart_value(qc, qc_user_id, qc_clean_cart):
    now = datetime.now(timezone.utc)

    coupons_resp = qc.request("GET", "/api/v1/admin/coupons")
    if coupons_resp.status_code != 200:
        pytest.skip("admin/coupons not available")
    coupons = [c for c in _as_list(qc.get_json(coupons_resp)) if isinstance(c, dict)]

    coupon = _pick_non_expired_coupon_with_min(coupons, now=now)
    if coupon is None:
        pytest.skip("No suitable non-expired coupon with min_cart_value > 0")

    code = coupon["coupon_code"]
    min_cart = float(coupon["min_cart_value"])

    prod_resp = qc.request("GET", "/api/v1/admin/products")
    assert prod_resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(prod_resp)) if isinstance(p, dict)]

    product = _pick_product_under_price(products, max_price=min_cart)
    if product is None:
        pytest.skip("No active product with price < min_cart_value")

    pid = product["product_id"]

    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201), add.text

    # Per doc: cart total must meet coupon's minimum cart value.
    resp = qc.request("POST", "/api/v1/coupon/apply", user_id=qc_user_id, json={"coupon_code": code})
    assert resp.status_code == 400, (
        f"Expected coupon rejected when cart below min_cart_value={min_cart}; "
        f"got {resp.status_code} body={resp.text[:200]!r}"
    )


def test_support_ticket_message_saved_exactly_via_admin(qc, qc_user_id):
    unique = datetime.now(timezone.utc).isoformat()
    subject = f"exact-message-check {unique}"
    message = f"Line1 {unique}\nLine2 !@#$%^&*()[]{{}}\\|;:'\",.<>/?"

    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": subject, "message": message},
    )
    assert create.status_code in (200, 201), create.text
    created = qc.get_json(create)

    ticket_id = _extract_ticket_id(created)
    if ticket_id is None:
        pytest.skip("Ticket create response did not expose ticket_id")

    admin = qc.request("GET", "/api/v1/admin/tickets")
    if admin.status_code != 200:
        pytest.skip("admin/tickets not available")

    row = _find_ticket_row(qc.get_json(admin), ticket_id)
    if row is None:
        pytest.skip("Could not find created ticket in admin/tickets")

    saved_message = _extract_first_str(row, ("message", "ticket_message", "content", "description"))
    if saved_message is None:
        pytest.skip(f"admin/tickets did not expose message field. keys={list(row.keys())}")

    assert saved_message == message

    status = _extract_first_str(row, ("status", "ticket_status"))
    if status is not None:
        assert status.upper() == "OPEN"


def test_support_ticket_invalid_transition_open_to_closed_rejected(qc, qc_user_id):
    unique = datetime.now(timezone.utc).isoformat()
    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": f"transition-check {unique}", "message": "hello"},
    )
    assert create.status_code in (200, 201), create.text

    ticket_id = _extract_ticket_id(qc.get_json(create))
    if ticket_id is None:
        pytest.skip("Ticket create response did not expose ticket_id")

    # Spec: OPEN -> IN_PROGRESS -> CLOSED only. OPEN -> CLOSED is not allowed.
    upd = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "CLOSED"},
    )
    assert upd.status_code == 400, f"Expected OPEN->CLOSED rejected; got {upd.status_code} body={upd.text[:200]!r}"


def test_support_ticket_starts_open_status_in_admin(qc, qc_user_id):
    unique = datetime.now(timezone.utc).isoformat()
    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": f"status-open-check {unique}", "message": "hello"},
    )
    assert create.status_code in (200, 201), create.text
    ticket_id = _extract_ticket_id(qc.get_json(create))
    if ticket_id is None:
        pytest.skip("Ticket create response did not expose ticket_id")

    admin = qc.request("GET", "/api/v1/admin/tickets")
    if admin.status_code != 200:
        pytest.skip("admin/tickets not available")

    row = _find_ticket_row(qc.get_json(admin), ticket_id)
    if row is None:
        pytest.skip("Could not find created ticket in admin/tickets")

    status = _extract_first_str(row, ("status", "ticket_status"))
    assert isinstance(status, str), f"Ticket status missing in admin row. keys={list(row.keys())}"
    assert status.upper() == "OPEN"


def test_reviews_average_is_decimal_with_two_users(qc, qc_user_ids):
    if len(qc_user_ids) < 2:
        pytest.skip("Need at least 2 users")

    u1, u2 = qc_user_ids[0], qc_user_ids[1]

    # Find a product that currently has no reviews (best effort).
    products_resp = qc.request("GET", "/api/v1/products", user_id=u1)
    assert products_resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(products_resp)) if isinstance(p, dict)]
    if not products:
        pytest.skip("No products")

    product_id = None
    for p in products[:20]:
        pid = p.get("product_id") or p.get("id")
        if not isinstance(pid, int):
            continue
        r = qc.request("GET", f"/api/v1/products/{pid}/reviews", user_id=u1)
        if r.status_code != 200:
            continue
        payload = qc.get_json(r)
        avg = None
        if isinstance(payload, dict):
            avg = payload.get("average_rating") or payload.get("avg_rating")
            reviews = payload.get("reviews") or payload.get("data")
            if avg == 0 and (reviews == [] or reviews is None):
                product_id = pid
                break
        elif isinstance(payload, list) and not payload:
            product_id = pid
            break

    if product_id is None:
        pytest.skip("Could not find a product with no reviews for clean average check")

    r1 = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=u1,
        json={"rating": 4, "comment": "good"},
    )
    assert r1.status_code in (200, 201), r1.text

    r2 = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=u2,
        json={"rating": 5, "comment": "great"},
    )
    assert r2.status_code in (200, 201), r2.text

    resp = qc.request("GET", f"/api/v1/products/{product_id}/reviews", user_id=u1)
    assert resp.status_code == 200
    payload = qc.get_json(resp)

    if isinstance(payload, dict):
        avg = payload.get("average_rating") or payload.get("avg_rating")
    else:
        pytest.skip("reviews GET payload shape unknown")

    if not isinstance(avg, (int, float)):
        pytest.skip("Average rating not exposed as number")

    assert math.isclose(float(avg), 4.5, rel_tol=0, abs_tol=0.01)


def test_payment_status_matches_method_via_admin_orders(qc, qc_user_id, qc_products, qc_clean_cart):
    # Pick an active, in-stock product.
    p = next(
        (
            x
            for x in qc_products
            if isinstance(x, dict)
            and x.get("is_active") is True
            and isinstance(x.get("product_id"), int)
            and isinstance(x.get("stock_quantity"), int)
            and x.get("stock_quantity") >= 2
        ),
        None,
    )
    if p is None:
        pytest.skip("No suitable product")

    pid = p["product_id"]

    def _place_order(method: str) -> int:
        qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
        add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
        assert add.status_code in (200, 201), add.text
        chk = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": method})
        assert chk.status_code in (200, 201), chk.text
        oid = _extract_order_id(qc.get_json(chk))
        if oid is None:
            pytest.skip("checkout response did not expose order_id")
        return oid

    def _payment_status(order_id: int) -> str | None:
        admin = qc.request("GET", "/api/v1/admin/orders")
        if admin.status_code != 200:
            pytest.skip("admin/orders not available")
        row = _find_order_row(qc.get_json(admin), order_id)
        if row is None:
            pytest.skip("Could not find order in admin/orders")
        return _extract_first_str(row, ("payment_status", "paymentState", "payment"))

    card_id = _place_order("CARD")
    card_status = _payment_status(card_id)
    if card_status is not None:
        assert card_status.upper() == "PAID"

    cod_id = _place_order("COD")
    cod_status = _payment_status(cod_id)
    if cod_status is not None:
        assert cod_status.upper() == "PENDING"


def test_support_ticket_rejects_empty_message(qc, qc_user_id):
    resp = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "valid subject", "message": ""},
    )
    assert resp.status_code == 400


def test_support_ticket_rejects_subject_too_long(qc, qc_user_id):
    resp = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "s" * 101, "message": "hello"},
    )
    assert resp.status_code == 400


def test_reviews_average_matches_mean_of_returned_ratings(qc, qc_user_ids, qc_product):
    if len(qc_user_ids) < 2:
        pytest.skip("Need at least 2 users")

    u1, u2 = qc_user_ids[0], qc_user_ids[1]
    pid = qc_product.get("product_id") or qc_product.get("id")
    if not isinstance(pid, int):
        pytest.skip("Could not determine product_id")

    # Add two reviews with different ratings (best effort; if API prevents duplicates, skip).
    r1 = qc.request(
        "POST",
        f"/api/v1/products/{pid}/reviews",
        user_id=u1,
        json={"rating": 4, "comment": "good"},
    )
    if r1.status_code not in (200, 201, 409):
        pytest.skip(f"Could not post review as user1: {r1.status_code}")

    r2 = qc.request(
        "POST",
        f"/api/v1/products/{pid}/reviews",
        user_id=u2,
        json={"rating": 5, "comment": "great"},
    )
    if r2.status_code not in (200, 201, 409):
        pytest.skip(f"Could not post review as user2: {r2.status_code}")

    resp = qc.request("GET", f"/api/v1/products/{pid}/reviews", user_id=u1)
    assert resp.status_code == 200
    payload = qc.get_json(resp)
    if not isinstance(payload, dict):
        pytest.skip("reviews GET payload shape unknown")

    avg = payload.get("average_rating") or payload.get("avg_rating")
    reviews = payload.get("reviews") or payload.get("data")

    if not isinstance(avg, (int, float)):
        pytest.skip("Average rating not exposed as number")
    if not isinstance(reviews, list):
        pytest.skip("Reviews list not exposed")

    ratings = []
    for row in reviews:
        if isinstance(row, dict) and isinstance(row.get("rating"), (int, float)):
            ratings.append(float(row["rating"]))

    # Need enough ratings to make a meaningful decimal check.
    if len(ratings) < 2:
        pytest.skip("Not enough review ratings returned")

    mean = sum(ratings) / len(ratings)
    assert math.isclose(float(avg), mean, rel_tol=0, abs_tol=0.01)


def test_invoice_total_matches_admin_order_total(qc, qc_user_id, qc_products, qc_clean_cart):
    p = next(
        (
            x
            for x in qc_products
            if isinstance(x, dict)
            and x.get("is_active") is True
            and isinstance(x.get("product_id"), int)
            and isinstance(x.get("stock_quantity"), int)
            and x.get("stock_quantity") >= 1
            and isinstance(x.get("price"), (int, float))
            and x.get("price") > 0
        ),
        None,
    )
    if p is None:
        pytest.skip("No suitable product")

    pid = p["product_id"]

    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201), add.text

    chk = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "CARD"})
    assert chk.status_code in (200, 201), chk.text
    chk_payload = qc.get_json(chk)
    order_id = _extract_order_id(chk_payload)
    if order_id is None:
        pytest.skip("checkout response did not expose order_id")

    inv = qc.request("GET", f"/api/v1/orders/{order_id}/invoice", user_id=qc_user_id)
    assert inv.status_code == 200
    invoice = qc.get_json(inv)
    if not isinstance(invoice, dict):
        pytest.skip("Invoice payload shape unknown")

    invoice_total = _extract_first_float(invoice, ("total", "grand_total", "total_amount"))
    if invoice_total is None:
        pytest.skip("Invoice did not expose numeric total")

    admin_orders = qc.request("GET", "/api/v1/admin/orders")
    if admin_orders.status_code != 200:
        pytest.skip("admin/orders not available")
    row = _find_order_row(qc.get_json(admin_orders), order_id)
    if row is None:
        pytest.skip("Could not find order in admin/orders")

    order_total = _extract_first_float(row, ("total", "total_amount", "grand_total"))
    if order_total is None:
        pytest.skip("admin/orders did not expose numeric order total")

    assert math.isclose(float(invoice_total), float(order_total), rel_tol=0, abs_tol=0.01)


def test_orders_list_is_scoped_to_user_via_admin_ground_truth(qc, qc_user_id):
    user_orders = qc.request("GET", "/api/v1/orders", user_id=qc_user_id)
    assert user_orders.status_code == 200
    user_ids = _extract_order_ids_from_user_orders(qc.get_json(user_orders))
    if not user_ids:
        pytest.skip("No user orders to validate scoping")

    admin = qc.request("GET", "/api/v1/admin/orders")
    if admin.status_code != 200:
        pytest.skip("admin/orders not available")
    admin_rows = [r for r in _as_list(qc.get_json(admin)) if isinstance(r, dict)]
    allowed = set()
    for r in admin_rows:
        if r.get("user_id") == qc_user_id:
            oid = r.get("order_id") or r.get("id")
            if isinstance(oid, int) and oid > 0:
                allowed.add(oid)

    if not allowed:
        pytest.skip("admin/orders did not expose any orders for this user")

    # Spec: user can view all *their* orders.
    assert all(oid in allowed for oid in user_ids)


def test_order_detail_not_accessible_for_other_users(qc, qc_user_id):
    admin = qc.request("GET", "/api/v1/admin/orders")
    if admin.status_code != 200:
        pytest.skip("admin/orders not available")
    admin_rows = [r for r in _as_list(qc.get_json(admin)) if isinstance(r, dict)]

    other_order_id = None
    for r in admin_rows:
        oid = r.get("order_id") or r.get("id")
        uid = r.get("user_id")
        if isinstance(oid, int) and oid > 0 and isinstance(uid, int) and uid != qc_user_id:
            other_order_id = oid
            break
    if other_order_id is None:
        pytest.skip("No other-user order found in admin/orders")

    # Spec implies user-scoped orders should not leak other users' data.
    resp = qc.request("GET", f"/api/v1/orders/{other_order_id}", user_id=qc_user_id)
    assert resp.status_code != 200, f"Expected not accessible; got 200 body={resp.text[:200]!r}"


def test_wallet_add_rejects_negative_amount(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/wallet/add", user_id=qc_user_id, json={"amount": -1})
    assert resp.status_code == 400


def test_wallet_pay_rejects_negative_amount(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/wallet/pay", user_id=qc_user_id, json={"amount": -1})
    assert resp.status_code == 400


def test_loyalty_redeem_rejects_negative_amount(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/loyalty/redeem", user_id=qc_user_id, json={"amount": -1})
    assert resp.status_code == 400


def test_support_ticket_invalid_transition_in_progress_to_open_rejected(qc, qc_user_id):
    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "transition-inprogress-open", "message": "hello"},
    )
    assert create.status_code in (200, 201), create.text
    ticket_id = _extract_ticket_id(qc.get_json(create))
    if ticket_id is None:
        pytest.skip("Ticket create response did not expose ticket_id")

    to_in_progress = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "IN_PROGRESS"},
    )
    assert to_in_progress.status_code in (200, 201), to_in_progress.text

    # Spec: status can only move forward; IN_PROGRESS -> OPEN must be rejected.
    back_to_open = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "OPEN"},
    )
    assert back_to_open.status_code == 400


def test_support_ticket_invalid_transition_closed_to_in_progress_rejected(qc, qc_user_id):
    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "transition-closed-inprogress", "message": "hello"},
    )
    assert create.status_code in (200, 201), create.text
    ticket_id = _extract_ticket_id(qc.get_json(create))
    if ticket_id is None:
        pytest.skip("Ticket create response did not expose ticket_id")

    to_in_progress = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "IN_PROGRESS"},
    )
    assert to_in_progress.status_code in (200, 201), to_in_progress.text

    to_closed = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "CLOSED"},
    )
    assert to_closed.status_code in (200, 201), to_closed.text

    # Spec: CLOSED is terminal; CLOSED -> IN_PROGRESS must be rejected.
    back_to_in_progress = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "IN_PROGRESS"},
    )
    assert back_to_in_progress.status_code == 400
