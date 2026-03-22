import pytest


def _get_product_id(product: dict):
    for key in ("product_id", "id"):
        if key in product:
            return product[key]
    raise AssertionError(f"Could not determine product id from keys={list(product)}")


def test_reviews_reject_empty_comment(qc, qc_user_id, qc_product):
    product_id = _get_product_id(qc_product)
    resp = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 5, "comment": ""},
    )
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:200]!r}"


def test_reviews_reject_too_long_comment(qc, qc_user_id, qc_product):
    product_id = _get_product_id(qc_product)
    resp = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 5, "comment": "x" * 201},
    )
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:200]!r}"
