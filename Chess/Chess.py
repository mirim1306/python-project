import random

class Chess:
    # 체스 기물 심볼을 카드 게임에서 사용할 이름으로 매핑 (공유될 수 있도록 클래스 변수로)
    piece_char_to_card_name_map = {
        'p': 'p',
        'r': 'r',
        'n': 'n',
        'b': 'b',
        'q': 'q',
        'k': 'k'
    }

    def __init__(self):
        self.game_over = False
        self.winner = None
        self.board = self.create_board()
        self.promotion_pending = False
        self.promotion_pos = None  # (row, col)
        self.promotion_color = None
        self.turn = 'w'
        self.castling_rights = {
            'w': {'K': True, 'Q': True},
            'b': {'K': True, 'Q': True}
        }
        # 앙파상 대상 칸: (row, col) 또는 None. 직전 턴에 폰이 두 칸 전진하여 통과한 칸
        self.en_passant_target = None
        self.last_move = None  # 마지막 이동을 저장 (앙파상 시뮬레이션용)

    def create_board(self):
        return [
            ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
            ['bp'] * 8,
            [None] * 8,
            [None] * 8,
            [None] * 8,
            [None] * 8,
            ['wp'] * 8,
            ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr']
        ]

    def in_bounds(self, row, col):
        return 0 <= row < 8 and 0 <= col < 8

    def get_valid_moves(self, row, col):
        piece = self.board[row][col]
        if not piece or piece[0] != self.turn:
            return []

        piece_type = piece[1]
        moves = []

        if piece_type == 'p':
            moves = self.get_pawn_moves(row, col)
        elif piece_type == 'r':
            moves = self.get_rook_moves(row, col)
        elif piece_type == 'n':
            moves = self.get_knight_moves(row, col)
        elif piece_type == 'b':
            moves = self.get_bishop_moves(row, col)
        elif piece_type == 'q':
            moves = self.get_queen_moves(row, col)
        elif piece_type == 'k':
            moves = self.get_king_moves(row, col)

        return moves

    def get_pawn_moves(self, row, col):
        direction = -1 if self.turn == 'w' else 1
        moves = []

        # 한 칸 전진
        if self.in_bounds(row + direction, col) and self.board[row + direction][col] is None:
            moves.append((row + direction, col))

        # 첫 이동 두 칸 전진
        start_row = 6 if self.turn == 'w' else 1
        if row == start_row and self.board[row + direction][col] is None and \
                self.in_bounds(row + 2 * direction, col) and self.board[row + 2 * direction][col] is None:
            moves.append((row + 2 * direction, col))

        # 대각선 캡처
        for dc in [-1, 1]:
            nr, nc = row + direction, col + dc
            if self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target and target[0] != self.turn:
                    moves.append((nr, nc))

        # 앙파상
        if self.en_passant_target:
            ep_row, ep_col = self.en_passant_target
            # 앙파상 대상 칸이 현재 폰의 바로 옆 칸인지 확인
            # 백색 폰은 4번째 랭크(인덱스 3), 흑색 폰은 3번째 랭크(인덱스 4)에 있어야 앙파상으로 잡을 수 있음
            if (self.turn == 'w' and row == 3) or (self.turn == 'b' and row == 4):
                # 앙파상 대상 칸으로 이동하는 것이 대각선 이동인지 확인
                if ep_row == row + direction and abs(col - ep_col) == 1:
                    # 앙파상으로 잡히는 폰이 실제로 있는지 확인 (대상 칸의 row-direction 위치에)
                    captured_pawn_row = row  # 잡히는 폰은 현재 폰과 같은 행, 도착할 열에 있음
                    captured_pawn_col = ep_col
                    if self.in_bounds(captured_pawn_row, captured_pawn_col):
                        captured_piece = self.board[captured_pawn_row][captured_pawn_col]
                        # 잡히는 기물이 상대방 폰인지 확인
                        if captured_piece and captured_piece[0] != self.turn and captured_piece[1] == 'p':
                            moves.append(self.en_passant_target)
                            print(f"DEBUG: En Passant move added: {self.en_passant_target}")

        return moves

    def promote_pawn(self, piece_type_char):
        if not self.promotion_pending or not self.promotion_pos:
            print("ERROR: Promotion not pending or position not set.")
            return

        row, col = self.promotion_pos
        # 폰의 색상은 promotion_color에 저장되어 있지만, 혹시 모르니 보드에서 다시 가져옴
        current_piece_color = self.board[row][col][0] if self.board[row][col] else self.promotion_color

        if not current_piece_color:  # 기물 정보가 없다면 오류
            print("ERROR: Could not determine pawn color for promotion.")
            self.promotion_pending = False
            self.promotion_pos = None
            self.promotion_color = None
            return

        self.board[row][col] = current_piece_color + piece_type_char
        self.promotion_pending = False
        self.promotion_pos = None
        self.promotion_color = None
        self.en_passant_target = None
        # 폰 승진 후 턴 넘기기는 ChessCard.py에서 처리하는 것이 더 일관적입니다.
        self.turn = 'b' if self.turn == 'w' else 'w'  # 폰 승진 후 턴 넘기기

    def get_rook_moves(self, row, col):
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        return self.slide_moves(row, col, directions)

    def get_knight_moves(self, row, col):
        moves = []
        deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                  (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in deltas:
            r, c = row + dr, col + dc
            if self.in_bounds(r, c):
                target = self.board[r][c]
                if not target or target[0] != self.turn:
                    moves.append((r, c))
        return moves

    def get_bishop_moves(self, row, col):
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        return self.slide_moves(row, col, directions)

    def get_queen_moves(self, row, col):
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1),
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]
        return self.slide_moves(row, col, directions)

    def get_king_moves(self, row, col):
        moves = []
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1),
                  (-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in deltas:
            r, c = row + dr, col + dc
            if self.in_bounds(r, c):
                target = self.board[r][c]
                if not target or target[0] != self.turn:
                    moves.append((r, c))

        # 캐슬링 (실제 체스 규칙에 따라 체크 경로 확인 로직 필요)
        if self.turn == 'w' and row == 7 and col == 4:
            # 킹사이드 캐슬링
            if self.castling_rights['w']['K'] and \
                    self.board[7][5] is None and self.board[7][6] is None and \
                    not self.is_in_check_after_move((7, 4), (7, 5)) and not self.is_in_check_after_move((7, 4),
                                                                                                        (7, 6)) and \
                    not self.is_in_check('w'):  # 킹이 현재 체크가 아님
                moves.append((7, 6))
            # 퀸사이드 캐슬링
            if self.castling_rights['w']['Q'] and \
                    self.board[7][1] is None and self.board[7][2] is None and self.board[7][3] is None and \
                    not self.is_in_check_after_move((7, 4), (7, 3)) and not self.is_in_check_after_move((7, 4),
                                                                                                        (7, 2)) and \
                    not self.is_in_check('w'):  # 킹이 현재 체크가 아님
                moves.append((7, 2))
        elif self.turn == 'b' and row == 0 and col == 4:
            # 킹사이드 캐슬링
            if self.castling_rights['b']['K'] and \
                    self.board[0][5] is None and self.board[0][6] is None and \
                    not self.is_in_check_after_move((0, 4), (0, 5)) and not self.is_in_check_after_move((0, 4),
                                                                                                        (0, 6)) and \
                    not self.is_in_check('b'):
                moves.append((0, 6))
            # 퀸사이드 캐슬링
            if self.castling_rights['b']['Q'] and \
                    self.board[0][1] is None and self.board[0][2] is None and self.board[0][3] is None and \
                    not self.is_in_check_after_move((0, 4), (0, 3)) and not self.is_in_check_after_move((0, 4),
                                                                                                        (0, 2)) and \
                    not self.is_in_check('b'):
                moves.append((0, 2))
        return moves

    def is_in_check(self, color):
        return False

    def is_in_check_after_move(self, start_pos, end_pos):
        return False

    def slide_moves(self, row, col, directions):
        moves = []
        for dr, dc in directions:
            r, c = row + dr, col + dc
            while self.in_bounds(r, c):
                target = self.board[r][c]
                if not target:
                    moves.append((r, c))
                elif target[0] != self.turn:
                    moves.append((r, c))
                    break
                else:
                    break
                r += dr
                c += dc
        return moves

    def move_piece(self, start, end):
        if self.game_over:
            return False

        sr, sc = start
        er, ec = end
        piece_moved = self.board[sr][sc]  # 이동할 기물

        if not piece_moved or piece_moved[0] != self.turn:
            return False

        valid_moves = self.get_valid_moves(sr, sc)
        if (er, ec) not in valid_moves:
            print(f"DEBUG: Move ({start} to {end}) is not in valid_moves: {valid_moves}")
            return False

        target_piece_at_end = self.board[er][ec]  # 목표 위치에 있던 기물 (캡처될 기물)

        # 앙파상 처리: 이동 후 앙파상 대상 폰 제거
        is_en_passant_capture = False
        captured_pawn_info_for_battle = None  # 앙파상으로 잡히는 폰의 정보를 담을 변수
        defender_original_pos_for_battle = end  # 수비자 기물의 원래 위치 (기본값은 도착 칸)

        # 앙파상 대상 칸으로 이동했고, 현재 움직이는 기물이 폰이며, 옆으로 한 칸 이동한 경우
        if piece_moved[1] == 'p' and (er, ec) == self.en_passant_target and abs(sc - ec) == 1:
            print(f"DEBUG: Detected potential En Passant move.")
            captured_pawn_row = sr  # 잡히는 폰은 공격자 폰과 같은 행, 도착할 열에 있음
            captured_pawn_col = ec
            # 잡히는 폰이 실제로 있는지, 그리고 그 폰이 상대방 폰인지 다시 한번 확인 (안전장치)
            if self.in_bounds(captured_pawn_row, captured_pawn_col) and \
                    self.board[captured_pawn_row][captured_pawn_col] and \
                    self.board[captured_pawn_row][captured_pawn_col][0] != self.turn and \
                    self.board[captured_pawn_row][captured_pawn_col][1] == 'p':

                # 앙파상으로 잡히는 폰 정보를 저장 (배틀에 사용될 정보)
                captured_piece_notation = self.board[captured_pawn_row][captured_pawn_col]
                defender_color = captured_piece_notation[0]
                defender_piece_char = captured_piece_notation[1]

                captured_pawn_info_for_battle = (
                defender_color, self.piece_char_to_card_name_map.get(defender_piece_char, "Unknown"))

                self.board[captured_pawn_row][captured_pawn_col] = None  # 잡히는 폰 제거
                is_en_passant_capture = True
                defender_original_pos_for_battle = (captured_pawn_row, captured_pawn_col)  # 앙파상 폰의 실제 위치
                print(f"DEBUG: En Passant capture at ({captured_pawn_row}, {captured_pawn_col}) CONFIRMED.")
            else:
                print(
                    f"DEBUG: En Passant target was not a valid captured pawn at ({captured_pawn_row}, {captured_pawn_col}).")

        # 캐슬링 처리 (이동 전에 룩도 함께 이동)
        if piece_moved[1] == 'k' and abs(sc - ec) == 2:
            if ec == 6:  # 킹사이드 캐슬링 (킹이 (sr,sc) -> (sr,6), 룩이 (sr,7) -> (sr,5))
                rook_piece = self.board[sr][7]
                self.board[sr][5] = rook_piece
                self.board[sr][7] = None
            elif ec == 2:  # 퀸사이드 캐슬링 (킹이 (sr,sc) -> (sr,2), 룩이 (sr,0) -> (sr,3))
                rook_piece = self.board[sr][0]
                self.board[sr][3] = rook_piece
                self.board[sr][0] = None

        # 기물 이동 (캡처 여부와 관계없이 일단 GUI에 반영되도록 이동)
        # 캡처인 경우에도 일단 공격자 기물을 목표 위치로 이동
        self.board[er][ec] = piece_moved
        self.board[sr][sc] = None  # 시작 위치는 비움

        # 캐슬링 권한 업데이트
        if piece_moved[1] == 'k':  # 킹이 움직이면 해당 색상의 캐슬링 권한 모두 제거
            self.castling_rights[self.turn]['K'] = False
            self.castling_rights[self.turn]['Q'] = False
        elif piece_moved[1] == 'r':  # 룩이 움직이면 해당 룩의 캐슬링 권한 제거
            if start == (7, 7): self.castling_rights['w']['K'] = False
            if start == (7, 0): self.castling_rights['w']['Q'] = False
            if start == (0, 7): self.castling_rights['b']['K'] = False
            if start == (0, 0): self.castling_rights['b']['Q'] = False

        # 앙파상 대상 칸 업데이트
        # 현재 폰이 두 칸 전진했을 때만 앙파상 타겟을 설정
        if piece_moved[1] == 'p' and abs(sr - er) == 2:
            self.en_passant_target = (sr + (er - sr) // 2, ec)  # 폰이 통과한 칸
            print(f"DEBUG: En Passant target set to: {self.en_passant_target}")
        else:
            # 앙파상 타겟 초기화 로직은 폰이 두 칸 전진하지 않은 모든 경우에 실행되어야 합니다.
            self.en_passant_target = None  # 다른 기물이 움직이거나 폰이 한 칸만 움직이면 초기화
            print(f"DEBUG: En Passant target set to None.")

        # 폰 승진 로직을 통합하여 처리
        is_promotion_possible = (piece_moved[1] == 'p' and (er == 0 or er == 7))

        # 캡처 (전투) 로직 (일반 캡처 또는 앙파상 캡처인 경우)
        if target_piece_at_end or is_en_passant_capture:
            attacker_color = piece_moved[0]
            attacker_piece_char = piece_moved[1]
            attacker_card_name = self.piece_char_to_card_name_map.get(attacker_piece_char, "Unknown")
            attacker_info = (attacker_color, attacker_card_name)

            # 수비자 정보는 일반 캡처와 앙파상 캡처에서 가져오는 방식이 다름
            if is_en_passant_capture:
                defender_info = captured_pawn_info_for_battle
            else:  # 일반 캡처
                defender_piece_notation = target_piece_at_end
                defender_color = defender_piece_notation[0]
                defender_piece_char = defender_piece_notation[1]
                defender_card_name = self.piece_char_to_card_name_map.get(defender_piece_char, "Unknown")
                defender_info = (defender_color, defender_card_name)

            # 캡처와 동시에 폰 승진이 가능한 경우
            if is_promotion_possible:
                self.promotion_pending = True
                self.promotion_pos = (er, ec)  # 승진할 폰의 최종 위치
                self.promotion_color = piece_moved[0]  # 승진할 폰의 색상
                print(
                    f"DEBUG: move_piece returning 'battle_and_promotion_pending'. Promotion pending for {self.promotion_pos}.")
                self.turn = 'b' if self.turn == 'w' else 'w'
                return ("battle_and_promotion_pending",
                        attacker_info,
                        defender_info,
                        start,  # 공격자 기물의 원래 시작 위치
                        defender_original_pos_for_battle,  # 수비자 기물의 실제 있던 위치
                        end)  # 폰 승진할 최종 위치 (캡처된 칸)
            else:  # 캡처는 발생했지만 폰 승진은 불가능한 경우 (일반 캡처)
                print(f"DEBUG: move_piece returning 'battle'.")
                self.turn = 'b' if self.turn == 'w' else 'w'
                return ("battle",
                        attacker_info,  # 공격자 정보 (색상, 카드 이름)
                        defender_info,  # 수비자 정보 (색상, 카드 이름)
                        start,  # 공격자 기물의 원래 위치 (sr, sc)
                        defender_original_pos_for_battle)  # 수비자 기물이 있던 위치 (er, ec) 또는 앙파상 폰의 위치

        # 캡처가 아니고 폰 승진이 필요한 경우
        if is_promotion_possible:
            # 즉, 캡처가 없는 순수 폰 승진 이동일 때입니다.
            self.promotion_pending = True
            self.promotion_pos = (er, ec)
            self.promotion_color = piece_moved[0]
            print(f"DEBUG: move_piece returning 'promotion_pending'. Promotion pending for {self.promotion_pos}.")
            self.turn = 'b' if self.turn == 'w' else 'w'
            return "promotion_pending"

        # 일반 이동 (캡처도 아니고 폰 승진도 아닌 경우)
        print(f"DEBUG: move_piece returning True. self.turn is currently: {self.turn}")  # 현재 턴 정보만 출력
        self.turn = 'b' if self.turn == 'w' else 'w'
        return True  # 일반 이동 성공

    def remove_piece_from_board(self, row, col):
        """
        주어진 위치의 기물을 보드에서 제거합니다.
        카드 배틀에서 패배한 기물 제거용.
        """
        if self.in_bounds(row, col):
            self.board[row][col] = None
            print(f"DEBUG: Piece removed from ({row}, {col})")

    def place_piece_on_board(self, piece_info, row, col):
        """
        주어진 위치에 기물을 다시 배치합니다.
        카드 배틀에서 승리하여 기물이 복원될 때 사용.
        piece_info: (color, piece_type_str) 예: ('w', 'p')
        """
        color = piece_info[0]
        card_name_to_piece_char = {v: k for k, v in self.piece_char_to_card_name_map.items()}
        piece_type_char = card_name_to_piece_char.get(piece_info[1], None)

        if self.in_bounds(row, col) and piece_type_char:
            self.board[row][col] = color + piece_type_char
            print(f"DEBUG: Successfully placed piece {color + piece_type_char} at ({row}, {col})")
        else:
            print(
                f"Error: Could not place piece {piece_info} at ({row}, {col}). Invalid piece_type_char or out of bounds.")

    def is_king_on_board(self, color):
        """
        주어진 색상의 킹이 체스판에 존재하는지 확인합니다.
        :param color: 'w' (흰색) 또는 'b' (검은색)
        :return: 킹이 존재하면 True, 없으면 False
        """
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                # 기물이 존재하고, 해당 기물의 색상이 주어진 color와 같고, 기물 타입이 'k'인지 확인합니다.
                if piece and piece[0] == color and piece[1] == 'k':
                    return True  # 킹을 찾음
        return False  # 킹을 찾지 못함

    def is_game_over(self):
        # 킹이 잡히면 게임 종료
        white_king_exists = self.is_king_on_board('w')
        black_king_exists = self.is_king_on_board('b')
        return not white_king_exists or not black_king_exists

    def get_winner(self):
        if not self.is_game_over():
            return None  # 게임 아직 안 끝남

        white_king_exists = self.is_king_on_board('w')
        black_king_exists = self.is_king_on_board('b')

        if not white_king_exists:
            return 'b'  # 백 킹이 없으면 흑 승리
        elif not black_king_exists:
            return 'w'  # 흑 킹이 없으면 백 승리
        return None  # 둘 다 있으면 뭔가 잘못된 경우


class ChessAI:
    """
    흑(black) 기물을 제어하는 체스 AI.
    minimax + 알파-베타 가지치기로 최적 수를 결정합니다.
    """

    PIECE_VALUES = {
        'p': 100, 'n': 320, 'b': 330,
        'r': 500, 'q': 900, 'k': 20000
    }

    # 위치 보너스 테이블 (백 기준, 흑은 뒤집어 사용)
    PAWN_TABLE = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [5, 5, 10, 25, 25, 10, 5, 5],
        [0, 0, 0, 20, 20, 0, 0, 0],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [5, 10, 10, -20, -20, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]
    KNIGHT_TABLE = [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20, 0, 0, 0, 0, -20, -40],
        [-30, 0, 10, 15, 15, 10, 0, -30],
        [-30, 5, 15, 20, 20, 15, 5, -30],
        [-30, 0, 15, 20, 20, 15, 0, -30],
        [-30, 5, 10, 15, 15, 10, 5, -30],
        [-40, -20, 0, 5, 5, 0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50],
    ]
    BISHOP_TABLE = [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 10, 10, 5, 0, -10],
        [-10, 5, 5, 10, 10, 5, 5, -10],
        [-10, 0, 10, 10, 10, 10, 0, -10],
        [-10, 10, 10, 10, 10, 10, 10, -10],
        [-10, 5, 0, 0, 0, 0, 5, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20],
    ]
    ROOK_TABLE = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [5, 10, 10, 10, 10, 10, 10, 5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [0, 0, 0, 5, 5, 0, 0, 0],
    ]
    QUEEN_TABLE = [
        [-20, -10, -10, -5, -5, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 5, 5, 5, 0, -10],
        [-5, 0, 5, 5, 5, 5, 0, -5],
        [0, 0, 5, 5, 5, 5, 0, -5],
        [-10, 5, 5, 5, 5, 5, 0, -10],
        [-10, 0, 5, 0, 0, 0, 0, -10],
        [-20, -10, -10, -5, -5, -10, -10, -20],
    ]
    KING_TABLE = [
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-20, -30, -30, -40, -40, -30, -30, -20],
        [-10, -20, -20, -20, -20, -20, -20, -10],
        [20, 20, 0, 0, 0, 0, 20, 20],
        [20, 30, 10, 0, 0, 10, 30, 20],
    ]

    POSITION_TABLES = {
        'p': PAWN_TABLE,
        'n': KNIGHT_TABLE,
        'b': BISHOP_TABLE,
        'r': ROOK_TABLE,
        'q': QUEEN_TABLE,
        'k': KING_TABLE,
    }

    def __init__(self, color='b', depth=3):
        self.color = color  # AI가 제어하는 색상
        self.opponent = 'w' if color == 'b' else 'b'
        self.depth = depth  # 탐색 깊이

    def get_best_move(self, chess_game):
        """
        현재 보드에서 AI의 최선 수를 반환합니다.
        반환값: (start_pos, end_pos) 또는 None(이동 불가)
        """
        best_move = None
        best_score = float('-inf')
        alpha = float('-inf')
        beta = float('inf')

        all_moves = self._get_all_moves(chess_game, self.color)
        random.shuffle(all_moves)  # 동점 시 랜덤성 부여

        for start, end in all_moves:
            # 이동 시뮬레이션
            saved = self._save_state(chess_game)
            chess_game.turn = self.color
            result = chess_game.move_piece(start, end)
            if result is False:
                self._restore_state(chess_game, saved)
                continue

            score = self._minimax(chess_game, self.depth - 1, alpha, beta, False)
            self._restore_state(chess_game, saved)

            if score > best_score:
                best_score = score
                best_move = (start, end)
            alpha = max(alpha, score)

        return best_move

    def _minimax(self, chess_game, depth, alpha, beta, is_maximizing):
        if depth == 0:
            return self._evaluate(chess_game)

        current_color = self.color if is_maximizing else self.opponent
        all_moves = self._get_all_moves(chess_game, current_color)

        if not all_moves:
            return self._evaluate(chess_game)

        if is_maximizing:
            best = float('-inf')
            for start, end in all_moves:
                saved = self._save_state(chess_game)
                chess_game.turn = current_color
                result = chess_game.move_piece(start, end)
                if result is False:
                    self._restore_state(chess_game, saved)
                    continue
                val = self._minimax(chess_game, depth - 1, alpha, beta, False)
                self._restore_state(chess_game, saved)
                best = max(best, val)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best
        else:
            best = float('inf')
            for start, end in all_moves:
                saved = self._save_state(chess_game)
                chess_game.turn = current_color
                result = chess_game.move_piece(start, end)
                if result is False:
                    self._restore_state(chess_game, saved)
                    continue
                val = self._minimax(chess_game, depth - 1, alpha, beta, True)
                self._restore_state(chess_game, saved)
                best = min(best, val)
                beta = min(beta, best)
                if beta <= alpha:
                    break
            return best

    def _get_all_moves(self, chess_game, color):
        """해당 색상의 모든 가능한 이동을 반환합니다."""
        moves = []
        orig_turn = chess_game.turn
        chess_game.turn = color
        for r in range(8):
            for c in range(8):
                piece = chess_game.board[r][c]
                if piece and piece[0] == color:
                    for end in chess_game.get_valid_moves(r, c):
                        moves.append(((r, c), end))
        chess_game.turn = orig_turn
        return moves

    def _evaluate(self, chess_game):
        """보드 상태를 평가합니다. AI(흑) 관점에서 높을수록 유리."""
        score = 0
        for r in range(8):
            for c in range(8):
                piece = chess_game.board[r][c]
                if not piece:
                    continue
                color = piece[0]
                ptype = piece[1]
                val = self.PIECE_VALUES.get(ptype, 0)
                table = self.POSITION_TABLES.get(ptype)

                if table:
                    if color == 'b':
                        pos_bonus = table[r][c]
                    else:
                        pos_bonus = table[7 - r][c]
                else:
                    pos_bonus = 0

                piece_score = val + pos_bonus
                if color == self.color:
                    score += piece_score
                else:
                    score -= piece_score
        return score

    def _save_state(self, chess_game):
        """보드 상태를 저장합니다."""
        import copy
        return {
            'board': copy.deepcopy(chess_game.board),
            'turn': chess_game.turn,
            'castling_rights': copy.deepcopy(chess_game.castling_rights),
            'en_passant_target': chess_game.en_passant_target,
            'promotion_pending': chess_game.promotion_pending,
            'promotion_pos': chess_game.promotion_pos,
            'promotion_color': chess_game.promotion_color,
        }

    def _restore_state(self, chess_game, saved):
        """보드 상태를 복원합니다."""
        chess_game.board = saved['board']
        chess_game.turn = saved['turn']
        chess_game.castling_rights = saved['castling_rights']
        chess_game.en_passant_target = saved['en_passant_target']
        chess_game.promotion_pending = saved['promotion_pending']
        chess_game.promotion_pos = saved['promotion_pos']
        chess_game.promotion_color = saved['promotion_color']