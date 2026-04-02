import pygame
import sys
import threading
import copy
import os
import subprocess

def run_server():
    try:
        current_dir = os.path.dirname(sys.executable)  # 👈 핵심
        server_path = os.path.join(current_dir, "Server.exe")

        print("서버 경로:", server_path)

        if os.path.exists(server_path):
            subprocess.Popen(server_path, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            print("Server.exe not found")
    except Exception as e:
        print("Server 실행 오류:", e)

def resource_path(relative_path):
    """PyInstaller 번들 및 일반 실행 모두에서 올바른 절대 경로를 반환합니다."""
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


from MenuGUI import MenuGUI
from CardGame.CardBattle import CardBattle
from ChessGUI.ChessGUI import ChessGUI
from Chess.Chess import Chess, ChessAI
from Network import NetworkClient


def get_pieces_on_board(chess_obj, color):
    """체스판에서 특정 색의 기물 목록 반환 (킹 제외, 중복 포함)."""
    pieces = []
    for r in range(8):
        for c in range(8):
            p = chess_obj.board[r][c]
            if p and p[0] == color and p[1] != 'k':
                pieces.append(p[1])
    return pieces


def remove_one_piece_from_board(chess_obj, color, piece_char):
    """체스판에서 해당 색+기물 문자의 기물을 하나만 제거."""
    for r in range(8):
        for c in range(8):
            p = chess_obj.board[r][c]
            if p and p[0] == color and p[1] == piece_char:
                chess_obj.board[r][c] = None
                return True
    return False


def main():
    pygame.init()
    screen_width = 850
    screen_height = 850
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("체스 카드 게임")
    clock = pygame.time.Clock()

    # 폰트 로드
    _font_path = resource_path(os.path.join("assets", "fonts", "OTF", "MaruBuri-Regular.otf"))
    def load_font(size):
        try:
            return pygame.font.Font(_font_path, size)
        except Exception:
            return pygame.font.Font(None, size)

    game_state = "menu"
    game_mode = "single"  # "single", "multi_local", "multi_net"

    menu_gui = MenuGUI(screen, screen_width, screen_height)

    # 네트워크 (멀티플레이)
    net = NetworkClient()
    my_color = 'w'       # 서버에서 받은 내 색x`
    net_waiting = False  # 서버 응답 대기 중
    net_status = ""      # 화면에 표시할 상태 메시지
    room_code_display = ""
    chess = Chess()
    gui = ChessGUI(chess, screen)
    chess_ai = ChessAI(color='b', depth=3)

    running = True
    in_card_game = False
    card_battle_manager = None

    # 나가기 버튼 (오른쪽 위)
    quit_btn_rect = pygame.Rect(screen_width - 110, 10, 100, 36)

    # 타이머: 각자 5분(300초), 자신의 턴에만 감소, 카드 게임 중 정지
    TIMER_TOTAL = 300.0
    white_time = TIMER_TOTAL  # 백 남은 시간
    black_time = TIMER_TOTAL  # 흑 남은 시간
    last_tick = pygame.time.get_ticks()

    card_mover_pos = None
    card_mover_is_player = True
    card_gone_piece_str = None

    # 카드 배틀 참가 기물의 색 (소환 기물 사망 시 체스판 제거에 필요)
    card_player_color = 'w'
    card_opponent_color = 'b'

    promotion_pending_display = False

    ai_thinking = False
    ai_move_result = [None]
    ai_delay_until = 0

    def ai_think():
        board_copy = copy.deepcopy(chess)
        move = chess_ai.get_best_move(board_copy)
        ai_move_result[0] = move

    def reset_game():
        nonlocal chess, gui, chess_ai, in_card_game, card_battle_manager
        nonlocal card_mover_pos, card_mover_is_player, card_gone_piece_str
        nonlocal card_player_color, card_opponent_color
        nonlocal promotion_pending_display, ai_thinking, ai_delay_until
        nonlocal white_time, black_time, last_tick
        chess = Chess()
        gui = ChessGUI(chess, screen)
        chess_ai = ChessAI(color='b', depth=3)
        in_card_game = False
        card_battle_manager = None
        card_mover_pos = None
        card_mover_is_player = True
        card_gone_piece_str = None
        card_player_color = 'w'
        card_opponent_color = 'b'
        promotion_pending_display = False
        ai_thinking = False
        ai_move_result[0] = None
        ai_delay_until = 0
        white_time = TIMER_TOTAL
        black_time = TIMER_TOTAL
        last_tick = pygame.time.get_ticks()

    while running:
        now_tick = pygame.time.get_ticks()
        dt = (now_tick - last_tick) / 1000.0
        last_tick = now_tick

        # 타이머 업데이트: 체스 게임 중, 카드 게임 아닐 때만 현재 턴 시간 감소
        if game_state == "chess_game" and not in_card_game:
            if chess.turn == 'w':
                white_time = max(0.0, white_time - dt)
            elif chess.turn == 'b' and (ai_thinking or game_mode in ("multi_local", "multi_net")):
                black_time = max(0.0, black_time - dt)

            # 시간 초과 → 패배 처리
            if white_time <= 0:
                gui.draw()
                gui.draw_game_over_message("시간 초과! 흑 승리!")
                pygame.display.flip()
                pygame.time.wait(3000)
                reset_game()
                game_state = "menu"
            elif black_time <= 0:
                gui.draw()
                gui.draw_game_over_message("시간 초과! 백 승리!")
                pygame.display.flip()
                pygame.time.wait(3000)
                reset_game()
                game_state = "menu"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if game_state == "menu":
                action = menu_gui.handle_event(event)
                if action == "start_single":
                    game_mode = "single"
                    reset_game()
                    game_state = "chess_game"
                elif action == "start_multi":
                    game_mode = "multi_local"
                    reset_game()
                    game_state = "chess_game"
                elif isinstance(action, dict):
                    act = action.get("action")
                    if act == "multi_quick":
                        net_waiting = True
                        net_status = "서버에 연결 중..."
                        menu_gui.lobby_status = net_status
                        def _connect_quick():
                            nonlocal net_waiting, net_status
                            if net.connect():
                                net.quick_match()
                                net_status = "상대방을 기다리는 중..."
                                menu_gui.lobby_status = net_status
                            else:
                                net_waiting = False
                                menu_gui.lobby_status = f"연결 실패: {net._error}"
                        threading.Thread(target=_connect_quick, daemon=True).start()
                    elif act == "multi_create":
                        net_waiting = True
                        menu_gui.lobby_status = "서버에 연결 중..."
                        def _connect_create():
                            nonlocal net_waiting, net_status, room_code_display
                            if net.connect():
                                net.create_room()
                                net_status = "방 생성 중..."
                                menu_gui.lobby_status = net_status
                            else:
                                net_waiting = False
                                menu_gui.lobby_status = f"연결 실패: {net._error}"
                        threading.Thread(target=_connect_create, daemon=True).start()
                    elif act == "multi_join":
                        code = action.get("code", "").strip()
                        if not code:
                            menu_gui.lobby_status = "방 코드를 입력해주세요."
                        else:
                            net_waiting = True
                            menu_gui.lobby_status = "서버에 연결 중..."
                            def _connect_join():
                                nonlocal net_waiting, net_status
                                if net.connect():
                                    net.join_room(code)
                                    net_status = "방 참가 중..."
                                    menu_gui.lobby_status = net_status
                                else:
                                    net_waiting = False
                                    menu_gui.lobby_status = f"연결 실패: {net._error}"
                            threading.Thread(target=_connect_join, daemon=True).start()
                elif action == "exit_game":
                    running = False

            elif game_state == "chess_game":
                # 나가기 버튼 클릭 처리
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if quit_btn_rect.collidepoint(event.pos):
                        reset_game()
                        game_state = "menu"
                        continue

                # 싱글: 백 턴만 입력 / 로컬멀티: 현재 턴 / 넷멀티: 내 색 턴만
                player_turn = (
                    (game_mode == "single" and chess.turn == 'w') or
                    (game_mode == "multi_local" and chess.turn in ('w', 'b')) or
                    (game_mode == "multi_net" and chess.turn == my_color)
                )

                if not in_card_game and player_turn and not ai_thinking:

                    if promotion_pending_display:
                        res = gui.handle_click(event)
                        if res == "promoted":
                            promotion_pending_display = False
                            ai_delay_until = pygame.time.get_ticks() + 1500
                            if game_mode == "multi_net":
                                net.send_promote(chess.board[gui.last_move[1][0]][gui.last_move[1][1]][1] if gui.last_move else 'q')
                        continue

                    result = gui.handle_click(event)

                    if isinstance(result, tuple) and result[0] in ("battle", "battle_and_promotion_pending"):
                        in_card_game = True
                        _, attacker_info, defender_info, start_pos, end_pos = result[:5]

                        card_mover_pos = end_pos
                        card_mover_is_player = True
                        card_gone_piece_str = defender_info[0] + defender_info[1]
                        card_player_color = attacker_info[0]
                        card_opponent_color = defender_info[0]

                        player_allies = get_pieces_on_board(chess, card_player_color)
                        opponent_allies = get_pieces_on_board(chess, card_opponent_color)

                        card_battle_manager = CardBattle(
                            screen,
                            attacker_info[1], defender_info[1],
                            attacker_info[0], defender_info[0],
                            player_ally_pieces=player_allies,
                            opponent_ally_pieces=opponent_allies
                        )
                        if game_mode == "multi_net" and gui.last_move:
                            net.send_move(gui.last_move[0], gui.last_move[1])

                    elif result == "promotion_pending":
                        promotion_pending_display = True

                    elif result == "moved":
                        ai_delay_until = pygame.time.get_ticks() + 1500
                        if game_mode == "multi_net" and gui.last_move:
                            net.send_move(gui.last_move[0], gui.last_move[1])

        # ── 네트워크 메시지 처리 ─────────────────────────────────────────
        if net.connected or net_waiting:
            for msg in net.poll():
                mtype = msg.get("type")

                if mtype == "waiting":
                    menu_gui.lobby_status = msg.get("message", "대기 중...")

                elif mtype == "room_created":
                    room_code_display = msg.get("code", "")
                    menu_gui.lobby_status = f"방 코드: {room_code_display}  |  상대방을 기다리는 중..."

                elif mtype == "room_joined":
                    menu_gui.lobby_status = "방에 참가했습니다. 게임 시작 대기 중..."

                elif mtype == "game_start":
                    my_color = msg.get("color", "w")
                    game_mode = "multi_net"
                    net_waiting = False
                    reset_game()
                    # 흑이면 체스판 뒤집기 플래그 (ChessGUI에서 처리 가능)
                    game_state = "chess_game"
                    menu_gui.lobby_status = ""

                elif mtype == "move":
                    # 상대방 이동 수신
                    if game_state == "chess_game" and game_mode == "multi_net":
                        start = tuple(msg["start"])
                        end = tuple(msg["end"])
                        chess.turn = 'b' if my_color == 'w' else 'w'
                        move_res = chess.move_piece(start, end)
                        if isinstance(move_res, tuple) and move_res[0] in ("battle", "battle_and_promotion_pending"):
                            in_card_game = True
                            _, attacker_info, defender_info, s_pos, e_pos = move_res[:5]
                            card_mover_pos = e_pos
                            card_mover_is_player = False
                            card_gone_piece_str = defender_info[0] + defender_info[1]
                            card_player_color = defender_info[0]
                            card_opponent_color = attacker_info[0]
                            player_allies = get_pieces_on_board(chess, card_player_color)
                            opponent_allies = get_pieces_on_board(chess, card_opponent_color)
                            card_battle_manager = CardBattle(
                                screen,
                                defender_info[1], attacker_info[1],
                                defender_info[0], attacker_info[0],
                                player_ally_pieces=player_allies,
                                opponent_ally_pieces=opponent_allies
                            )

                elif mtype == "promote":
                    chess.promote_pawn(msg.get("piece", "q"))

                elif mtype == "error":
                    menu_gui.lobby_status = msg.get("message", "오류 발생")
                    net_waiting = False
                    net.disconnect()

                elif mtype in ("disconnected", "opponent_disconnected"):
                    if game_state == "chess_game":
                        gui.draw()
                        gui.draw_game_over_message("상대방 연결이 끊어졌습니다.")
                        pygame.display.flip()
                        pygame.time.wait(3000)
                        reset_game()
                        game_state = "menu"
                    net_waiting = False
                    menu_gui.lobby_status = "연결이 끊어졌습니다."

        # ── AI 턴 처리 (싱글플레이만) ────────────────────────────────────
        if game_mode == "single" and game_state == "chess_game" and not in_card_game and chess.turn == 'b':
            now = pygame.time.get_ticks()

            if not ai_thinking and now >= ai_delay_until:
                ai_thinking = True
                ai_move_result[0] = None
                t = threading.Thread(target=ai_think, daemon=True)
                t.start()

            elif ai_thinking and ai_move_result[0] is not None:
                ai_thinking = False
                best = ai_move_result[0]
                ai_move_result[0] = None

                if best:
                    start_pos_ai, end_pos_ai = best
                    chess.turn = 'b'
                    move_res = chess.move_piece(start_pos_ai, end_pos_ai)

                    if isinstance(move_res, tuple) and move_res[0] in ("battle", "battle_and_promotion_pending"):
                        in_card_game = True
                        _, attacker_info, defender_info, s_pos, e_pos = move_res[:5]

                        # AI(흑) 공격 → 카드 Player=백(수비자), 카드 Opponent=흑(공격자)
                        card_mover_pos = e_pos
                        card_mover_is_player = False
                        card_gone_piece_str = defender_info[0] + defender_info[1]
                        card_player_color = defender_info[0]    # 'w'
                        card_opponent_color = attacker_info[0]  # 'b'

                        player_allies = get_pieces_on_board(chess, card_player_color)
                        opponent_allies = get_pieces_on_board(chess, card_opponent_color)

                        card_battle_manager = CardBattle(
                            screen,
                            defender_info[1], attacker_info[1],
                            defender_info[0], attacker_info[0],
                            player_ally_pieces=player_allies,
                            opponent_ally_pieces=opponent_allies
                        )

                    elif move_res == "promotion_pending":
                        chess.promote_pawn('q')
                        ai_delay_until = pygame.time.get_ticks() + 500
                else:
                    chess.turn = 'w'

        # ── 카드 배틀 처리 ───────────────────────────────────────────────
        if game_state == "chess_game" and in_card_game and card_battle_manager:
            winner_obj = card_battle_manager.run()

            if winner_obj == "quit":
                running = False

            elif winner_obj is not None:
                in_card_game = False

                # 소환 기물 사망 → 체스판에서 제거
                for (dead_color, dead_char) in card_battle_manager.dead_summoned_pieces:
                    removed = remove_one_piece_from_board(gui.chess, dead_color, dead_char)
                    print(f"소환 기물 사망 체스판 제거: {dead_color}{dead_char} {'성공' if removed else '실패'}")

                # 보드에 공격자가 있는 위치 = card_mover_pos
                # card_mover_is_player=True → 보드 기물 = 카드 Player
                # card_mover_is_player=False → 보드 기물 = 카드 Opponent
                mover_won = (
                    (card_mover_is_player and winner_obj.role == "Player") or
                    (not card_mover_is_player and winner_obj.role == "Opponent")
                )
                pos = card_mover_pos

                if mover_won:
                    # 공격자(보드에 있는 기물) 승리 → 유지
                    pass
                else:
                    # 공격자 패배 → 공격자 제거, 수비자 복원
                    gui.chess.board[pos[0]][pos[1]] = card_gone_piece_str

                # 킹 생존 확인
                white_king_alive = gui.chess.is_king_on_board('w')
                black_king_alive = gui.chess.is_king_on_board('b')

                if not white_king_alive:
                    gui.draw()
                    gui.draw_game_over_message("흑 승리!")
                    pygame.display.flip()
                    pygame.time.wait(3000)
                    reset_game()
                    game_state = "menu"
                elif not black_king_alive:
                    gui.draw()
                    gui.draw_game_over_message("백 승리!")
                    pygame.display.flip()
                    pygame.time.wait(3000)
                    reset_game()
                    game_state = "menu"
                else:
                    ai_delay_until = pygame.time.get_ticks() + 1500

                card_mover_pos = None
                card_mover_is_player = True
                card_gone_piece_str = None
                card_battle_manager = None
                promotion_pending_display = False
                ai_thinking = False
                ai_move_result[0] = None

        # ── 화면 그리기 ──────────────────────────────────────────────────
        if game_state == "menu":
            menu_gui.draw()
            # 네트워크 대기 중 표시
            if net_waiting:
                font = load_font(28)
                surf = font.render(net_status, True, (255, 220, 80))
                screen.blit(surf, surf.get_rect(center=(screen_width // 2, screen_height - 30)))
        elif game_state == "chess_game" and not in_card_game:
            screen.fill((30, 30, 30))  # 배경
            gui.draw()

            # AI 상태 / 현재 턴 표시
            if game_mode == "single" and chess.turn == 'b':
                font = load_font(36)
                msg = "AI 생각 중..." if ai_thinking else "AI 대기 중..."
                surf = font.render(msg, True, (255, 200, 0))
                screen.blit(surf, (10, screen_height - 40))
            elif game_mode in ("multi_local", "multi_net"):
                font = load_font(32)
                if game_mode == "multi_net":
                    if chess.turn == my_color:
                        turn_msg = "내 턴"
                    else:
                        turn_msg = "상대방 턴"
                else:
                    turn_msg = "백의 턴" if chess.turn == 'w' else "흑의 턴"
                turn_surf = font.render(turn_msg, True, (255, 220, 100))
                screen.blit(turn_surf, turn_surf.get_rect(center=(screen_width // 2, screen_height - 25)))

            # ── 타이머 표시 (체스판 위 가운데) ───────────────────────────
            timer_font = load_font(38)
            board_center_x = screen_width // 2
            timer_y = 22

            w_label = "백" if game_mode == "single" else ("백(나)" if (game_mode == "multi_net" and my_color == 'w') else "백")
            b_label = "흑" if game_mode == "single" else ("흑(나)" if (game_mode == "multi_net" and my_color == 'b') else "흑")

            # 백 타이머 — 왼쪽
            wm = int(white_time) // 60
            ws = int(white_time) % 60
            w_str = f"{w_label}  {wm:02d}:{ws:02d}"
            w_color = (255, 80, 80) if white_time < 30 else (220, 220, 255)
            if chess.turn == 'w':
                w_bg = pygame.Rect(board_center_x - 240, timer_y - 6, 190, 36)
                pygame.draw.rect(screen, (60, 60, 120), w_bg, border_radius=6)
            w_surf = timer_font.render(w_str, True, w_color)
            screen.blit(w_surf, w_surf.get_rect(center=(board_center_x - 145, timer_y + 12)))

            # 흑 타이머 — 오른쪽
            bm = int(black_time) // 60
            bs = int(black_time) % 60
            b_str = f"{b_label}  {bm:02d}:{bs:02d}"
            b_color = (255, 80, 80) if black_time < 30 else (180, 220, 180)
            if chess.turn == 'b':
                b_bg = pygame.Rect(board_center_x + 50, timer_y - 6, 190, 36)
                pygame.draw.rect(screen, (40, 90, 40), b_bg, border_radius=6)
            b_surf = timer_font.render(b_str, True, b_color)
            screen.blit(b_surf, b_surf.get_rect(center=(board_center_x + 145, timer_y + 12)))

            # 구분선
            pygame.draw.line(screen, (100, 100, 100),
                             (board_center_x - 10, timer_y - 4),
                             (board_center_x - 10, timer_y + 28), 2)

            # 나가기 버튼
            mouse_pos = pygame.mouse.get_pos()
            btn_color = (200, 60, 60) if quit_btn_rect.collidepoint(mouse_pos) else (160, 40, 40)
            pygame.draw.rect(screen, btn_color, quit_btn_rect, border_radius=6)
            pygame.draw.rect(screen, (255, 120, 120), quit_btn_rect, 2, border_radius=6)
            btn_font = load_font(28)
            btn_surf = btn_font.render("나가기", True, (255, 255, 255))
            screen.blit(btn_surf, btn_surf.get_rect(center=quit_btn_rect.center))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_server()
    main()