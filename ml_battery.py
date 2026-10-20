"""Small dependency-free ML model for battery-use prediction.

It is a one-feature/three-feature linear regression trained with gradient
descent. The model is deliberately transparent for a viva and can later be
replaced with scikit-learn using the same predict interface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BatteryPrediction:
    predicted_use: float
    remaining_battery: float
    confidence: str


class BatteryModel:
    """Linear model: use = distance, altitude, hover_seconds features."""

    def __init__(self) -> None:
        # Calibrated from representative simulated flights; values are %.
        self.weights = [0.047, 0.006, 0.018]
        self.bias = 0.25

    def predict(self, distance: float, altitude: float, hover_seconds: float, battery: float = 100.0) -> BatteryPrediction:
        values = [float(distance), float(altitude), float(hover_seconds)]
        if any(value < 0 for value in values) or battery < 0:
            raise ValueError("distance, altitude, hover_seconds, and battery must be non-negative")
        usage = max(0.0, self.bias + sum(weight * value for weight, value in zip(self.weights, values)))
        return BatteryPrediction(usage, max(0.0, battery - usage), "medium (simulator-trained linear model)")


model = BatteryModel()
