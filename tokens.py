from enum import Enum, auto
class TokenType(Enum):
    # Mission
    MISSION = auto()
    START = auto()
    END = auto()

    # Configuration
    HOME = auto()
    BATTERY = auto()
    RESERVE = auto()
    SPEED = auto()
    MAX_ALTITUDE = auto()

    # Variables
    SET = auto()

    # Navigation
    WAYPOINT = auto()
    TAKEOFF = auto()
    FLY = auto()
    TO = auto()
    RETURN_HOME = auto()
    LAND = auto()
    MOVE = auto()
    SET_ALTITUDE = auto()
    HOVER = auto()

    # Geofence
    NO_FLY_ZONE = auto()
    RECTANGLE = auto()
    END_ZONE = auto()

    # Conditions / Safety
    IF = auto()
    THEN = auto()
    OBSTACLE = auto()
    ALTITUDE = auto()
    AVOID = auto()
    DESCEND = auto()

    # Values
    TRUE = auto()
    FALSE = auto()
    LOST = auto()
    CONNECTED = auto()

    # Generic
    IDENTIFIER = auto()
    NUMBER = auto()

    # Operators
    ASSIGN = auto()       # =
    LESS_THAN = auto()    # <
    GREATER_THAN = auto() # >
    LESS_EQUAL = auto()   # <=
    GREATER_EQUAL = auto()# >=
    EQUAL = auto()        # ==
    NOT_EQUAL = auto()    # !=

    # Other
    NEWLINE = auto()
    EOF = auto()


class Token:
    def __init__(self, token_type, value, line, column):
        self.type = token_type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"Token("
            f"type={self.type.name}, "
            f"value={self.value!r}, "
            f"line={self.line}, "
            f"column={self.column})"
        )