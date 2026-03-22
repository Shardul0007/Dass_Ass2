import pytest


def test_wallet_add_allows_max_boundary_100000(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/wallet/add", user_id=qc_user_id, json={"amount": 100000})
    assert resp.status_code in (200, 201), f"status={resp.status_code} body={resp.text[:200]!r}"
