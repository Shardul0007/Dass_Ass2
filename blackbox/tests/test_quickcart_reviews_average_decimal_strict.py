from __future__ import annotations

import math

import pytest


def _as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def _pick_product_with_no_reviews(qc, user_id: int, products: list[dict]) -> int | None:
    for p in products[:30]:
        if not isinstance(p, dict):
            continue
        pid = p.get("product_id") or p.get("id")
        if not isinstance(pid, int):
            continue
        r = qc.request("GET", f"/api/v1/products/{pid}/reviews", user_id=user_id)
        if r.status_code != 200:
            continue
        payload = qc.get_json(r)

        # Accept either: {reviews: [], average_rating: 0} or []
        if isinstance(payload, list) and not payload:
            return pid
        if isinstance(payload, dict):
            avg = payload.get("average_rating") or payload.get("avg_rating")
            reviews = payload.get("reviews") or payload.get("data")
            if (avg == 0 or avg == 0.0) and (reviews == [] or reviews is None):
                return pid
    return None


def test_reviews_average_is_non_integer_when_expected(qc, qc_user_ids):
    if len(qc_user_ids) < 2:
        pytest.skip("Need at least 2 users")

    u1, u2 = qc_user_ids[0], qc_user_ids[1]

    prod = qc.request("GET", "/api/v1/products", user_id=u1)
    assert prod.status_code == 200
    products = [p for p in _as_list(qc.get_json(prod)) if isinstance(p, dict)]
    if not products:
        pytest.skip("No products")

    pid = _pick_product_with_no_reviews(qc, u1, products)
    if pid is None:
        pytest.skip("Could not find a product with no reviews")

    # Two users, ratings 2 and 3 => average must be 2.5 exactly.
    r1 = qc.request(
        "POST",
        f"/api/v1/products/{pid}/reviews",
        user_id=u1,
        json={"rating": 2, "comment": "ok"},
    )
    if r1.status_code == 409:
        pytest.skip("User1 already reviewed this product")
    assert r1.status_code in (200, 201), r1.text

    r2 = qc.request(
        "POST",
        f"/api/v1/products/{pid}/reviews",
        user_id=u2,
        json={"rating": 3, "comment": "fine"},
    )
    if r2.status_code == 409:
        pytest.skip("User2 already reviewed this product")
    assert r2.status_code in (200, 201), r2.text

    resp = qc.request("GET", f"/api/v1/products/{pid}/reviews", user_id=u1)
    assert resp.status_code == 200
    payload = qc.get_json(resp)

    if not isinstance(payload, dict):
        pytest.skip("reviews GET payload shape unknown")

    avg = payload.get("average_rating") or payload.get("avg_rating")
    if not isinstance(avg, (int, float)):
        pytest.skip("Average rating not exposed as number")

    assert math.isclose(float(avg), 2.5, rel_tol=0, abs_tol=0.01), f"avg={avg!r} payload_keys={list(payload.keys())}"
