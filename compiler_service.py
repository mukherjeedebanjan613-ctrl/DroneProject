"""Shared AeroSafeX compilation service for local interfaces."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from typing import Any

from code_generator import CodeGenerator
from ir import IRGenerator
from ir_optimizer import IROptimizer
from lexer import Lexer, LexerError
from parser import Parser, ParserError
from safety_analyzer import SafetyAnalyzer
from semantic_analyzer import SemanticAnalyzer, SemanticError


def compile_source(source: str) -> dict[str, Any]:
    """Run the existing compiler pipeline and return UI-ready mission data."""
    try:
        tokens = Lexer(source).tokenize()
        mission = Parser(tokens).parse()
    except (LexerError, ParserError) as error:
        return {"status": "REJECTED", "stage": "Syntax", "error": str(error)}

    try:
        symbols = SemanticAnalyzer(mission).analyze()
    except SemanticError as error:
        return {"status": "REJECTED", "stage": "Semantic", "error": str(error)}

    report = SafetyAnalyzer(mission).analyze()
    base = {
        "tokens": len(tokens),
        "waypoints": mission.waypoints,
        "zones": mission.no_fly_zones,
        "home": mission.configuration.get("HOME"),
        "variables": mission.variables,
        "route": report.route,
        "distance": report.distance,
        "estimated_battery_used": report.estimated_battery_used,
        "issues": [{"level": item.level.value, "message": item.message} for item in report.issues],
        "symbol_count": {"waypoints": len(symbols.waypoints), "variables": len(symbols.variables)},
    }
    if not report.is_safe:
        return {**base, "status": "REJECTED", "stage": "Safety", "error": "Mission execution blocked by safety analysis."}

    ir_program = IRGenerator(mission).generate()
    optimization = IROptimizer().optimize(ir_program)
    generated_code = CodeGenerator(optimization.program).generate()
    namespace: dict[str, Any] = {}
    try:
        with redirect_stdout(StringIO()) as simulator_log:
            exec(generated_code, namespace)
    except (RuntimeError, ValueError) as error:
        return {**base, "status": "FAILED", "stage": "Simulation", "error": str(error)}

    drone = namespace["drone"]
    return {
        **base,
        "status": "COMPLETED",
        "stage": "Simulation",
        "ir": str(optimization.program),
        "generated_code": generated_code,
        "optimizations": optimization.changes,
        "simulator_log": simulator_log.getvalue(),
        "drone": {
            "position": drone.position,
            "altitude": drone.altitude,
            "battery": drone.battery_level,
            "mission_status": drone.mission_status,
            "flight_state": drone.flight_state,
            "trace": drone.flight_trace,
        },
    }
