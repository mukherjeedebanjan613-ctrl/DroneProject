"""Parser for the AeroSafeX mission language.

Grammar (one statement per line):
    program       -> MISSION START NEWLINE* statement* MISSION END EOF
    statement     -> configuration | SET assignment | WAYPOINT point
                   | NO_FLY_ZONE name NEWLINE RECTANGLE bounds NEWLINE END_ZONE
                   | IF condition NEWLINE THEN command | command
    condition     -> value comparison value
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from tokens import Token, TokenType
class ParserError(Exception):
    """Raised when a valid token stream does not match the mission grammar."""
@dataclass
class Condition:
    left: Any
    operator: str
    right: Any
@dataclass
class Command:
    name: str
    arguments: list[Any] = field(default_factory=list)
@dataclass
class Mission:
    configuration: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    waypoints: dict[str, tuple[float, float]] = field(default_factory=dict)
    waypoint_declarations: list[tuple[str, tuple[float, float]]] = field(default_factory=list)
    no_fly_zones: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)
    safety_rules: list[tuple[Condition, Command]] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)


class Parser:
    CONFIGURATION = {
        TokenType.HOME: ("HOME", 2),
        TokenType.BATTERY: ("BATTERY", 1),
        TokenType.RESERVE: ("RESERVE", 1),
        TokenType.SPEED: ("SPEED", 1),
        TokenType.MAX_ALTITUDE: ("MAX_ALTITUDE", 1),
        TokenType.MODE: ("MODE", 1),
    }
    COMMAND_ARGUMENTS = {
        TokenType.TAKEOFF: 1,
        TokenType.FLY: 2,  # TO <waypoint>
        TokenType.RETURN_HOME: 0,
        TokenType.LAND: 0,
        TokenType.MOVE: 2,
        TokenType.SET_ALTITUDE: 1,
        TokenType.HOVER: 1,
        TokenType.AVOID: 0,
        TokenType.DESCEND: 1,
    }
    COMPARISONS = {
        TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS_THAN,
        TokenType.LESS_EQUAL, TokenType.GREATER_THAN, TokenType.GREATER_EQUAL,
    }
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0
    @property
    def current(self) -> Token:
        return self.tokens[self.position]
    def advance(self) -> Token:
        token = self.current
        if token.type is not TokenType.EOF:
            self.position += 1
        return token
    def expect(self, token_type: TokenType) -> Token:
        if self.current.type is not token_type:
            raise ParserError(
                f"Expected {token_type.name}, found {self.current.type.name} "
                f"at line {self.current.line}, column {self.current.column}"
            )
        return self.advance()
    def consume_newlines(self) -> None:
        while self.current.type is TokenType.NEWLINE:
            self.advance()
    def value(self) -> Any:
        token = self.current
        if token.type in (TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.ENERGY_SAVE, TokenType.NORMAL):
            self.advance()
            return token.value
        if token.type in (TokenType.BATTERY, TokenType.OBSTACLE, TokenType.ALTITUDE):
            self.advance()
            return token.value
        if token.type is TokenType.TRUE:
            self.advance()
            return True
        if token.type is TokenType.FALSE:
            self.advance()
            return False
        if token.type in (TokenType.LOST, TokenType.CONNECTED):
            self.advance()
            return token.value
        raise ParserError(
            f"Expected a value at line {token.line}, column {token.column}"
        )
    def parse(self) -> Mission:
        mission = Mission()
        self.expect(TokenType.MISSION)
        self.expect(TokenType.START)
        self.consume_newlines()

        while self.current.type is not TokenType.EOF:
            if self.current.type is TokenType.MISSION:
                self.advance()
                self.expect(TokenType.END)
                self.consume_newlines()
                self.expect(TokenType.EOF)
                return mission
            self.parse_statement(mission)
            self.consume_newlines()
        raise ParserError("Expected 'MISSION END' before end of file")
    def parse_statement(self, mission: Mission) -> None:
        token_type = self.current.type
        if token_type in self.CONFIGURATION:
            name, argument_count = self.CONFIGURATION[token_type]
            self.advance()
            values = [self.value() for _ in range(argument_count)]
            mission.configuration[name] = tuple(values) if argument_count > 1 else values[0]
        elif token_type is TokenType.SET:
            self.advance()
            name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.ASSIGN)
            mission.variables[name] = self.value()
        elif token_type is TokenType.WAYPOINT:
            self.advance()
            name = self.expect(TokenType.IDENTIFIER).value
            coordinates = (self.number(), self.number())
            mission.waypoints[name] = coordinates
            mission.waypoint_declarations.append((name, coordinates))
        elif token_type is TokenType.NO_FLY_ZONE:
            self.parse_no_fly_zone(mission)
        elif token_type is TokenType.IF:
            self.parse_safety_rule(mission)
        elif token_type in self.COMMAND_ARGUMENTS:
            mission.commands.append(self.parse_command())
        else:
            raise ParserError(
                f"Unexpected {self.current.type.name} at line {self.current.line}, "
                f"column {self.current.column}"
            )
    def number(self) -> float:
        return self.expect(TokenType.NUMBER).value
    def parse_no_fly_zone(self, mission: Mission) -> None:
        self.expect(TokenType.NO_FLY_ZONE)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.RECTANGLE)
        bounds = tuple(self.number() for _ in range(4))
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.END_ZONE)
        mission.no_fly_zones[name] = bounds
    def parse_safety_rule(self, mission: Mission) -> None:
        self.expect(TokenType.IF)
        condition = Condition(
            left=self.value(),
            operator=self.parse_comparison(),
            right=self.value(),
        )
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.THEN)
        mission.safety_rules.append((condition, self.parse_command()))
    def parse_comparison(self) -> str:
        if self.current.type not in self.COMPARISONS:
            raise ParserError(
                f"Expected comparison operator at line {self.current.line}, "
                f"column {self.current.column}"
            )
        return self.advance().value
    def parse_command(self) -> Command:
        command_token = self.current
        if command_token.type not in self.COMMAND_ARGUMENTS:
            raise ParserError(
                f"Expected command at line {command_token.line}, column {command_token.column}"
            )
        self.advance()
        if command_token.type is TokenType.FLY:
            self.expect(TokenType.TO)
            arguments = [self.value()]
        else:
            arguments = [self.value() for _ in range(self.COMMAND_ARGUMENTS[command_token.type])]
        return Command(command_token.value, arguments)
