import pygame
import os

class ChessGUI:
    def __init__(self, chess_game, screen):
        self.chess_game = chess_game
        self.chess = chess_game
        self.screen = screen
        self.square_size = 88
        self.width = self.square_size * 8   # 704
        self.height = self.square_size * 8  # 704

        screen_w = screen.get_width()   # 850
        screen_h = screen.get_height()  # 850
        self.board_offset_x = (screen_w - self.width) // 2   # 73
        self.board_offset_y = (screen_h - self.height) // 2  # 73

        self.piece_images = self.load_images()
        self.selected_pos = None  # 선택된 기물의 보드 위치 (row, col)
        self.valid_moves = []

        # 폰트 경로 설정 (이전 수정안에서 더 견고하게 만든 경로 사용)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(base_dir, '..')
        self.font_path = os.path.join(project_root, "assets", "fonts", "OTF", "MaruBuri-Regular.otf")

        print(f"DEBUG: Attempting to load font from: {self.font_path}")

        # 폰트 로드
        try:
            self.main_font = pygame.font.Font(self.font_path, 26)  # 턴 표시용 폰트
            self.promotion_font = pygame.font.Font(self.font_path, 30)  # 프로모션 메뉴용 폰트
            self.game_over_font = pygame.font.Font(self.font_path, 40)  # 게임 오버 메시지용 폰트 추가
            print("DEBUG: Custom fonts loaded successfully.")
        except FileNotFoundError:
            print(f"ERROR: Font file not found at {self.font_path}. Falling back to default font.")
            self.main_font = pygame.font.Font(None, 26)
            self.promotion_font = pygame.font.Font(None, 30)
            self.game_over_font = pygame.font.Font(None, 40)
        except Exception as e:
            print(f"ERROR: An error occurred while loading font from {self.font_path}: {e}. Falling back to default font.")
            self.main_font = pygame.font.Font(None, 26)
            self.promotion_font = pygame.font.Font(None, 30)
            self.game_over_font = pygame.font.Font(None, 40)

        self.promotion_menu_active = False
        self.promotion_buttons = []
        self.promotion_piece_types = ['q', 'r', 'b', 'n']  # 퀸, 룩, 비숍, 나이트
        self.promotion_button_texts = ['퀸', '룩', '비숍', '나이트']
        self._setup_promotion_menu_buttons()
        self.last_move = None  # (start_pos, end_pos) — 네트워크 전송용

    def _setup_promotion_menu_buttons(self):
        self.promotion_buttons = []
        button_width = 100
        button_height = 50
        padding = 20
        total_width = (button_width + padding) * len(self.promotion_button_texts) - padding
        start_x = self.board_offset_x + (self.width - total_width) // 2

        for i, text in enumerate(self.promotion_button_texts):
            rect = pygame.Rect(
                start_x + i * (button_width + padding),
                self.board_offset_y + self.height // 2 - button_height // 2,
                button_width, button_height)
            self.promotion_buttons.append(rect)

    def load_images(self):
        pieces = ['wp', 'wr', 'wn', 'wb', 'wq', 'wk', 'bp', 'br', 'bn', 'bb', 'bq', 'bk']
        images = {}
        base_path = os.path.dirname(os.path.abspath(__file__))
        # assets 폴더 경로 조정 (ChessGUI/assets -> ChessGUI/../assets)
        assets_path = os.path.join(base_path, '..', 'assets')
        for piece in pieces:
            path = os.path.join(assets_path, f"{piece}.png")
            if not os.path.exists(path):
                print(f"Warning: Image not found at {path}")
                continue
            images[piece] = pygame.transform.scale(pygame.image.load(path),(self.square_size, self.square_size))
        return images

    def draw(self):
        self.draw_board()
        self.draw_pieces()
        self.highlight_moves()
        if self.promotion_menu_active:
            self.draw_promotion_menu()

    def draw_board(self):
        colors = [(236, 224, 198), (168, 120, 96)]
        for row in range(8):
            for col in range(8):
                color = colors[(row + col) % 2]
                pygame.draw.rect(self.screen, color,(
                    self.board_offset_x + col * self.square_size,
                    self.board_offset_y + row * self.square_size,
                    self.square_size, self.square_size))

    def draw_pieces(self):
        for row in range(8):
            for col in range(8):
                piece = self.chess_game.board[row][col]
                if piece and piece in self.piece_images:
                    self.screen.blit(self.piece_images[piece], (
                        self.board_offset_x + col * self.square_size,
                        self.board_offset_y + row * self.square_size))

    def handle_click(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self.promotion_menu_active:
                return self.handle_promotion_click(pos)

            # 보드 영역 바깥 클릭 무시
            bx = pos[0] - self.board_offset_x
            by = pos[1] - self.board_offset_y
            if bx < 0 or by < 0 or bx >= self.width or by >= self.height:
                return None

            row, col = by // self.square_size, bx // self.square_size

            piece_on_board = self.chess.board[row][col]

            if self.selected_pos is None:
                # 기물 선택 시도
                if piece_on_board and piece_on_board[0] == self.chess.turn:
                    self.selected_pos = (row, col)
                    self.valid_moves = self.chess.get_valid_moves(row, col)
            else:
                # 선택된 기물이 있는 상태에서 클릭 (이동 시도 또는 선택 해제)
                src = self.selected_pos
                if (row, col) in self.valid_moves:
                    move_result = self.chess.move_piece(src, (row, col))
                    self.last_move = (src, (row, col))  # 네트워크 전송용

                    self.selected_pos = None
                    self.valid_moves = []

                    if move_result == True:
                        return "moved"
                    elif move_result == "promotion_pending":
                        self.promotion_menu_active = True
                        return "promotion_pending"
                    elif isinstance(move_result, tuple) and move_result[0] == "battle":
                        self.promotion_menu_active = False
                        return move_result
                    else:
                        pass
                        pass
                else:
                    # 유효한 이동이 아니거나 다른 기물을 클릭한 경우, 선택 해제
                    self.selected_pos = None
                    self.valid_moves = []
        return None

    def highlight_moves(self):
        if self.selected_pos:
            r, c = self.selected_pos
            pygame.draw.rect(self.screen, (255, 255, 0),(
                self.board_offset_x + c * self.square_size,
                self.board_offset_y + r * self.square_size,
                self.square_size, self.square_size), 3)

        for move in self.valid_moves:
            r, c = move
            if self.chess.board[r][c] and self.chess.board[r][c][0] != self.chess.turn:
                pygame.draw.rect(self.screen, (255, 0, 0),(
                    self.board_offset_x + c * self.square_size,
                    self.board_offset_y + r * self.square_size,
                    self.square_size, self.square_size), 3)
            else:
                pygame.draw.rect(self.screen, (0, 255, 0),(
                    self.board_offset_x + c * self.square_size,
                    self.board_offset_y + r * self.square_size,
                    self.square_size, self.square_size), 3)

    def draw_promotion_menu(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (self.board_offset_x, self.board_offset_y))

        for i, rect in enumerate(self.promotion_buttons):
            pygame.draw.rect(self.screen, (200, 200, 200), rect)
            text_surf = self.promotion_font.render(self.promotion_button_texts[i], True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

    def handle_promotion_click(self, pos):
        for i, rect in enumerate(self.promotion_buttons):
            if rect.collidepoint(pos):
                self.chess.promote_pawn(self.promotion_piece_types[i])
                self.promotion_menu_active = False
                return "promoted"
        return None

    def draw_game_over_message(self, message):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (self.board_offset_x, self.board_offset_y))

        text_surface = self.game_over_font.render(message, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(
            self.board_offset_x + self.width // 2,
            self.board_offset_y + self.height // 2))
        self.screen.blit(text_surface, text_rect)