from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class EmotivMetrics:

    stress: float = 0.0
    engagement: float = 0.0
    interest: float = 0.0
    excitement: float = 0.0
    focus: float = 0.0
    relaxation: float = 0.0

    def __str__(self) -> str:
        return (f"str:{self.stress} eng:{self.engagement} int:{self.interest}"
                f"exc:{self.excitement} foc:{self.focus} rel:{self.relaxation}")
    

@dataclass
class EmotivPower:

    theta: float = 0.0
    alpha: float = 0.0
    low_beta: float = 0.0
    high_beta: float = 0.0
    gamma: float = 0.0

@dataclass
class EmotivData:
    timestamp: float = 0.0
    metrics: EmotivMetrics = field(default_factory=EmotivMetrics)
    power: EmotivPower = field(default_factory=EmotivPower)
    battery_level: int = 0
    signal_quality: int = 0
    headset_id: str = ""
    status: Optional[str] = None

    def __str__(self) -> str:
        return (f"Time:{self.timestamp} | Bat:{self.battery_level}% | "
                f"Metrics[{self.metrics}] | Pow[{self.power}]")
 