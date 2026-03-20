import builtins

import game


def _make_game_with_stubs(*, players, bank, dice):
    g = game.Game.__new__(game.Game)
    g.board = None
    g.bank = bank
    g.dice = dice
    g.players = players
    g.current_index = 0
    g.turn_number = 0
    g.running = True
    g.chance_deck = None
    g.community_deck = None
    return g


class _FakeDice:
    def __init__(self, roll_value=7):
        self.roll_value = roll_value

    def roll(self):
        return self.roll_value

    def describe(self):
        return "fake"


def test_handle_jail_turn_uses_get_out_of_jail_card_and_moves(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    player.in_jail = True
    player.jail_turns = 0
    player.get_out_of_jail_cards = 1

    bank = StubBank()
    dice = _FakeDice(roll_value=6)
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.confirm_answers = [True]
    monkeypatch.setattr(game, "ui", stub_ui)

    moved = {}
    monkeypatch.setattr(g, "_move_and_resolve", lambda p, steps: moved.update({"p": p, "steps": steps}))

    g._handle_jail_turn(player)

    assert player.in_jail is False
    assert player.jail_turns == 0
    assert player.get_out_of_jail_cards == 0
    assert moved["p"] == player
    assert moved["steps"] == 6


def test_handle_jail_turn_pays_fine_and_moves(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer
    from config import JAIL_FINE

    player = StubPlayer("A", balance=100)
    player.in_jail = True
    player.get_out_of_jail_cards = 0

    bank = StubBank()
    dice = _FakeDice(roll_value=8)
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    # Decline card prompt (skipped), accept fine prompt.
    stub_ui.confirm_answers = [True]
    monkeypatch.setattr(game, "ui", stub_ui)

    moved = {}
    monkeypatch.setattr(g, "_move_and_resolve", lambda p, steps: moved.update({"p": p, "steps": steps}))

    g._handle_jail_turn(player)

    assert bank.collected == JAIL_FINE
    assert player.balance == 100 - JAIL_FINE
    assert player.in_jail is False
    assert player.jail_turns == 0
    assert moved["steps"] == 8


def test_handle_jail_turn_no_action_increments_turn(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    player.in_jail = True
    player.jail_turns = 0
    player.get_out_of_jail_cards = 0

    bank = StubBank()
    dice = _FakeDice(roll_value=5)
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.confirm_answers = [False]
    monkeypatch.setattr(game, "ui", stub_ui)

    monkeypatch.setattr(g, "_move_and_resolve", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Should not move")))

    g._handle_jail_turn(player)

    assert player.in_jail is True
    assert player.jail_turns == 1


def test_handle_jail_turn_mandatory_release_after_three_turns(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer
    from config import JAIL_FINE

    player = StubPlayer("A", balance=100)
    player.in_jail = True
    player.jail_turns = 2
    player.get_out_of_jail_cards = 0

    bank = StubBank()
    dice = _FakeDice(roll_value=3)
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.confirm_answers = [False]
    monkeypatch.setattr(game, "ui", stub_ui)

    moved = {}
    monkeypatch.setattr(g, "_move_and_resolve", lambda p, steps: moved.update({"p": p, "steps": steps}))

    g._handle_jail_turn(player)

    assert player.in_jail is False
    assert player.jail_turns == 0
    assert bank.collected == JAIL_FINE
    assert player.balance == 100 - JAIL_FINE
    assert moved["steps"] == 3


def test_interactive_menu_exercises_each_choice_branch(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    # 1 standings, 2 ownership, 3 mortgage, 4 unmortgage, 5 trade, 6 loan amount, 0 roll
    stub_ui.int_answers = [1, 2, 3, 4, 5, 6, 100, 0]
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"mort": 0, "unmort": 0, "trade": 0, "loan": 0}
    monkeypatch.setattr(g, "_menu_mortgage", lambda _p: called.__setitem__("mort", called["mort"] + 1))
    monkeypatch.setattr(g, "_menu_unmortgage", lambda _p: called.__setitem__("unmort", called["unmort"] + 1))
    monkeypatch.setattr(g, "_menu_trade", lambda _p: called.__setitem__("trade", called["trade"] + 1))
    monkeypatch.setattr(
        bank,
        "give_loan",
        lambda _p, amt: called.__setitem__("loan", amt),
        raising=False,
    )

    g.interactive_menu(player)

    assert stub_ui.standings_calls == 1
    assert stub_ui.board_ownership_calls == 1
    assert called["mort"] == 1
    assert called["unmort"] == 1
    assert called["trade"] == 1
    assert called["loan"] == 100


def test_interactive_menu_loan_amount_non_positive_is_ignored(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    stub_ui.int_answers = [6, 0]
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"loan": 0}
    monkeypatch.setattr(
        bank,
        "give_loan",
        lambda *_args, **_kwargs: called.__setitem__("loan", called["loan"] + 1),
        raising=False,
    )

    g.interactive_menu(player)

    assert called["loan"] == 0


def test_menu_mortgage_no_mortgageable_properties(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    monkeypatch.setattr(game, "ui", stub_ui)

    g._menu_mortgage(player)


def test_menu_mortgage_select_valid_property_calls_mortgage(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P")
    player.add_property(prop)

    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.int_answers = [1]
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {}
    monkeypatch.setattr(g, "mortgage_property", lambda p, pr: called.update({"p": p, "pr": pr}))

    g._menu_mortgage(player)

    assert called["p"] == player
    assert called["pr"] == prop


def test_menu_unmortgage_no_mortgaged_properties(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    monkeypatch.setattr(game, "ui", stub_ui)

    g._menu_unmortgage(player)


def test_menu_trade_exercises_branch_paths(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    # Add one property to trade.
    prop = StubProperty(name="P", owner=player)
    player.add_property(prop)

    # Select partner=1, property=1, cash=25.
    stub_ui.int_answers = [1, 1, 25]
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {}
    monkeypatch.setattr(g, "trade", lambda s, b, pr, cash: called.update({"s": s, "b": b, "pr": pr, "cash": cash}))

    g._menu_trade(player)

    assert called["s"] == player
    assert called["b"] == other
    assert called["pr"] == prop
    assert called["cash"] == 25


def test_auction_property_covers_pass_too_low_too_high_and_winner(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    p1 = StubPlayer("P1", balance=50)
    p2 = StubPlayer("P2", balance=50)
    p3 = StubPlayer("P3", balance=50)

    prop = StubProperty(name="Avenue", price=100)
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[p1, p2, p3], bank=bank, dice=dice)

    # p1 bids 5 (too low), p2 bids 100 (too high), p3 bids 20 (wins)
    stub_ui.int_answers = [5, 100, 20]
    monkeypatch.setattr(game, "ui", stub_ui)

    g.auction_property(prop)

    assert prop.owner == p3
    assert prop in p3.properties
    assert p3.balance == 30
    assert bank.collected == 20


def test_handle_property_tile_unowned_auction_path(monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P", owner=None)
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    monkeypatch.setattr(builtins, "input", lambda _prompt="": "a")

    called = {"auction": 0}
    monkeypatch.setattr(g, "auction_property", lambda _prop: called.__setitem__("auction", called["auction"] + 1))

    g._handle_property_tile(player, prop)

    assert called["auction"] == 1


def test_handle_jail_turn_declines_card_then_pays_fine(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer
    from config import JAIL_FINE

    player = StubPlayer("A", balance=100)
    player.in_jail = True
    player.get_out_of_jail_cards = 1
    player.jail_turns = 0

    bank = StubBank()
    dice = _FakeDice(roll_value=4)
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    # Decline using card, accept paying fine.
    stub_ui.confirm_answers = [False, True]
    monkeypatch.setattr(game, "ui", stub_ui)

    moved = {}
    monkeypatch.setattr(g, "_move_and_resolve", lambda _p, steps: moved.update({"steps": steps}))

    g._handle_jail_turn(player)

    assert bank.collected == JAIL_FINE
    assert player.balance == 100 - JAIL_FINE
    assert player.get_out_of_jail_cards == 1
    assert player.in_jail is False
    assert moved["steps"] == 4


def test_menu_mortgage_invalid_index_does_not_call_mortgage(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P")
    player.add_property(prop)

    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.int_answers = [0]  # idx=-1
    monkeypatch.setattr(game, "ui", stub_ui)

    monkeypatch.setattr(
        g,
        "mortgage_property",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Should not mortgage")),
    )

    g._menu_mortgage(player)


def test_menu_unmortgage_valid_selection_calls_unmortgage(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P")
    prop.is_mortgaged = True
    player.add_property(prop)

    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.int_answers = [1]
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {}
    monkeypatch.setattr(g, "unmortgage_property", lambda p, pr: called.update({"p": p, "pr": pr}))

    g._menu_unmortgage(player)

    assert called["p"] == player
    assert called["pr"] == prop


def test_menu_unmortgage_invalid_index_does_not_call_unmortgage(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P")
    prop.is_mortgaged = True
    player.add_property(prop)

    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    stub_ui.int_answers = [0]  # idx=-1
    monkeypatch.setattr(game, "ui", stub_ui)

    monkeypatch.setattr(
        g,
        "unmortgage_property",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Should not unmortgage")),
    )

    g._menu_unmortgage(player)


def test_interactive_menu_loan_amount_zero_continues_to_next_choice(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    # 6 -> amount 0 (ignored) -> 1 standings -> 0 roll
    stub_ui.int_answers = [6, 0, 1, 0]
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"loan": 0}
    monkeypatch.setattr(bank, "give_loan", lambda *_a, **_k: called.__setitem__("loan", called["loan"] + 1), raising=False)

    g.interactive_menu(player)

    assert called["loan"] == 0
    assert stub_ui.standings_calls == 1


def test_interactive_menu_invalid_choice_is_ignored_and_loops(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    # 7 is an unhandled option; the menu should just loop again.
    stub_ui.int_answers = [7, 0]
    monkeypatch.setattr(game, "ui", stub_ui)

    g.interactive_menu(player)


def test_menu_trade_no_other_players_branch(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player], bank=bank, dice=dice)

    monkeypatch.setattr(game, "ui", stub_ui)

    g._menu_trade(player)


def test_menu_trade_invalid_partner_index_returns(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    stub_ui.int_answers = [0]  # idx=-1
    monkeypatch.setattr(game, "ui", stub_ui)

    g._menu_trade(player)


def test_menu_trade_no_properties_branch(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer

    player = StubPlayer("A")
    other = StubPlayer("B")
    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    stub_ui.int_answers = [1]
    monkeypatch.setattr(game, "ui", stub_ui)

    g._menu_trade(player)


def test_menu_trade_invalid_property_index_returns(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    other = StubPlayer("B")
    player.add_property(StubProperty(name="P", owner=player))

    bank = StubBank()
    dice = _FakeDice()
    g = _make_game_with_stubs(players=[player, other], bank=bank, dice=dice)

    # Select partner=1, then invalid property selection 0 (idx=-1)
    stub_ui.int_answers = [1, 0]
    monkeypatch.setattr(game, "ui", stub_ui)

    monkeypatch.setattr(
        g,
        "trade",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Should not trade")),
    )

    g._menu_trade(player)
