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

quick_queue = []

# 방 목록: {code: {"players": [ws], "event": Event}}
rooms = {}


def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


async def send(ws, data):
    try:
        await ws.send(json.dumps(data))
    except Exception as e:
        print(f"[SEND ERROR] {e}")


async def forward(src, dst):
    """src → dst 단방향 메시지 중계."""
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

            # 상대방이 올 때까지 대기
            while ws in quick_queue:
                await asyncio.sleep(0.3)
                if len(quick_queue) >= 2:
                    p1 = quick_queue.pop(0)
                    p2 = quick_queue.pop(0)
                    await send(p1, {"type": "game_start", "color": "w"})
                    await send(p2, {"type": "game_start", "color": "b"})
                    print("[GAME] 빠른매칭 게임 시작")
                    # 각 핸들러가 한 방향씩 담당
                    if ws is p1:
                        await forward(p1, p2)
                    else:
                        await forward(p2, p1)
                    break

        # ── 방 만들기 ───────────────────────────────────────────────────
        elif action == "create_room":
            code = gen_code()
            while code in rooms:
                code = gen_code()
            event = asyncio.Event()
            rooms[code] = {"players": [ws], "event": event}
            await send(ws, {"type": "room_created", "code": code})
            print(f"[ROOM] 방 생성: {code}")

            # 상대방 참가 대기
            await event.wait()

            room = rooms.pop(code, None)
            if room and len(room["players"]) == 2:
                p1, p2 = room["players"]
                await send(p1, {"type": "game_start", "color": "w"})
                await send(p2, {"type": "game_start", "color": "b"})
                print("[GAME] 방 게임 시작")
                # create 핸들러: p1 → p2 방향
                await forward(p1, p2)

        # ── 방 참가 ────────────────────────────────────────────────────
        elif action == "join_room":
            code = msg.get("code", "").upper()
            if code not in rooms:
                await send(ws, {"type": "error", "message": "방을 찾을 수 없습니다."})
                return
            if len(rooms[code]["players"]) >= 2:
                await send(ws, {"type": "error", "message": "방이 가득 찼습니다."})
                return

            p1 = rooms[code]["players"][0]  # event.set() 전에 p1 저장
            rooms[code]["players"].append(ws)
            await send(ws, {"type": "room_joined", "code": code})
            print(f"[ROOM] 방 참가: {code}")
            rooms[code]["event"].set()  # create 핸들러 깨우기

            # join 핸들러: p2(ws) → p1 방향
            await forward(ws, p1)

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if ws in quick_queue:
            quick_queue.remove(ws)
        print(f"[DISCONNECT] {ws.remote_address}")


async def main():
    print(f"[SERVER] 시작됨 — 0.0.0.0:{PORT}")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())