"""
체스 카드 게임 WebSocket 서버
Render.com 배포용
실행: python server.py
"""
import asyncio
import websockets
import json
import random
import string
import os

PORT = int(os.environ.get("PORT", 10000))

# 빠른 매칭 대기열
quick_queue = []

# 방 목록: {code: {"players": [ws1], "event": asyncio.Event}}
rooms = {}


def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


async def send(ws, data):
    try:
        await ws.send(json.dumps(data))
    except Exception as e:
        print(f"[SEND ERROR] {e}")


async def relay(ws1, ws2):
    """두 클라이언트 사이에서 메시지 중계."""
    async def forward(src, dst):
        try:
            async for message in src:
                await dst.send(message)
        except Exception:
            pass
        finally:
            try:
                await send(dst, {"type": "opponent_disconnected"})
            except Exception:
                pass

    await asyncio.gather(
        forward(ws1, ws2),
        forward(ws2, ws1)
    )


async def start_game(ws1, ws2):
    await send(ws1, {"type": "game_start", "color": "w"})
    await send(ws2, {"type": "game_start", "color": "b"})
    print("[GAME] 게임 시작")
    await relay(ws1, ws2)


async def handler(ws):
    print(f"[CONNECT] {ws.remote_address}")
    try:
        raw = await ws.recv()
        msg = json.loads(raw)
        action = msg.get("type")

        # ── 빠른 매칭 ──────────────────────────────────────────────────
        if action == "quick_match":
            await send(ws, {"type": "waiting", "message": "상대방을 기다리는 중..."})
            quick_queue.append(ws)
            if len(quick_queue) >= 2:
                p1 = quick_queue.pop(0)
                p2 = quick_queue.pop(0)
                await start_game(p1, p2)
            else:
                # 상대방이 올 때까지 연결 유지
                try:
                    async for _ in ws:
                        pass
                except Exception:
                    pass
                finally:
                    if ws in quick_queue:
                        quick_queue.remove(ws)

        # ── 방 만들기 ───────────────────────────────────────────────────
        elif action == "create_room":
            code = gen_code()
            while code in rooms:
                code = gen_code()
            event = asyncio.Event()
            rooms[code] = {"players": [ws], "event": event}
            await send(ws, {"type": "room_created", "code": code})
            print(f"[ROOM] 방 생성: {code}")

            # 상대방이 참가할 때까지 대기
            await event.wait()

            if code in rooms and len(rooms[code]["players"]) == 2:
                p1, p2 = rooms.pop(code)["players"]
                await start_game(p1, p2)

        # ── 방 참가 ────────────────────────────────────────────────────
        elif action == "join_room":
            code = msg.get("code", "").upper()
            if code not in rooms:
                await send(ws, {"type": "error", "message": "방을 찾을 수 없습니다."})
                return
            if len(rooms[code]["players"]) >= 2:
                await send(ws, {"type": "error", "message": "방이 가득 찼습니다."})
                return
            rooms[code]["players"].append(ws)
            await send(ws, {"type": "room_joined", "code": code})
            print(f"[ROOM] 방 참가: {code}")
            rooms[code]["event"].set()  # 방 만든 쪽 깨우기

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        # 대기열에서 제거
        if ws in quick_queue:
            quick_queue.remove(ws)
        print(f"[DISCONNECT] {ws.remote_address}")


async def main():
    print(f"[SERVER] 시작됨 — 0.0.0.0:{PORT}")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # 영구 실행


if __name__ == "__main__":
    asyncio.run(main())