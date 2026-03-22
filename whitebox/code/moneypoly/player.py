"""Module defining the Player class,
 which represents a single player in the Monopoly game."""
from .config import STARTING_BALANCE, BOARD_SIZE, GO_SALARY, JAIL_POSITION

class Player:
    """Represents a single player in a MoneyPoly game."""

    def __init__(self, name, balance=STARTING_BALANCE):
        self.name = name
        self.balance = balance
        self.position = 0
        self.properties = []
        self.is_eliminated = False
        self.jail={
            "in_jail": False,
            "turns": 0,
            "get_out_of_jail_cards": 0
        }

    @property
    def in_jail(self):
        """Compatibility attribute for game logic (mirrors jail['in_jail'])."""
        return bool(self.jail.get("in_jail", False))

    @in_jail.setter
    def in_jail(self, value):
        self.jail["in_jail"] = bool(value)

    @property
    def jail_turns(self):
        """Compatibility attribute for game logic (mirrors jail['turns'])."""
        return int(self.jail.get("turns", 0))

    @jail_turns.setter
    def jail_turns(self, value):
        self.jail["turns"] = int(value)

    @property
    def get_out_of_jail_cards(self):
        """Compatibility attribute for game logic (mirrors jail['get_out_of_jail_cards'])."""
        return int(self.jail.get("get_out_of_jail_cards", 0))

    @get_out_of_jail_cards.setter
    def get_out_of_jail_cards(self, value):
        self.jail["get_out_of_jail_cards"] = int(value)


    def add_money(self, amount):
        """Add funds to this player's balance. Amount must be non-negative."""
        if amount < 0:
            raise ValueError(f"Cannot add a negative amount: {amount}")
        self.balance += amount

    def deduct_money(self, amount):
        """Deduct funds from this player's balance. Amount must be non-negative."""
        if amount < 0:
            raise ValueError(f"Cannot deduct a negative amount: {amount}")
        self.balance -= amount

    def is_bankrupt(self):
        """Return True if this player has no money remaining."""
        return self.balance <= 0

    def net_worth(self):
        """Calculate and return this player's total net worth."""
        return self.balance

    def move(self, steps):
        """
        Move this player forward by `steps` squares, wrapping around the board.
        Awards the Go salary if the player passes or lands on Go.
        Returns the new board position.
        """
        old_pos = self.position
        raw_pos = old_pos + steps
        self.position = raw_pos % BOARD_SIZE

        # Salary is awarded when passing (or landing on) Go.
        if steps > 0 and raw_pos >= BOARD_SIZE:
            passes = raw_pos // BOARD_SIZE
            self.add_money(GO_SALARY * passes)
            if self.position == 0:
                print(
                    f"  {self.name} landed on Go and collected ${GO_SALARY * passes}."
                )
            else:
                print(
                    f"  {self.name} passed Go and collected ${GO_SALARY * passes}."
                )

        return self.position

    def go_to_jail(self):
        """Send this player directly to the Jail square."""
        self.position = JAIL_POSITION
        self.jail["in_jail"] = True
        self.jail["turns"] = 0


    def add_property(self, prop):
        """Add a property tile to this player's holdings."""
        if prop not in self.properties:
            self.properties.append(prop)

    def remove_property(self, prop):
        """Remove a property tile from this player's holdings."""
        if prop in self.properties:
            self.properties.remove(prop)

    def count_properties(self):
        """Return the number of properties this player currently owns."""
        return len(self.properties)


    def status_line(self):
        """Return a concise one-line status string for this player."""
        jail_tag = " [JAILED]" if self.jail["in_jail"] else ""
        return (
            f"{self.name}: ${self.balance}  "
            f"pos={self.position}  "
            f"props={len(self.properties)}"
            f"{jail_tag}"
        )

    def __repr__(self):
        return f"Player({self.name!r}, balance={self.balance}, pos={self.position})"
    