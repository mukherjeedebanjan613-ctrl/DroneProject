from tokens import Token, TokenType
class LexerError(Exception):
    """Raised when the lexer encounters invalid input."""
    pass
class Lexer:
    KEYWORDS = {
        # Mission
        "MISSION": TokenType.MISSION,
        "START": TokenType.START,
        "END": TokenType.END,

        # Configuration
        "HOME": TokenType.HOME,
        "BATTERY": TokenType.BATTERY,
        "RESERVE": TokenType.RESERVE,
        "SPEED": TokenType.SPEED,
        "MAX_ALTITUDE": TokenType.MAX_ALTITUDE,
        "MODE": TokenType.MODE,
        "ENERGY_SAVE": TokenType.ENERGY_SAVE,
        "NORMAL": TokenType.NORMAL,

        # Variables
        "SET": TokenType.SET,

        # Navigation
        "WAYPOINT": TokenType.WAYPOINT,
        "TAKEOFF": TokenType.TAKEOFF,
        "FLY": TokenType.FLY,
        "TO": TokenType.TO,
        "RETURN_HOME": TokenType.RETURN_HOME,
        "LAND": TokenType.LAND,
        "MOVE": TokenType.MOVE,
        "SET_ALTITUDE": TokenType.SET_ALTITUDE,
        "HOVER": TokenType.HOVER,

        # Geofence
        "NO_FLY_ZONE": TokenType.NO_FLY_ZONE,
        "RECTANGLE": TokenType.RECTANGLE,
        "END_ZONE": TokenType.END_ZONE,

        # Conditions
        "IF": TokenType.IF,
        "THEN": TokenType.THEN,
        "OBSTACLE": TokenType.OBSTACLE,
        "ALTITUDE": TokenType.ALTITUDE,
        "AVOID": TokenType.AVOID,
        "DESCEND": TokenType.DESCEND,

        # Values
        "TRUE": TokenType.TRUE,
        "FALSE": TokenType.FALSE,
        "LOST": TokenType.LOST,
        "CONNECTED": TokenType.CONNECTED,
    }
    def __init__(self, source):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1

    def current_char(self):
        """Return the current character."""
        if self.position >= len(self.source):
            return None

        return self.source[self.position]

    def peek_char(self):
        """Look one character ahead."""
        if self.position + 1 >= len(self.source):
            return None

        return self.source[self.position + 1]

    def advance(self):
        """Move to the next character."""
        char = self.current_char()

        if char is None:
            return

        self.position += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def skip_whitespace(self):
        """Skip spaces and tabs, but preserve newlines."""

        while True:
            char = self.current_char()

            if char in (" ", "\t", "\r"):
                self.advance()
            else:
                break

    def skip_comment(self):
        """Skip // comments."""
        if (
            self.current_char() == "/"
            and self.peek_char() == "/"
        ):
            while self.current_char() is not None:
                if self.current_char() == "\n":
                    break

                self.advance()

    def read_identifier(self):
        """Read an identifier or keyword."""

        start_line = self.line
        start_column = self.column

        value = ""

        while True:
            char = self.current_char()

            if char is None:
                break

            if char.isalnum() or char == "_":
                value += char
                self.advance()
            else:
                break

        # Check whether it is a keyword
        token_type = self.KEYWORDS.get(
            value.upper(),
            TokenType.IDENTIFIER
        )

        return Token(
            token_type,
            value,
            start_line,
            start_column
        )

    def read_number(self):
        """Read integer or decimal number."""

        start_line = self.line
        start_column = self.column

        value = ""

        decimal_found = False

        while True:
            char = self.current_char()

            if char is None:
                break

            if char.isdigit():
                value += char
                self.advance()

            elif char == "." and not decimal_found:
                decimal_found = True
                value += char
                self.advance()

            else:
                break

        if decimal_found:
            number_value = float(value)
        else:
            number_value = int(value)

        return Token(
            TokenType.NUMBER,
            number_value,
            start_line,
            start_column
        )

    def read_operator(self):
        """Read comparison or assignment operators."""

        start_line = self.line
        start_column = self.column

        char = self.current_char()
        next_char = self.peek_char()

        # Two-character operators
        if char == "=" and next_char == "=":
            self.advance()
            self.advance()

            return Token(
                TokenType.EQUAL,
                "==",
                start_line,
                start_column
            )

        if char == "!" and next_char == "=":
            self.advance()
            self.advance()

            return Token(
                TokenType.NOT_EQUAL,
                "!=",
                start_line,
                start_column
            )

        if char == "<" and next_char == "=":
            self.advance()
            self.advance()

            return Token(
                TokenType.LESS_EQUAL,
                "<=",
                start_line,
                start_column
            )

        if char == ">" and next_char == "=":
            self.advance()
            self.advance()

            return Token(
                TokenType.GREATER_EQUAL,
                ">=",
                start_line,
                start_column
            )

        # Single-character operators
        if char == "=":
            self.advance()

            return Token(
                TokenType.ASSIGN,
                "=",
                start_line,
                start_column
            )

        if char == "<":
            self.advance()

            return Token(
                TokenType.LESS_THAN,
                "<",
                start_line,
                start_column
            )

        if char == ">":
            self.advance()

            return Token(
                TokenType.GREATER_THAN,
                ">",
                start_line,
                start_column
            )
        raise LexerError(
            f"Unknown operator '{char}' "
            f"at line {start_line}, column {start_column}"
        )
    def tokenize(self):
        """Convert the entire source program into tokens."""

        tokens = []

        while self.current_char() is not None:

            # Whitespace
            if self.current_char() in (" ", "\t", "\r"):
                self.skip_whitespace()
                continue

            # Comments
            if (
                self.current_char() == "/"
                and self.peek_char() == "/"
            ):
                self.skip_comment()
                continue

            # Newline
            if self.current_char() == "\n":

                tokens.append(
                    Token(
                        TokenType.NEWLINE,
                        "\\n",
                        self.line,
                        self.column
                    )
                )

                self.advance()
                continue

            # Identifier / keyword
            if (
                self.current_char().isalpha()
                or self.current_char() == "_"
            ):
                tokens.append(
                    self.read_identifier()
                )
                continue

            # Number
            if self.current_char().isdigit():
                tokens.append(
                    self.read_number()
                )
                continue

            # Operators
            if self.current_char() in ("=", "<", ">", "!"):
                tokens.append(
                    self.read_operator()
                )
                continue

            # Unknown character
            raise LexerError(
                f"Unexpected character "
                f"'{self.current_char()}' "
                f"at line {self.line}, "
                f"column {self.column}"
            )
        # End of file
        tokens.append(
            Token(
                TokenType.EOF,
                None,
                self.line,
                self.column
            )
        )
        return tokens
