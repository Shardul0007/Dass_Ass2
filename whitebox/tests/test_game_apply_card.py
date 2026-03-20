import pytest

import game


def _make_game_with_stubs(*, stub_ui, board, bank, players):
    # Arrange: construct Game instance without running __init__ (white-box).
    g = game.Game.__new__(game.Game)
    g.ui = stub_ui  # not used directly; we patch module-level ui below
    g.board = board
    g.bank = bank
    g.players = players
    g.current_index = 0
    g.turn_number = 0
    g.running = True
    g.chance_deck = None
    g.community_deck = None
    return g


def test_apply_card_none_returns_no_state_change(stub_ui, monkeypatch):
    # CFG: _apply_card -> if card is None (True branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    # Act
    g._apply_card(player, None)

    # Assert
    assert player.balance == 100
    assert player.position == 0
    assert player.in_jail is False


def test_apply_card_collect_increases_balance(stub_ui, monkeypatch):
    # CFG: _apply_card -> action == 'collect'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=0)
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=bank, players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Collect", "action": "collect", "value": 50}

    # Act
    g._apply_card(player, card)

    # Assert
    assert bank.payouts == [50]
    assert player.balance == 50


def test_apply_card_collect_zero_value_no_change(stub_ui, monkeypatch):
    # Edge-case CFG: _apply_card -> action == 'collect' with value 0
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=123)
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=bank, players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Collect", "action": "collect", "value": 0}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.balance == 123
    assert bank.payouts == [0]


def test_apply_card_pay_decreases_balance_and_collects(stub_ui, monkeypatch):
    # CFG: _apply_card -> action == 'pay'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=bank, players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Pay", "action": "pay", "value": 30}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.balance == 70
    assert bank.collected == 30


def test_apply_card_pay_negative_value_raises_value_error(stub_ui, monkeypatch):
    # Edge/failure CFG: _apply_card -> action == 'pay' with negative value
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=bank, players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Pay", "action": "pay", "value": -1}

    # Act / Assert
    with pytest.raises(ValueError):
        g._apply_card(player, card)


def test_apply_card_jail_sends_player_to_jail(stub_ui, monkeypatch):
    # CFG: _apply_card -> action == 'jail'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Jail", "action": "jail", "value": 0}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.in_jail is True
    assert player.position == 10


def test_apply_card_jail_free_increments_card_count(stub_ui, monkeypatch):
    # CFG: _apply_card -> action == 'jail_free'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", get_out_of_jail_cards=0)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Jail free", "action": "jail_free", "value": 0}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.get_out_of_jail_cards == 1


def test_apply_card_move_to_passes_go_awards_salary(stub_ui, monkeypatch):
    # CFG: _apply_card -> action == 'move_to' and (value < old_pos) True branch
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=0, position=30)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(tile="blank"), bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Move", "action": "move_to", "value": 5}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.position == 5
    assert player.balance == game.GO_SALARY


def test_apply_card_move_to_does_not_pass_go_no_salary(stub_ui, monkeypatch):
    # CFG: _apply_card -> action == 'move_to' and (value < old_pos) False branch
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100, position=5)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(tile="blank"), bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Move", "action": "move_to", "value": 10}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.position == 10
    assert player.balance == 100


def test_apply_card_move_to_lands_on_property_calls_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _apply_card -> move_to -> if tile == 'property' (True branch)
    from conftest import StubBoard, StubBank, StubPlayer, StubProperty

    player = StubPlayer("A", position=20)
    prop = StubProperty(name="P")
    board = StubBoard(tile="property", prop=prop)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"hit": False}

    def _handle_property_tile(_player, _prop):
        called["hit"] = True

    monkeypatch.setattr(g, "_handle_property_tile", _handle_property_tile)

    card = {"description": "Move", "action": "move_to", "value": 1}

    # Act
    g._apply_card(player, card)

    # Assert
    assert called["hit"] is True


def test_apply_card_move_to_not_property_does_not_call_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _apply_card -> move_to -> if tile == 'property' (False branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", position=20)
    board = StubBoard(tile="blank", prop=None)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    def _boom(*_args, **_kwargs):
        raise AssertionError("_handle_property_tile should not be called")

    monkeypatch.setattr(g, "_handle_property_tile", _boom)

    card = {"description": "Move", "action": "move_to", "value": 1}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.position == 1


def test_apply_card_move_to_property_with_missing_property_does_not_call_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _apply_card -> move_to -> tile == 'property' but prop is falsy (False branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player_obj = StubPlayer("A", position=20)
    board = StubBoard(tile="property", prop=None)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank(), players=[player_obj])
    monkeypatch.setattr(game, "ui", stub_ui)

    def _boom(*_args, **_kwargs):
        raise AssertionError("_handle_property_tile should not be called")

    monkeypatch.setattr(g, "_handle_property_tile", _boom)

    card = {"description": "Move", "action": "move_to", "value": 1}

    # Act
    g._apply_card(player_obj, card)

    # Assert
    assert player_obj.position == 1


def test_apply_card_move_to_railroad_triggers_property_tile_handling(stub_ui, monkeypatch):
    # Edge case: move_to should resolve railroad tiles the same way as movement.
    from conftest import StubBoard, StubBank, StubPlayer, StubProperty

    player_obj = StubPlayer("A", position=20)
    prop = StubProperty(name="Rail", owner=None)
    board = StubBoard(tile="railroad", prop=prop)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank(), players=[player_obj])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {}
    monkeypatch.setattr(g, "_handle_property_tile", lambda p, pr: called.update({"p": p, "pr": pr}))

    g._apply_card(player_obj, {"description": "Move", "action": "move_to", "value": 1})

    assert player_obj.position == 1
    assert called["p"] == player_obj
    assert called["pr"] == prop


def test_apply_card_birthday_transfers_from_all_eligible_players(stub_ui, monkeypatch):
    # CFG: _apply_card -> action in {'birthday','collect_from_all'}; transfer loop charges all other players
    from conftest import StubBoard, StubBank, StubPlayer

    recipient = StubPlayer("A", balance=0)
    donor_ok = StubPlayer("B", balance=10)
    donor_poor = StubPlayer("C", balance=5)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=StubBank(), players=[recipient, donor_ok, donor_poor])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "Birthday", "action": "birthday", "value": 6}

    # Act
    g._apply_card(recipient, card)

    # Assert
    assert donor_ok.balance == 4
    assert donor_poor.balance == -1
    assert recipient.balance == 12
    assert recipient.is_eliminated is False
    assert recipient in g.players


def test_apply_card_collect_from_all_no_eligible_donors_no_transfer(stub_ui, monkeypatch):
    # Edge case: even "poor" players still owe the card amount (may go negative).
    from conftest import StubBoard, StubBank, StubPlayer

    recipient = StubPlayer("A", balance=0)
    donor_poor = StubPlayer("B", balance=1)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=StubBank(), players=[recipient, donor_poor])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "All pay", "action": "collect_from_all", "value": 50}

    # Act
    g._apply_card(recipient, card)

    # Assert
    assert recipient.balance == 50
    assert donor_poor.balance == -49

def test_apply_card_collect_from_all_negative_value_is_ignored(stub_ui, monkeypatch):
    # Mutation-killer: guard `if value <= 0: return` must remain.
    from conftest import StubBoard, StubBank, StubPlayer

    recipient = StubPlayer("A", balance=10)
    donor = StubPlayer("B", balance=10)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=StubBank(), players=[recipient, donor])
    monkeypatch.setattr(game, "ui", stub_ui)

    g._apply_card(recipient, {"description": "Bad card", "action": "collect_from_all", "value": -1})

    assert recipient.balance == 10
    assert donor.balance == 10


def test_apply_card_invalid_action_no_effect(stub_ui, monkeypatch):
    # CFG: _apply_card -> handler is None (invalid action branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=StubBoard(), bank=bank, players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    card = {"description": "???", "action": "invalid", "value": 999999}

    # Act
    g._apply_card(player, card)

    # Assert
    assert player.balance == 100
    assert bank.collected == 0
    assert bank.payouts == []
