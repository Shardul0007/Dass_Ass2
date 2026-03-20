import builtins

import game


def test_game_init_constructs_components_and_players():
    g = game.Game(["A", "B"])
    assert len(g.players) == 2
    assert g.players[0].name == "A"
    assert g.players[1].name == "B"
    assert g.current_index == 0
    assert g.turn_number == 0
    assert g.running is True
    assert g.board is not None
    assert g.bank is not None
    assert g.dice is not None
    assert g.chance_deck is not None
    assert g.community_deck is not None


def test_current_player_and_advance_turn_wraps_and_increments():
    from conftest import StubPlayer

    p1 = StubPlayer("A")
    p2 = StubPlayer("B")

    g = game.Game.__new__(game.Game)
    g.players = [p1, p2]
    g.current_index = 1
    g.turn_number = 0

    assert g.current_player() == p2

    g.advance_turn()
    assert g.current_index == 0
    assert g.turn_number == 1


def test_handle_property_tile_unowned_skip_path(monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P", owner=None)

    g = game.Game.__new__(game.Game)
    g.players = [player]
    g.bank = StubBank()

    monkeypatch.setattr(builtins, "input", lambda _p="": "s")
    monkeypatch.setattr(g, "buy_property", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Should not buy")))
    monkeypatch.setattr(g, "auction_property", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Should not auction")))

    g._handle_property_tile(player, prop)


def test_handle_property_tile_owned_by_player_no_rent(monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P", owner=player)

    g = game.Game.__new__(game.Game)
    g.players = [player]
    g.bank = StubBank()

    monkeypatch.setattr(g, "pay_rent", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("No rent due")))

    g._handle_property_tile(player, prop)


def test_handle_property_tile_owned_by_other_calls_pay_rent(monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    owner = StubPlayer("O")
    prop = StubProperty(name="P", owner=owner)

    g = game.Game.__new__(game.Game)
    g.players = [player, owner]
    g.bank = StubBank()

    called = {"rent": 0}
    monkeypatch.setattr(g, "pay_rent", lambda *_a, **_k: called.__setitem__("rent", called["rent"] + 1))

    g._handle_property_tile(player, prop)

    assert called["rent"] == 1


def test_auction_property_no_bids_path(stub_ui, monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    p1 = StubPlayer("P1", balance=50)
    p2 = StubPlayer("P2", balance=50)
    prop = StubProperty(name="Avenue", price=100)

    g = game.Game.__new__(game.Game)
    g.players = [p1, p2]
    g.bank = StubBank()

    stub_ui.int_answers = [0, 0]
    monkeypatch.setattr(game, "ui", stub_ui)

    g.auction_property(prop)

    assert prop.owner is None


def test_apply_card_transfer_from_all_actions(monkeypatch):
    from conftest import StubBank, StubBoard, StubPlayer

    bank = StubBank()
    board = StubBoard(tile="blank", prop=None)

    target = StubPlayer("T", balance=0)
    rich = StubPlayer("R", balance=100)
    poor = StubPlayer("P", balance=5)

    g = game.Game.__new__(game.Game)
    g.players = [target, rich, poor]
    g.bank = bank
    g.board = board

    # collect_from_all
    g._apply_card(target, {"description": "from all", "action": "collect_from_all", "value": 10})
    assert target.balance == 10
    assert rich.balance == 90
    assert poor.balance == 5

    # birthday (same transfer function)
    g._apply_card(target, {"description": "birthday", "action": "birthday", "value": 5})
    assert target.balance == 20
    assert rich.balance == 85
    assert poor.balance == 0


def test_apply_card_unknown_action_is_noop():
    from conftest import StubBank, StubBoard, StubPlayer

    bank = StubBank()
    board = StubBoard(tile="blank", prop=None)
    player = StubPlayer("A", balance=100)

    g = game.Game.__new__(game.Game)
    g.players = [player]
    g.bank = bank
    g.board = board

    g._apply_card(player, {"description": "noop", "action": "does_not_exist", "value": 999})

    assert player.balance == 100
    assert bank.collected == 0


def test_check_bankruptcy_eliminates_and_removes_player():
    from conftest import StubPlayer, StubProperty

    p1 = StubPlayer("A", balance=100)
    p2 = StubPlayer("B", balance=0)

    prop = StubProperty(name="P", owner=p2)
    prop.is_mortgaged = True
    p2.add_property(prop)

    g = game.Game.__new__(game.Game)
    g.players = [p1, p2]
    g.current_index = 1

    g._check_bankruptcy(p2)

    assert p2.is_eliminated is True
    assert prop.owner is None
    assert prop.is_mortgaged is False
    assert p2.properties == []
    assert p2 not in g.players
    assert g.current_index == 0


def test_check_bankruptcy_does_not_reset_current_index_when_still_in_range():
    from conftest import StubPlayer

    p1 = StubPlayer("A", balance=100)
    p2 = StubPlayer("B", balance=0)
    p3 = StubPlayer("C", balance=100)

    g = game.Game.__new__(game.Game)
    g.players = [p1, p2, p3]
    g.current_index = 0

    g._check_bankruptcy(p2)

    assert g.current_index == 0
    assert p2 not in g.players


def test_check_bankruptcy_player_not_in_list_does_not_remove(monkeypatch):
    from conftest import StubPlayer

    survivor = StubPlayer("A", balance=100)
    eliminated = StubPlayer("B", balance=0)

    g = game.Game.__new__(game.Game)
    g.players = [survivor]
    g.current_index = 0

    g._check_bankruptcy(eliminated)

    assert eliminated.is_eliminated is True
    assert g.players == [survivor]


def test_handle_property_tile_unowned_buy_path_calls_buy_property(monkeypatch):
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A")
    prop = StubProperty(name="P", owner=None)

    g = game.Game.__new__(game.Game)
    g.players = [player]
    g.bank = StubBank()

    monkeypatch.setattr(builtins, "input", lambda _p="": "b")
    called = {"buy": 0}
    monkeypatch.setattr(g, "buy_property", lambda *_a, **_k: called.__setitem__("buy", called["buy"] + 1))

    g._handle_property_tile(player, prop)
    assert called["buy"] == 1


def test_buy_property_insufficient_funds_returns_false():
    from conftest import StubBank, StubPlayer, StubProperty

    player = StubPlayer("A", balance=10)
    prop = StubProperty(name="P", price=100, owner=None)
    bank = StubBank()

    g = game.Game.__new__(game.Game)
    g.bank = bank

    assert g.buy_property(player, prop) is False
    assert prop.owner is None
    assert bank.collected == 0


def test_pay_rent_owner_none_is_noop():
    from conftest import StubPlayer, StubProperty

    tenant = StubPlayer("Tenant", balance=200)
    prop = StubProperty(name="P", owner=None, is_mortgaged=False)

    g = game.Game.__new__(game.Game)
    g.pay_rent(tenant, prop)

    assert tenant.balance == 200


def test_mortgage_property_owner_mismatch_and_already_mortgaged_paths():
    from conftest import StubBank, StubPlayer
    import property as property_mod

    bank = StubBank()
    owner = StubPlayer("Owner", balance=0)
    other = StubPlayer("Other", balance=0)
    prop = property_mod.Property("P", 1, 200, 20, None)
    prop.owner = owner

    g = game.Game.__new__(game.Game)
    g.bank = bank

    assert g.mortgage_property(other, prop) is False

    prop.mortgage()
    assert g.mortgage_property(owner, prop) is False


def test_mortgage_property_bank_insufficient_reverts_mortgage_flag(monkeypatch):
    from conftest import StubPlayer
    import property as property_mod

    class _FailingBank:
        def pay_out(self, _amount):
            raise ValueError("no funds")

    owner = StubPlayer("Owner", balance=0)
    prop = property_mod.Property("P", 1, 200, 20, None)
    prop.owner = owner

    g = game.Game.__new__(game.Game)
    g.bank = _FailingBank()

    ok = g.mortgage_property(owner, prop)
    assert ok is False
    assert prop.is_mortgaged is False


def test_unmortgage_property_owner_mismatch_and_not_mortgaged_paths():
    from conftest import StubBank, StubPlayer
    import property as property_mod

    bank = StubBank()
    owner = StubPlayer("Owner", balance=1000)
    other = StubPlayer("Other", balance=1000)
    prop = property_mod.Property("P", 1, 200, 20, None)
    prop.owner = owner

    g = game.Game.__new__(game.Game)
    g.bank = bank

    assert g.unmortgage_property(other, prop) is False
    assert g.unmortgage_property(owner, prop) is False


def test_trade_failure_branches():
    from conftest import StubPlayer, StubProperty

    seller = StubPlayer("Seller", balance=0)
    buyer = StubPlayer("Buyer", balance=10)
    prop = StubProperty(name="P", owner=None)

    g = game.Game.__new__(game.Game)

    assert g.trade(seller, buyer, prop, cash_amount=5) is False

    prop.owner = seller
    assert g.trade(seller, buyer, prop, cash_amount=50) is False


def test_apply_card_none_is_noop():
    from conftest import StubBank, StubBoard, StubPlayer

    g = game.Game.__new__(game.Game)
    g.players = []
    g.bank = StubBank()
    g.board = StubBoard(tile="blank", prop=None)

    player = StubPlayer("A", balance=100)
    g._apply_card(player, None)
    assert player.balance == 100


def test_check_bankruptcy_non_bankrupt_is_noop():
    from conftest import StubPlayer

    p = StubPlayer("A", balance=1)
    g = game.Game.__new__(game.Game)
    g.players = [p]
    g.current_index = 0

    g._check_bankruptcy(p)

    assert p.is_eliminated is False
    assert g.players == [p]
