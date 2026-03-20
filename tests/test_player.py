import pytest

import config
import player


def test_player_add_money_increases_balance():
    # Arrange
    p = player.Player("A")
    start = p.balance

    # Act
    p.add_money(10)

    # Assert
    assert p.balance == start + 10


def test_player_add_money_negative_raises_value_error():
    # CFG: add_money -> amount < 0 (True branch)
    p = player.Player("A")
    with pytest.raises(ValueError):
        p.add_money(-1)


def test_player_deduct_money_decreases_balance():
    # Arrange
    p = player.Player("A")
    start = p.balance

    # Act
    p.deduct_money(10)

    # Assert
    assert p.balance == start - 10


def test_player_deduct_money_negative_raises_value_error():
    # CFG: deduct_money -> amount < 0 (True branch)
    p = player.Player("A")
    with pytest.raises(ValueError):
        p.deduct_money(-1)


def test_player_is_bankrupt_false_when_positive_balance():
    p = player.Player("A")
    p.balance = 1
    assert p.is_bankrupt() is False


def test_player_is_bankrupt_true_when_zero_balance():
    p = player.Player("A")
    p.balance = 0
    assert p.is_bankrupt() is True


def test_player_move_lands_on_go_awards_salary():
    # CFG: move -> if self.position == 0 after move (True branch)
    p = player.Player("A")
    p.position = config.BOARD_SIZE - 1
    start = p.balance

    p.move(1)

    assert p.position == 0
    assert p.balance == start + config.GO_SALARY


def test_player_move_not_on_go_does_not_award_salary():
    # CFG: move -> if self.position == 0 after move (False branch)
    p = player.Player("A")
    p.position = 0
    start = p.balance

    p.move(1)

    assert p.position == 1
    assert p.balance == start


def test_player_move_passing_go_awards_salary():
    # Edge-case CFG: move wraps around (passing Go) should award salary.
    p = player.Player("A")
    p.position = config.BOARD_SIZE - 1
    start = p.balance

    p.move(2)

    assert p.position == 1
    assert p.balance == start + config.GO_SALARY


def test_player_go_to_jail_sets_position_and_jail_state():
    p = player.Player("A")
    p.go_to_jail()
    assert p.position == config.JAIL_POSITION
    assert p.jail["in_jail"] is True
    assert p.jail["turns"] == 0


def test_player_exposes_jail_state_via_attributes():
    # White-box: Game uses player.in_jail/player.jail_turns/player.get_out_of_jail_cards.
    p = player.Player("A")

    assert p.in_jail is False
    assert p.jail_turns == 0
    assert p.get_out_of_jail_cards == 0

    p.in_jail = True
    p.jail_turns = 2
    p.get_out_of_jail_cards = 1

    assert p.jail["in_jail"] is True
    assert p.jail["turns"] == 2
    assert p.jail["get_out_of_jail_cards"] == 1


def test_player_status_line_has_jailed_tag_when_jailed():
    p = player.Player("A")
    p.go_to_jail()
    assert "[JAILED]" in p.status_line()


def test_player_status_line_no_jailed_tag_when_not_jailed():
    p = player.Player("A")
    assert "[JAILED]" not in p.status_line()


def test_player_add_property_adds_once_and_remove_property_removes():
    p = player.Player("A")
    prop = object()

    p.add_property(prop)
    p.add_property(prop)
    assert p.count_properties() == 1

    p.remove_property(prop)
    assert p.count_properties() == 0


def test_player_remove_property_when_absent_no_change():
    # CFG: remove_property -> if prop in self.properties (False branch)
    p = player.Player("A")
    missing = object()
    p.remove_property(missing)
    assert p.count_properties() == 0


def test_player_net_worth_equals_balance():
    p = player.Player("A")
    p.balance = 123
    assert p.net_worth() == 123


def test_player_repr_contains_name():
    p = player.Player("A")
    assert "Player(" in repr(p)
    assert "A" in repr(p)
