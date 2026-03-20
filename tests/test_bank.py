import pytest

import bank


class _StubPlayer:
    def __init__(self, name="P"):
        self.name = name
        self.balance = 0

    def add_money(self, amount):
        self.balance += amount


def test_bank_collect_positive_increases_funds():
    b = bank.Bank()
    start = b.get_balance()

    b.collect(10)

    assert b.get_balance() == start + 10


def test_bank_collect_negative_is_ignored():
    # White-box: docstring says negatives are ignored.
    b = bank.Bank()
    start = b.get_balance()

    b.collect(-10)

    assert b.get_balance() == start


def test_bank_pay_out_zero_returns_zero_and_no_change():
    b = bank.Bank()
    start = b.get_balance()

    assert b.pay_out(0) == 0
    assert b.get_balance() == start


def test_bank_pay_out_negative_returns_zero_and_no_change():
    b = bank.Bank()
    start = b.get_balance()

    assert b.pay_out(-1) == 0
    assert b.get_balance() == start


def test_bank_pay_out_insufficient_raises_value_error():
    b = bank.Bank()
    with pytest.raises(ValueError):
        b.pay_out(b.get_balance() + 1)


def test_bank_give_loan_reduces_bank_funds_and_credits_player():
    # White-box: docstring says bank funds are reduced.
    b = bank.Bank()
    p = _StubPlayer("A")
    start_funds = b.get_balance()

    b.give_loan(p, 10)

    assert p.balance == 10
    assert b.get_balance() == start_funds - 10
    assert b.loan_count() == 1
    assert b.total_loans_issued() == 10


def test_bank_give_loan_zero_does_nothing():
    b = bank.Bank()
    p = _StubPlayer()
    start_funds = b.get_balance()

    b.give_loan(p, 0)

    assert p.balance == 0
    assert b.get_balance() == start_funds
    assert b.loan_count() == 0


def test_bank_summary_and_repr_branches(monkeypatch):
    b = bank.Bank()
    b.collect(123)

    lines = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: lines.append(" ".join(str(x) for x in a)))

    b.summary()

    joined = "\n".join(lines)
    assert "Bank reserves" in joined
    assert "Total collected" in joined
    assert "Loans issued" in joined

    assert "Bank(funds=" in repr(b)
