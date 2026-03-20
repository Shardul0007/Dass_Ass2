import game


def _make_game_with_stubs(*, stub_ui, board, bank, chance_deck=None, community_deck=None):
    g = game.Game.__new__(game.Game)
    g.board = board
    g.bank = bank
    g.dice = None
    g.players = []
    g.current_index = 0
    g.turn_number = 0
    g.running = True
    g.chance_deck = chance_deck
    g.community_deck = community_deck
    return g


def test_move_and_resolve_go_to_jail_branch(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'go_to_jail' (True branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", position=0)
    board = StubBoard(tile="go_to_jail")
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=bank)
    monkeypatch.setattr(game, "ui", stub_ui)

    # Act
    g._move_and_resolve(player, steps=5)

    # Assert
    assert player.in_jail is True
    assert player.position == 10


def test_move_and_resolve_income_tax_branch_deducts_and_collects(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'income_tax'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=100)
    board = StubBoard(tile="income_tax")
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=bank)
    monkeypatch.setattr(game, "ui", stub_ui)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert player.balance == 100 - game.INCOME_TAX_AMOUNT
    assert bank.collected == game.INCOME_TAX_AMOUNT


def test_move_and_resolve_luxury_tax_branch_deducts_and_collects(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'luxury_tax'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=1000)
    board = StubBoard(tile="luxury_tax")
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=bank)
    monkeypatch.setattr(game, "ui", stub_ui)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert player.balance == 1000 - game.LUXURY_TAX_AMOUNT
    assert bank.collected == game.LUXURY_TAX_AMOUNT


def test_move_and_resolve_free_parking_branch_no_state_change(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'free_parking'
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A", balance=123)
    board = StubBoard(tile="free_parking")
    bank = StubBank()
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=bank)
    monkeypatch.setattr(game, "ui", stub_ui)

    # Act
    g._move_and_resolve(player, steps=0)

    # Assert
    assert player.balance == 123
    assert bank.collected == 0


def test_move_and_resolve_chance_branch_draws_and_applies_card(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'chance'
    from conftest import StubBoard, StubBank, StubDeck, StubPlayer

    player = StubPlayer("A")
    board = StubBoard(tile="chance")
    bank = StubBank()
    deck = StubDeck(card={"description": "Collect", "action": "collect", "value": 1})
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=bank, chance_deck=deck)
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"hit": False}

    def _apply_card(_player, _card):
        called["hit"] = True

    monkeypatch.setattr(g, "_apply_card", _apply_card)
    monkeypatch.setattr(g, "_check_bankruptcy", lambda _p: None)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert called["hit"] is True


def test_move_and_resolve_community_chest_branch_draws_and_applies_card(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'community_chest'
    from conftest import StubBoard, StubBank, StubDeck, StubPlayer

    player = StubPlayer("A")
    board = StubBoard(tile="community_chest")
    bank = StubBank()
    deck = StubDeck(card={"description": "Pay", "action": "pay", "value": 1})
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=bank, community_deck=deck)
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"hit": False}

    def _apply_card(_player, _card):
        called["hit"] = True

    monkeypatch.setattr(g, "_apply_card", _apply_card)
    monkeypatch.setattr(g, "_check_bankruptcy", lambda _p: None)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert called["hit"] is True


def test_move_and_resolve_railroad_with_property_calls_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'railroad' and prop is not None (True branch)
    from conftest import StubBoard, StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="RR")
    board = StubBoard(tile="railroad", prop=prop)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank())
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"hit": False}

    def _handle_property_tile(_player, _prop):
        called["hit"] = True

    monkeypatch.setattr(g, "_handle_property_tile", _handle_property_tile)
    monkeypatch.setattr(g, "_check_bankruptcy", lambda _p: None)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert called["hit"] is True


def test_move_and_resolve_railroad_with_no_property_does_not_call_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'railroad' and prop is None (False branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A")
    board = StubBoard(tile="railroad", prop=None)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank())
    monkeypatch.setattr(game, "ui", stub_ui)

    def _boom(*_args, **_kwargs):
        raise AssertionError("_handle_property_tile should not be called")

    monkeypatch.setattr(g, "_handle_property_tile", _boom)
    monkeypatch.setattr(g, "_check_bankruptcy", lambda _p: None)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert player.position == 1


def test_move_and_resolve_property_with_property_calls_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'property' and prop is not None (True branch)
    from conftest import StubBoard, StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P")
    board = StubBoard(tile="property", prop=prop)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank())
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"hit": False}

    def _handle_property_tile(_player, _prop):
        called["hit"] = True

    monkeypatch.setattr(g, "_handle_property_tile", _handle_property_tile)
    monkeypatch.setattr(g, "_check_bankruptcy", lambda _p: None)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert called["hit"] is True


def test_move_and_resolve_property_with_no_property_does_not_call_handle_property_tile(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> tile == 'property' and prop is None (False branch)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A")
    board = StubBoard(tile="property", prop=None)
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank())
    monkeypatch.setattr(game, "ui", stub_ui)

    def _boom(*_args, **_kwargs):
        raise AssertionError("_handle_property_tile should not be called")

    monkeypatch.setattr(g, "_handle_property_tile", _boom)
    monkeypatch.setattr(g, "_check_bankruptcy", lambda _p: None)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert player.position == 1


def test_move_and_resolve_blank_tile_branch_only_checks_bankruptcy(stub_ui, monkeypatch):
    # CFG: _move_and_resolve -> no tile matches (falls through)
    from conftest import StubBoard, StubBank, StubPlayer

    player = StubPlayer("A")
    board = StubBoard(tile="blank")
    g = _make_game_with_stubs(stub_ui=stub_ui, board=board, bank=StubBank())
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"hit": False}

    def _check_bankruptcy(_player):
        called["hit"] = True

    monkeypatch.setattr(g, "_check_bankruptcy", _check_bankruptcy)

    # Act
    g._move_and_resolve(player, steps=1)

    # Assert
    assert called["hit"] is True
