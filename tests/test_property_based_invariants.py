import builtins

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import bank as bank_mod
import cards as cards_mod
import game as game_mod


class _NoOpUI:
    def confirm(self, _prompt: str) -> bool:
        return False

    def safe_int_input(self, _prompt: str, default: int = 0) -> int:
        return default

    def print_banner(self, _title: str) -> None:
        return

    def print_standings(self, _players) -> None:
        return

    def print_board_ownership(self, _board) -> None:
        return


@given(
    start_balance=st.integers(min_value=0, max_value=5000),
    fine=st.integers(min_value=1, max_value=500),
)
@settings(max_examples=80)
def test_bank_collect_and_pay_out_never_make_funds_negative(start_balance, fine):
    bank = bank_mod.Bank()

    # Force bank to a known small balance via internal field.
    bank._funds = start_balance  # noqa: SLF001

    bank.collect(fine)
    assert bank.get_balance() == start_balance + fine

    payout = min(fine, bank.get_balance())
    paid = bank.pay_out(payout)
    assert paid == payout
    assert bank.get_balance() >= 0


@given(
    cards=st.lists(st.dictionaries(keys=st.text(min_size=1, max_size=8), values=st.integers()), max_size=15),
    draws=st.integers(min_value=0, max_value=80),
)
@settings(max_examples=60)
def test_card_deck_draw_cycles_without_exceptions(cards, draws):
    deck = cards_mod.CardDeck(cards)
    for _ in range(draws):
        card = deck.draw()
        if not cards:
            assert card is None
        else:
            assert card in cards


@given(
    cash_amount=st.integers(min_value=0, max_value=3000),
    buyer_balance=st.integers(min_value=0, max_value=3000),
    seller_balance=st.integers(min_value=0, max_value=3000),
)
@settings(max_examples=120)
def test_trade_conserves_cash_when_valid(cash_amount, buyer_balance, seller_balance):
    from conftest import StubPlayer, StubProperty

    seller = StubPlayer("Seller", balance=seller_balance)
    buyer = StubPlayer("Buyer", balance=buyer_balance)
    prop = StubProperty(name="P", price=100, owner=seller)
    seller.add_property(prop)

    g = game_mod.Game.__new__(game_mod.Game)
    g.bank = None

    before_sum = seller.balance + buyer.balance
    ok = g.trade(seller, buyer, prop, cash_amount=cash_amount)

    if cash_amount > buyer_balance:
        assert ok is False
        assert seller.balance + buyer.balance == before_sum
        assert prop.owner == seller
    else:
        assert ok is True
        assert seller.balance + buyer.balance == before_sum
        assert prop.owner == buyer


@pytest.mark.parametrize("turns", [25, 60])
def test_simulation_many_turns_no_exceptions(monkeypatch, turns):
    # Deterministic simulation: avoid interactive inputs.
    monkeypatch.setattr(game_mod, "ui", _NoOpUI())
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "s")

    g = game_mod.Game(["A", "B", "C"])

    class _FixedDice:
        def __init__(self):
            self.doubles_streak = 0
            self._i = 0
            self._seq = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

        def roll(self):
            self._i = (self._i + 1) % len(self._seq)
            return self._seq[self._i]

        def describe(self):
            return "fixed"

        def is_doubles(self):
            return False

    g.dice = _FixedDice()

    for _ in range(turns):
        g.play_turn()
        assert 0 <= g.current_player().position < 40
        assert g.bank.get_balance() >= 0

        for p in g.players:
            assert 0 <= p.position < 40
            assert p.jail_turns >= 0
            assert p.get_out_of_jail_cards >= 0
