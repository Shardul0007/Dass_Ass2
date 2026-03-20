import game
import bank as bank_mod
import property as property_mod


def _make_game_with_bank(*, players, bank):
    g = game.Game.__new__(game.Game)
    g.board = None
    g.bank = bank
    g.dice = None
    g.players = players
    g.current_index = 0
    g.turn_number = 0
    g.running = True
    g.chance_deck = None
    g.community_deck = None
    return g


def test_buy_property_allows_exact_funds(monkeypatch):
    # Branch: buy_property affordability boundary (balance == price).
    from conftest import StubPlayer, StubProperty, StubBank

    player = StubPlayer("A", balance=100)
    prop = StubProperty(name="P", price=100, owner=None)
    bank = StubBank()
    g = _make_game_with_bank(players=[player], bank=bank)

    ok = g.buy_property(player, prop)

    assert ok is True
    assert player.balance == 0
    assert prop.owner == player
    assert prop in player.properties
    assert bank.collected == 100


def test_pay_rent_transfers_to_owner_when_not_mortgaged():
    # Branch: pay_rent with non-mortgaged, owned property.
    from conftest import StubPlayer, StubProperty

    owner = StubPlayer("Owner", balance=1000)
    tenant = StubPlayer("Tenant", balance=200)

    class _RentProp(StubProperty):
        def get_rent(self) -> int:  # type: ignore[override]
            return 25

    prop = _RentProp(name="P", price=100, owner=owner, is_mortgaged=False)
    g = _make_game_with_bank(players=[owner, tenant], bank=None)

    g.pay_rent(tenant, prop)

    assert tenant.balance == 175
    assert owner.balance == 1025


def test_pay_rent_noop_when_mortgaged():
    # Branch: pay_rent early-return when mortgaged.
    from conftest import StubPlayer, StubProperty

    owner = StubPlayer("Owner", balance=1000)
    tenant = StubPlayer("Tenant", balance=200)
    prop = StubProperty(name="P", price=100, owner=owner, is_mortgaged=True)
    g = _make_game_with_bank(players=[owner, tenant], bank=None)

    g.pay_rent(tenant, prop)

    assert tenant.balance == 200
    assert owner.balance == 1000


def test_trade_transfers_cash_to_seller_and_property_to_buyer():
    # Branch: trade success path transfers both property and cash.
    from conftest import StubPlayer, StubProperty

    seller = StubPlayer("Seller", balance=0)
    buyer = StubPlayer("Buyer", balance=60)
    prop = StubProperty(name="P", price=50, owner=seller)
    seller.add_property(prop)

    g = _make_game_with_bank(players=[seller, buyer], bank=None)

    ok = g.trade(seller, buyer, prop, cash_amount=50)

    assert ok is True
    assert buyer.balance == 10
    assert seller.balance == 50
    assert prop.owner == buyer
    assert prop not in seller.properties
    assert prop in buyer.properties


def test_mortgage_property_pays_out_from_bank_funds():
    # Branch: mortgage_property success should reduce bank funds via pay_out.
    from conftest import StubPlayer

    player = StubPlayer("A", balance=0)
    bank = bank_mod.Bank()

    prop = property_mod.Property("P", 1, 200, 20, None)
    prop.owner = player
    player.add_property(prop)

    g = _make_game_with_bank(players=[player], bank=bank)

    before = bank.get_balance()
    ok = g.mortgage_property(player, prop)

    assert ok is True
    assert prop.is_mortgaged is True
    assert player.balance == prop.mortgage_value
    assert bank.get_balance() == before - prop.mortgage_value


def test_unmortgage_property_does_not_change_state_if_cannot_afford():
    # Branch: unmortgage_property insufficient funds must not unmortgage.
    from conftest import StubPlayer

    player = StubPlayer("A", balance=0)
    bank = bank_mod.Bank()

    prop = property_mod.Property("P", 1, 200, 20, None)
    prop.owner = player
    player.add_property(prop)
    prop.mortgage()

    assert prop.is_mortgaged is True

    g = _make_game_with_bank(players=[player], bank=bank)

    ok = g.unmortgage_property(player, prop)

    assert ok is False
    assert prop.is_mortgaged is True


def test_unmortgage_property_success_charges_player_and_credits_bank():
    # Branch: unmortgage_property success path.
    from conftest import StubPlayer

    player = StubPlayer("A", balance=1000)
    bank = bank_mod.Bank()

    prop = property_mod.Property("P", 1, 200, 20, None)
    prop.owner = player
    player.add_property(prop)
    prop.mortgage()

    cost = int(prop.mortgage_value * 1.1)
    before_bank = bank.get_balance()

    g = _make_game_with_bank(players=[player], bank=bank)

    ok = g.unmortgage_property(player, prop)

    assert ok is True
    assert prop.is_mortgaged is False
    assert player.balance == 1000 - cost
    assert bank.get_balance() == before_bank + cost
