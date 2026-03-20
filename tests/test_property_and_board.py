import pytest

import board
import property as propmod


class _Owner:
    def __init__(self, name="O"):
        self.name = name


def test_board_initializes_without_type_errors():
    # White-box: Board creates Property objects; this must not crash.
    b = board.Board()
    assert len(b.properties) > 0


def test_board_get_tile_type_special_tile():
    b = board.Board()
    assert b.get_tile_type(0) == "go"


def test_board_get_tile_type_property_tile():
    b = board.Board()
    # Position 1 is a property in the list.
    assert b.get_tile_type(1) == "property"


def test_board_get_tile_type_blank_tile():
    b = board.Board()
    # Position 12 is not special and not a property in the board definition.
    assert b.get_tile_type(12) == "blank"


def test_board_is_purchasable_false_when_no_property():
    b = board.Board()
    assert b.is_purchasable(4) is False


def test_board_is_purchasable_false_when_mortgaged():
    b = board.Board()
    p = b.get_property_at(1)
    assert p is not None
    p.is_mortgaged = True
    assert b.is_purchasable(1) is False


def test_board_is_purchasable_false_when_owned():
    b = board.Board()
    p = b.get_property_at(1)
    p.owner = _Owner("A")
    assert b.is_purchasable(1) is False


def test_board_is_purchasable_true_when_unowned_and_not_mortgaged():
    b = board.Board()
    p = b.get_property_at(1)
    p.owner = None
    p.is_mortgaged = False
    assert b.is_purchasable(1) is True


def test_property_group_all_owned_by_requires_all_properties_owned_by_player():
    g = propmod.PropertyGroup("Test", "t")

    # Create two properties in same group.
    p1 = propmod.Property({"name": "A", "position": 1, "price": 10, "base_rent": 1}, g)
    p2 = propmod.Property({"name": "B", "position": 2, "price": 10, "base_rent": 1}, g)

    owner = _Owner("X")
    p1.owner = owner
    p2.owner = None

    assert g.all_owned_by(owner) is False

    p2.owner = owner
    assert g.all_owned_by(owner) is True


def test_property_group_all_owned_by_false_for_none_player_and_empty_group():
    g = propmod.PropertyGroup("Empty", "e")
    assert g.all_owned_by(None) is False
    assert g.all_owned_by(_Owner("X")) is False


def test_property_dict_constructor_with_explicit_group_kwarg():
    g = propmod.PropertyGroup("Test", "t")
    cfg = {"name": "A", "position": 1, "price": 10, "base_rent": 1}
    p = propmod.Property(cfg, group=g)
    assert p.group == g


def test_property_get_rent_doubles_when_full_group_owned():
    g = propmod.PropertyGroup("Test", "t")
    p1 = propmod.Property({"name": "A", "position": 1, "price": 10, "base_rent": 5}, g)
    p2 = propmod.Property({"name": "B", "position": 2, "price": 10, "base_rent": 5}, g)
    owner = _Owner("X")
    p1.owner = owner
    p2.owner = owner

    assert p1.get_rent() == 10


def test_property_get_rent_zero_when_mortgaged():
    g = propmod.PropertyGroup("Test", "t")
    p1 = propmod.Property({"name": "A", "position": 1, "price": 10, "base_rent": 5}, g)
    p1.is_mortgaged = True
    assert p1.get_rent() == 0


def test_property_get_rent_base_rent_when_group_not_fully_owned():
    g = propmod.PropertyGroup("Test", "t")
    p1 = propmod.Property({"name": "A", "position": 1, "price": 10, "base_rent": 5}, g)
    p2 = propmod.Property({"name": "B", "position": 2, "price": 10, "base_rent": 5}, g)
    owner = _Owner("X")
    p1.owner = owner
    p2.owner = None

    assert p1.get_rent() == 5


def test_property_mortgage_and_unmortgage_branches():
    g = propmod.PropertyGroup("Test", "t")
    p1 = propmod.Property({"name": "A", "position": 1, "price": 100, "base_rent": 5}, g)

    payout = p1.mortgage()
    assert payout == 50
    assert p1.is_mortgaged is True

    # second mortgage should return 0
    assert p1.mortgage() == 0

    cost = p1.unmortgage()
    assert cost == 55
    assert p1.is_mortgaged is False

    # second unmortgage should return 0
    assert p1.unmortgage() == 0


def test_property_is_available_false_when_owned_or_mortgaged():
    g = propmod.PropertyGroup("Test", "t")
    p1 = propmod.Property({"name": "A", "position": 1, "price": 10, "base_rent": 5}, g)

    assert p1.is_available() is True

    p1.owner = _Owner("X")
    assert p1.is_available() is False

    p1.owner = None
    p1.is_mortgaged = True
    assert p1.is_available() is False


def test_board_is_special_tile_true_and_false():
    b = board.Board()
    assert b.is_special_tile(0) is True
    assert b.is_special_tile(1) is False


def test_board_owned_and_unowned_helpers_and_repr():
    b = board.Board()
    owner = _Owner("X")
    p1 = b.get_property_at(1)
    p2 = b.get_property_at(3)
    assert p1 is not None and p2 is not None

    p1.owner = owner
    p2.owner = None

    owned = b.properties_owned_by(owner)
    assert p1 in owned
    assert p2 not in owned

    unowned = b.unowned_properties()
    assert p2 in unowned
    assert p1 not in unowned

    assert "Board(" in repr(b)


def test_property_positional_constructor_registers_group_and_repr():
    g = propmod.PropertyGroup("Test", "t")
    p = propmod.Property("Pos", 5, 100, 10, g)
    assert p in g.properties
    assert "Property(" in repr(p)


def test_property_group_add_property_and_counts_and_repr():
    g = propmod.PropertyGroup("Test", "t")
    p1 = propmod.Property("A", 1, 10, 1, None)
    p2 = propmod.Property("B", 2, 10, 1, None)
    p3 = propmod.Property("C", 3, 10, 1, None)
    owner = _Owner("X")
    p1.owner = owner
    p2.owner = owner
    p3.owner = None

    g.add_property(p1)
    g.add_property(p2)
    g.add_property(p1)  # duplicate add should be a no-op
    g.add_property(p3)

    counts = g.get_owner_counts()
    assert counts.get(owner) == 2
    assert None not in counts
    assert g.size() == 3
    assert "PropertyGroup(" in repr(g)
