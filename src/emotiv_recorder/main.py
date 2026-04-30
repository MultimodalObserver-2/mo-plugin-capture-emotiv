import json
import time
import sys
import os
from pathlib import Path
from typing import Callable, Any, List, Optional

from mo.core import load_metadata_json
from mo.modules.capture.plugins.capture_plugin import CaptureData, CapturePlugin

sys.path.insert(0, os.path.dirname(__file__))
from cortex_client import CortexClient
from emotiv_data import EmotivData


@load_metadata_json(rel_path="../..")
class EmotivCapturePlugin(CapturePlugin):

    def __init__(self):
        super().__init__()
        self.client = None
        self.file_path: Optional[Path] = None
        self.is_capturing = False
        self.is_paused = False
        self.on_data_callback: Optional[Callable[[CaptureData], None]] = None

    def load(self):
        self.is_capturing = False
        self.is_paused = False

    def unload(self):
        self.stop(0)

    def prepare(self, path: str, file_name: str):
        self.file_path = Path(path) / f"{file_name}.json"
        with open(self.file_path, 'w') as f:
            json.dump([], f, indent=2)

    def start(self, start_ts: float, get_timestamp: Callable[[], float], on_data: Callable[[CaptureData], None]):
        self.on_data_callback = on_data
        c_id = self.settings.get_setting("client_id") or ""
        c_secret = self.settings.get_setting("client_secret") or ""

        self.client = CortexClient(c_id, c_secret)
        
        self.client.add_listener(self.on_emotiv_data)
        
        self.is_capturing = True
        self.is_paused = False
        self.client.connect()

        while self.is_capturing:
            time.sleep(0.1)

    def stop(self, stop_ts: float):
        self.is_capturing = False
        if self.client:
            self.client.disconnect()
            self.client = None

    def pause(self, pause_ts: float):
        if self.is_capturing:
            self.is_paused = True

    def resume(self, resume_ts: float):
        if self.is_capturing:
            self.is_paused = False

    def save(self, data: List[CaptureData], end_of_data: bool = False):
        if not self.file_path or not data:
            return

        existing_data = []
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

        new_data = [item.data for item in data]
        existing_data.extend(new_data)

        with open(self.file_path, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)

    def on_emotiv_data(self, data: EmotivData) -> None:
        if self.is_capturing and not self.is_paused and self.on_data_callback:
            data_dict = {
                "timestamp": data.timestamp,
                "metrics": {
                    "stress": data.metrics.stress,
                    "engagement": data.metrics.engagement,
                    "interest": data.metrics.interest,
                    "excitement": data.metrics.excitement,
                    "focus": data.metrics.focus,
                    "relaxation": data.metrics.relaxation
                },
                "power": {
                    "theta": data.power.theta,
                    "alpha": data.power.alpha,
                    "low_beta": data.power.low_beta,
                    "high_beta": data.power.high_beta,
                    "gamma": data.power.gamma
                },
                "status": {
                    "battery": getattr(data, 'battery_level', 0),
                    "headset": getattr(data, 'headset_id', 'unknown')
                }
            }
            capture_data = CaptureData(timestamp=data.timestamp, data=data_dict)
            self.on_data_callback(capture_data)
    
    def get_file_extension(self) -> str:
        return "json"
    
    def get_output_descriptor(self) -> dict[str, Any] | None:
        return {"type": "object", 
                "properties": {"metrics": {"type": "object"}, 
                               "power": {"type": "object"}}}