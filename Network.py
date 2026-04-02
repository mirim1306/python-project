"""
클라이언트 WebSocket 네트워크 모듈
"""
import threading
import json
try:
    import websocket  # websocket-client 라이브러리
except ImportError:
    websocket = None

SERVER_URL = "ws://172.30.3.45:10000"


class NetworkClient:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.my_color = None
        self.game_started = False
        self.room_code = None

        self._thread = None
        self._incoming = []
        self._lock = threading.Lock()
        self._error = None

    def connect(self, url: str = SERVER_URL) -> bool:
        if websocket is None:
            self._error = "websocket-client 라이브러리가 없습니다. pip install websocket-client"
            return False
        try:
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            self._thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self._thread.start()

            # 연결 대기 (최대 10초)
            import time
            for _ in range(100):
                if self.connected:
                    return True
                if self._error:
                    return False
                time.sleep(0.1)
            self._error = "연결 시간 초과"
            return False
        except Exception as e:
            self._error = str(e)
            return False

    def _on_open(self, ws):
        self.connected = True
        print("[NET] 서버 연결 성공")

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
            with self._lock:
                self._incoming.append(msg)
        except Exception as e:
            print(f"[NET] 메시지 파싱 오류: {e}")

    def _on_error(self, ws, error):
        self._error = str(error)
        print(f"[NET] 오류: {error}")

    def _on_close(self, ws, code, msg):
        self.connected = False
        with self._lock:
            self._incoming.append({"type": "disconnected"})
        print("[NET] 연결 종료")

    def poll(self):
        with self._lock:
            msgs = self._incoming[:]
            self._incoming.clear()
        return msgs

    def send(self, data: dict):
        if self.connected and self.ws:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                print(f"[NET SEND ERROR] {e}")

    def quick_match(self):
        self.send({"type": "quick_match"})

    def create_room(self):
        self.send({"type": "create_room"})

    def join_room(self, code: str):
        self.send({"type": "join_room", "code": code.upper()})

    def send_move(self, start, end):
        self.send({"type": "move", "start": list(start), "end": list(end)})

    def send_promote(self, piece: str):
        self.send({"type": "promote", "piece": piece})

    def send_card_action(self, data: dict):
        data["type"] = "card_action"
        self.send(data)

    def disconnect(self):
        self.connected = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass