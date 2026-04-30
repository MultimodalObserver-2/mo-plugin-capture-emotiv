import json
import threading
import time
import ssl
import websocket
from typing import Callable, Optional, List
from emotiv_data import EmotivData

class CortexClient:

    def __init__(self, client_id: str, client_secret: str):
        self.ws_url = "wss://localhost:6868"
        self.client_id = client_id
        self.client_secret = client_secret
        self.ws: Optional[websocket.WebSocketApp] = None
        self.listeners: List[Callable[[EmotivData], None]] = []    
        self.is_connected = False
        self.auth_token = None
        self.session_id = None
        self.headset_id = None 
        self.thread: Optional[threading.Thread] = None
        self.should_run = False
        self.request_id = 1
        self.latest_data = EmotivData()
        
    def add_listener(self, listener: Callable[[EmotivData], None]):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def connect(self):
        self.should_run = True
        self.thread = threading.Thread(target=self.run_ws, daemon=True)
        self.thread.start()

    def disconnect(self):
        self.should_run = False
        if self.ws:
            self.ws.close()
        self.is_connected = False
        if self.thread and self.thread.is_alive():
             self.thread.join(timeout=1.0)

    def run_ws(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def send_json(self, method: str, params: dict):
        if not self.ws or not self.ws.sock or not self.ws.sock.connected: 
            return
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        self.request_id += 1
        try:
            self.ws.send(json.dumps(payload))
        except Exception:
            pass

    def on_open(self, ws):
        self.is_connected = True
        self.send_json("requestAccess", {
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        })

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        if "result" in data:
            res = data["result"]
            
            if isinstance(res, dict) and res.get("accessGranted"):
                self.send_json("authorize", {
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret
                })
            
            elif isinstance(res, dict) and "cortexToken" in res:
                self.auth_token = res["cortexToken"]
                self.send_json("queryHeadsets", {})

            elif isinstance(res, list): 
                found_id = None
                for h in res:
                    status = h.get("status")
                    hid = h.get("id")
                    if status == "connected":
                        found_id = hid
                        break 
                
                if found_id:
                    self.headset_id = found_id
                    self.send_json("createSession", {
                        "cortexToken": self.auth_token,
                        "headset": self.headset_id,
                        "status": "active"
                    })
                else:
                    time.sleep(3)
                    self.send_json("queryHeadsets", {})

            elif isinstance(res, dict) and "id" in res and "appId" in res:
                self.session_id = res["id"]
                streams = ["met", "pow", "sys"] 
                self.send_json("subscribe", {
                    "cortexToken": self.auth_token,
                    "session": self.session_id,
                    "streams": streams
                })

        if "sid" in data: 
            self.process_stream_data(data)

    def process_stream_data(self, data):
        try:
            self.latest_data.timestamp = data.get("time", time.time())
            
            should_emit = False
            if "met" in data:
                met = data["met"]
                if len(met) >= 6:
                    for field, val in zip(['engagement', 'excitement', 'stress', 'relaxation', 'interest', 'focus'], met):
                        setattr(self.latest_data.metrics, field, val if val is not None else 0.0)
                    should_emit = True

            if "pow" in data:
                p = data["pow"]
                if len(p) >= 5:
                    for field, val in zip(['theta', 'alpha', 'low_beta', 'high_beta', 'gamma'], p):
                        setattr(self.latest_data.power, field, val if val is not None else 0.0)
                    should_emit = True

            if should_emit:
                # CREA COPIA DE LOS DATOS CAPTURADOS PARA NO PERDERLOS EN EL PROCESO
                packet_to_send = EmotivData()
                packet_to_send.timestamp = self.latest_data.timestamp

                packet_to_send.metrics.engagement = self.latest_data.metrics.engagement
                packet_to_send.metrics.excitement = self.latest_data.metrics.excitement
                packet_to_send.metrics.stress = self.latest_data.metrics.stress
                packet_to_send.metrics.relaxation = self.latest_data.metrics.relaxation
                packet_to_send.metrics.interest = self.latest_data.metrics.interest
                packet_to_send.metrics.focus = self.latest_data.metrics.focus

                packet_to_send.power.theta = self.latest_data.power.theta
                packet_to_send.power.alpha = self.latest_data.power.alpha
                packet_to_send.power.low_beta = self.latest_data.power.low_beta
                packet_to_send.power.high_beta = self.latest_data.power.high_beta
                packet_to_send.power.gamma = self.latest_data.power.gamma

                for listener in self.listeners:
                    listener(packet_to_send)
                    
        except Exception:
            pass

    def on_error(self, ws, error):
        pass

    def on_close(self, ws, close_status_code, close_msg):
        pass