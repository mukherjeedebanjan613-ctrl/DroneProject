"""Small, local execution target for generated AeroSafeX simulator code."""

from dataclasses import dataclass, field
from math import hypot
from time import sleep


@dataclass
class DroneSimulator:
    position: tuple[float, float] = (0, 0)
    altitude: float = 0
    airborne: bool = False
    initial_battery: float = 100.0
    flight_mode: str = "NORMAL"
    battery_level: float = 100.0
    mission_status: str = "PENDING"
    flight_state: str = "LANDED"
    animation_steps: int = 8
    step_delay: float = 0.08
    events: list[str] = field(default_factory=list)
    flight_trace: list[tuple[float, float, float, float]] = field(default_factory=list)

    BATTERY_PER_DISTANCE = 0.05
    ENERGY_SAVE_BATTERY_PER_DISTANCE = 0.035

    def __post_init__(self) -> None:
        self.battery_level = self.initial_battery

    @property
    def x(self) -> float:
        """Current horizontal X coordinate."""
        return self.position[0]

    @property
    def y(self) -> float:
        """Current horizontal Y coordinate."""
        return self.position[1]

    def start_mission(self) -> None:
        self.mission_status = "RUNNING"
        self.flight_trace.append((self.x, self.y, self.altitude, self.battery_level))
        print("[SIM] Mission started")

    def takeoff(self, altitude: float) -> None:
        self.airborne = True
        self.flight_state = "AIRBORNE"
        self.altitude = altitude
        self.events.append(f"TAKEOFF {altitude}")
        print(f"[SIM] TAKEOFF -> altitude {altitude}")

    def move_to(self, x: float, y: float, altitude: float) -> None:
        if not self.airborne:
            raise RuntimeError("Cannot move before takeoff")
        start_x, start_y = self.position
        start_altitude = self.altitude
        distance = hypot(x - start_x, y - start_y)
        rate = (
            self.ENERGY_SAVE_BATTERY_PER_DISTANCE
            if self.flight_mode == "ENERGY_SAVE"
            else self.BATTERY_PER_DISTANCE
        )
        battery_cost = distance * rate
        # Energy-saving mode represents slower, smoother movement. The route
        # and altitude remain unchanged; only execution efficiency changes.
        steps = self.animation_steps * (2 if self.flight_mode == "ENERGY_SAVE" else 1)

        print(f"[SIM] MOVE -> ({x}, {y}, {altitude})")
        for step in range(1, steps + 1):
            progress = step / steps
            self.position = (
                start_x + (x - start_x) * progress,
                start_y + (y - start_y) * progress,
            )
            self.altitude = start_altitude + (altitude - start_altitude) * progress
            self.battery_level = max(0.0, self.battery_level - battery_cost / steps)
            self.flight_trace.append((self.x, self.y, self.altitude, self.battery_level))
            print(
                f"[SIM]   position=({self.x:.1f}, {self.y:.1f}, {self.altitude:.1f}) "
                f"battery={self.battery_level:.1f}%"
            )
            if self.step_delay > 0:
                sleep(self.step_delay)

        # Keep mission coordinates exact after the interpolated updates.
        self.position = (x, y)
        self.altitude = altitude
        self.events.append(f"MOVE {x} {y} {altitude}")

    def set_altitude(self, altitude: float) -> None:
        if not self.airborne:
            raise RuntimeError("Cannot change altitude before takeoff")
        self.altitude = altitude
        self.events.append(f"SET_ALTITUDE {altitude}")
        print(f"[SIM] SET_ALTITUDE -> {altitude}")

    def hover(self, seconds: float) -> None:
        self.events.append(f"HOVER {seconds}")
        print(f"[SIM] HOVER -> {seconds}s")

    def avoid(self) -> None:
        self.events.append("AVOID")
        print("[SIM] AVOID")

    def land(self) -> None:
        if not self.airborne:
            raise RuntimeError("Cannot land before takeoff")
        self.airborne = False
        self.flight_state = "LANDED"
        self.altitude = 0
        self.events.append("LAND")
        print("[SIM] LAND")

    def complete_mission(self) -> None:
        if self.airborne:
            raise RuntimeError("Mission cannot complete while drone is airborne")
        self.mission_status = "COMPLETED"

    def fail_mission(self) -> None:
        """Record a failed local simulation without affecting real hardware."""
        self.mission_status = "FAILED"

    def summary(self) -> str:
        return (
            "=" * 60
            + "\nSIMULATION COMPLETE\n"
            + "=" * 60
            + f"\nFinal Position : {self.position}"
            + f"\nFinal Altitude : {self.altitude}"
            + f"\nBattery        : {self.battery_level:.1f}%"
            + f"\nMission Status : {self.mission_status}"
            + f"\nFlight State   : {self.flight_state}"
            + "\n" + "=" * 60
        )
if __name__ == "__main__":
    drone = DroneSimulator()

    drone.takeoff(50)
    drone.move_to(100, 100, 50)
    drone.move_to(200, 200, 50)
    drone.move_to(250, 300, 50)
    drone.move_to(0, 0, 50)
    drone.land()

    print(drone.summary())
