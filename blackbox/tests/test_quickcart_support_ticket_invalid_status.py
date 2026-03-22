import pytest


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


def test_support_ticket_rejects_invalid_status_value(qc, qc_user_id):
    create = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "invalid-status-check", "message": "hello"},
    )
    assert create.status_code in (200, 201), create.text
    ticket_id = _extract_ticket_id(qc.get_json(create))
    if ticket_id is None:
        pytest.skip("Could not determine ticket_id")

    resp = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "DONE"},
    )
    assert resp.status_code == 400, f"status={resp.status_code} body={resp.text[:200]!r}"
