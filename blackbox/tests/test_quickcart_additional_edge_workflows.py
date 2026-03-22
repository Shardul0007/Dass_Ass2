import math

import pytest


def _get_product_id(product: dict):
    return product.get("product_id") or product.get("id")


def _get_stock(product: dict):
    stock = product.get("stock")
    if not isinstance(stock, int):
        stock = product.get("stock_quantity")
    return stock if isinstance(stock, int) else None


def _get_price(product: dict) -> float | None:
    for key in ("price", "unit_price"):
        val = product.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _pick_active_instock_products(qc_products: list[dict], *, limit: int = 3) -> list[dict]:
    picked: list[dict] = []
    for p in qc_products:
        if not isinstance(p, dict):
            continue
        pid = _get_product_id(p)
        if not isinstance(pid, int):
            continue
        active = p.get("active") if "active" in p else p.get("is_active")
        stock = _get_stock(p)
        if (active is None or active is True) and (stock is None or stock > 0):
            picked.append(p)
            if len(picked) >= limit:
                break
    return picked


@pytest.mark.parametrize(
    "payload",
    [
        # invalid label
        {"label": "HOUSE", "street": "12345 Main Street", "city": "City", "pincode": "123456", "is_default": False},
        # street too short (<5)
        {"label": "HOME", "street": "1234", "city": "City", "pincode": "123456", "is_default": False},
        # street too long (>100)
        {"label": "HOME", "street": "A" * 101, "city": "City", "pincode": "123456", "is_default": False},
        # city too short (<2)
        {"label": "HOME", "street": "12345 Main Street", "city": "C", "pincode": "123456", "is_default": False},
        # city too long (>50)
        {"label": "HOME", "street": "12345 Main Street", "city": "B" * 51, "pincode": "123456", "is_default": False},
        # pincode not 6 digits
        {"label": "HOME", "street": "12345 Main Street", "city": "City", "pincode": "12345", "is_default": False},
        # pincode non-digit
        {"label": "HOME", "street": "12345 Main Street", "city": "City", "pincode": "12A456", "is_default": False},
    ],
)
def test_address_add_validation_matrix(qc, qc_user_id, payload):
    resp = qc.request("POST", "/api/v1/addresses", user_id=qc_user_id, json=payload)
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:300]!r}"


def test_address_default_uniqueness(qc, qc_user_id):
    # Create two addresses, both marked default; server should ensure only one default overall.
    a1 = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "11111 Alpha Street", "city": "Alpha", "pincode": "111111", "is_default": True},
    )
    assert a1.status_code in (200, 201), a1.text

    a2 = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "OFFICE", "street": "22222 Beta Street", "city": "Beta", "pincode": "222222", "is_default": True},
    )
    assert a2.status_code in (200, 201), a2.text

    lst = qc.request("GET", "/api/v1/addresses", user_id=qc_user_id)
    assert lst.status_code == 200, lst.text
    payload = qc.get_json(lst)
    addrs = payload if isinstance(payload, list) else payload.get("addresses") or payload.get("data") or []
    assert isinstance(addrs, list)

    defaults = [a for a in addrs if isinstance(a, dict) and a.get("is_default") is True]
    assert len(defaults) <= 1


@pytest.mark.parametrize("qty", [0, -1])
def test_cart_update_rejects_non_positive(qc, qc_user_id, qc_product, qc_clean_cart, qty):
    pid = _get_product_id(qc_product)
    assert isinstance(pid, int)

    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201), add.text

    upd = qc.request("POST", "/api/v1/cart/update", user_id=qc_user_id, json={"product_id": pid, "quantity": qty})
    assert upd.status_code == 400, f"qty={qty} status={upd.status_code} body={upd.text[:300]!r}"


def test_cart_remove_nonexistent_returns_404(qc, qc_user_id, qc_clean_cart):
    # Attempt to remove a product that isn't in the cart.
    resp = qc.request("POST", "/api/v1/cart/remove", user_id=qc_user_id, json={"product_id": 99999999})
    assert resp.status_code == 404, f"status={resp.status_code} body={resp.text[:300]!r}"


def test_wallet_pay_insufficient_funds_rejected(qc, qc_user_id):
    bal = qc.request("GET", "/api/v1/wallet", user_id=qc_user_id)
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

    resp = qc.request("POST", "/api/v1/wallet/pay", user_id=qc_user_id, json={"amount": int(balance) + 1000000})
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:300]!r}"


def test_support_ticket_status_transitions(qc, qc_user_id):
    # Create a ticket
    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "Payment issue", "message": "Please help: card charged but no order created."},
    )
    assert create.status_code in (200, 201)
    created = qc.get_json(create)

    # Find ticket id
    ticket_id = None
    if isinstance(created, dict):
        ticket_id = created.get("ticket_id") or created.get("id")
        if not isinstance(ticket_id, int):
            for v in created.values():
                if isinstance(v, dict) and isinstance(v.get("ticket_id"), int):
                    ticket_id = v["ticket_id"]
                    break

    if not isinstance(ticket_id, int):
        # Fall back to list tickets and pick newest
        lst = qc.request("GET", "/api/v1/support/tickets", user_id=qc_user_id)
        assert lst.status_code == 200
        payload = qc.get_json(lst)
        tickets = payload if isinstance(payload, list) else payload.get("tickets") or payload.get("data") or []
        if isinstance(tickets, list) and tickets and isinstance(tickets[-1], dict):
            ticket_id = tickets[-1].get("ticket_id") or tickets[-1].get("id")

    if not isinstance(ticket_id, int):
        pytest.skip("Could not determine ticket_id")

    # Forward transition: OPEN -> IN_PROGRESS
    r1 = qc.request("PUT", f"/api/v1/support/tickets/{ticket_id}", user_id=qc_user_id, json={"status": "IN_PROGRESS"})
    assert r1.status_code in (200, 201), r1.text

    # Forward transition: IN_PROGRESS -> CLOSED
    r2 = qc.request("PUT", f"/api/v1/support/tickets/{ticket_id}", user_id=qc_user_id, json={"status": "CLOSED"})
    assert r2.status_code in (200, 201), r2.text

    # Invalid backward transition: CLOSED -> OPEN must 400
    r3 = qc.request("PUT", f"/api/v1/support/tickets/{ticket_id}", user_id=qc_user_id, json={"status": "OPEN"})
    assert r3.status_code == 400, f"status={r3.status_code} body={r3.text[:300]!r}"


def test_reviews_comment_boundaries_and_average_decimal(qc, qc_user_id, qc_products):
    products = _pick_active_instock_products(qc_products, limit=1)
    if not products:
        pytest.skip("No suitable product")
    pid = _get_product_id(products[0])
    assert isinstance(pid, int)

    # Invalid comment length: 0
    resp = qc.request("POST", f"/api/v1/products/{pid}/reviews", user_id=qc_user_id, json={"rating": 3, "comment": ""})
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:200]!r}"

    # Invalid comment length: >200
    resp = qc.request("POST", f"/api/v1/products/{pid}/reviews", user_id=qc_user_id, json={"rating": 3, "comment": "x" * 201})
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:200]!r}"

    # Valid boundary comments
    r1 = qc.request("POST", f"/api/v1/products/{pid}/reviews", user_id=qc_user_id, json={"rating": 1, "comment": "a"})
    assert r1.status_code in (200, 201)
    r2 = qc.request("POST", f"/api/v1/products/{pid}/reviews", user_id=qc_user_id, json={"rating": 2, "comment": "b" * 200})
    assert r2.status_code in (200, 201)

    # Average must be decimal calculation (not floor-int). Best effort: compute from returned reviews.
    getr = qc.request("GET", f"/api/v1/products/{pid}/reviews", user_id=qc_user_id)
    assert getr.status_code == 200
    payload = qc.get_json(getr)

    reviews = payload if isinstance(payload, list) else payload.get("reviews") or payload.get("data") or []
    avg = None
    if isinstance(payload, dict):
        avg = payload.get("average_rating") or payload.get("avg_rating")

    if not isinstance(reviews, list) or not reviews:
        pytest.skip("No reviews returned")

    ratings = [r.get("rating") for r in reviews if isinstance(r, dict) and isinstance(r.get("rating"), (int, float))]
    if not ratings:
        pytest.skip("No numeric ratings")

    computed = float(sum(ratings)) / float(len(ratings))
    if isinstance(avg, (int, float)):
        # Must not floor; allow tolerance
        assert math.isclose(float(avg), computed, rel_tol=0, abs_tol=0.01)


def test_order_cancel_restock_best_effort(qc, qc_user_id, qc_products):
    products = _pick_active_instock_products(qc_products, limit=1)
    if not products:
        pytest.skip("No suitable product")
    product = products[0]
    pid = _get_product_id(product)
    stock0 = _get_stock(product)

    if not isinstance(pid, int) or stock0 is None or stock0 < 2:
        pytest.skip("Need a product with known stock>=2")

    # Clear cart, add one item, checkout with CARD
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201), add.text

    chk = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "CARD"})
    assert chk.status_code in (200, 201), chk.text
    chk_payload = qc.get_json(chk)
    order_id = chk_payload.get("order_id") if isinstance(chk_payload, dict) else None
    if not isinstance(order_id, int):
        pytest.skip("Checkout did not return numeric order_id")

    # Cancel the order
    cancel = qc.request("POST", f"/api/v1/orders/{order_id}/cancel", user_id=qc_user_id)
    assert cancel.status_code in (200, 201), cancel.text

    # Verify stock increased by 1 (via admin/products)
    admin = qc.request("GET", "/api/v1/admin/products")
    assert admin.status_code == 200
    rows = qc.get_json(admin)
    rows = rows if isinstance(rows, list) else rows.get("products") or rows.get("data") or []
    if not isinstance(rows, list):
        pytest.skip("admin/products shape unknown")

    stock_after = None
    for row in rows:
        if isinstance(row, dict) and (row.get("product_id") == pid or row.get("id") == pid):
            stock_val = row.get("stock")
            if not isinstance(stock_val, int):
                stock_val = row.get("stock_quantity")
            if isinstance(stock_val, int):
                stock_after = stock_val
                break

    if stock_after is None:
        pytest.skip("Could not read stock after cancel")

    assert stock_after >= stock0, f"expected stock to be restored. before={stock0} after={stock_after}"
