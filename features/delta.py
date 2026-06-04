"""Delta velocity and acceleration."""


class DeltaEngine:
    def __init__(self) -> None:
        self.previous_cvd: float | None = None
        self.previous_velocity: float | None = None

    def update(self, cvd: float) -> dict[str, float]:
        velocity = 0.0 if self.previous_cvd is None else cvd - self.previous_cvd
        acceleration = (
            0.0 if self.previous_velocity is None else velocity - self.previous_velocity
        )
        self.previous_cvd = cvd
        self.previous_velocity = velocity
        return {"velocity": velocity, "acceleration": acceleration}

    def reset(self) -> None:
        self.previous_cvd = None
        self.previous_velocity = None
