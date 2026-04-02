import pygame
import os
import sys


def resource_path(relative_path):
    """PyInstaller 번들 및 일반 실행 모두에서 올바른 절대 경로를 반환합니다."""
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

class MenuGUI:
    # 상수 정의 (가독성을 위해)
    FONT_SIZE_TITLE = 74
    FONT_SIZE_BUTTON = 50
    BUTTON_WIDTH = 200
    BUTTON_HEIGHT = 60
    BUTTON_SPACING = 20
    COLOR_BUTTON = (70, 70, 70)
    COLOR_HOVER = (100, 100, 100)
    COLOR_TEXT = (255, 255, 255)
    COLOR_BACKGROUND = (50, 50, 50)
    COLOR_TITLE = (255, 255, 0)
    COLOR_DESCRIPTION_BG = (30, 30, 30)  # 설명 화면 배경색
    COLOR_DESCRIPTION_TEXT = (200, 200, 200)  # 설명 화면 텍스트색
    DESCRIPTION_TEXT_WIDTH_LIMIT = 400
    CARDS_PER_PAGE = 1

    def __init__(self, screen, screen_width, screen_height):
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height

        project_root = resource_path("")

        font_path = resource_path(os.path.join("assets", "fonts", "OTF", "MaruBuri-Regular.otf"))

        if not os.path.exists(font_path):
            print(f"경고: 폰트 파일이 없습니다: {font_path}. 기본 폰트로 대체합니다.")
            self.font = pygame.font.Font(None, self.FONT_SIZE_TITLE)
            self.button_font = pygame.font.Font(None, self.FONT_SIZE_BUTTON)
            self.description_font = pygame.font.Font(None, 30)  # 설명 폰트 (기본)
            self.card_name_font = pygame.font.Font(None, 40)  # 카드 이름 폰트 (기본)
        else:
            print(f"DEBUG: 폰트 로드 성공: {font_path}")
            self.font = pygame.font.Font(font_path, self.FONT_SIZE_TITLE)
            self.button_font = pygame.font.Font(font_path, self.FONT_SIZE_BUTTON)
            self.description_font = pygame.font.Font(font_path, 30)  # 설명 폰트
            self.card_name_font = pygame.font.Font(font_path, 40)  # 카드 이름 폰트

        self.button_color = self.COLOR_BUTTON
        self.hover_color = self.COLOR_HOVER
        self.text_color = self.COLOR_TEXT

        # 배경 이미지
        self.background_image = None
        background_path = resource_path(os.path.join('assets', 'main_menu.png'))
        if os.path.exists(background_path):
             self.background_image = pygame.image.load(background_path).convert_alpha()
             self.background_image = pygame.transform.scale(self.background_image, (screen_width, screen_height))

        self.start_button_rect = pygame.Rect(self.screen_width // 2 - 100, self.screen_height // 2 - 25, 200, 50)

        # 아이콘 설정
        icon_image_path = resource_path(os.path.join('assets', 'main_menu.png'))

        # 파일 존재 여부 확인
        if os.path.exists(icon_image_path):
            try:
                # 이미지 로드
                game_icon_surface = pygame.image.load(icon_image_path)
                # 아이콘 설정
                pygame.display.set_icon(game_icon_surface)
                print(f"게임 아이콘 '{icon_image_path}'을(를) 성공적으로 설정했습니다.")
            except pygame.error as e:
                print(f"아이콘 이미지 로드 또는 설정 중 오류 발생: {e}")
                print(f"경고: 아이콘을 설정할 수 없습니다. '{icon_image_path}' 파일이 유효한 이미지인지 확인하세요.")
        else:
            print(f"경고: 아이콘 이미지 '{icon_image_path}'를 찾을 수 없습니다. 경로를 확인하세요.")

        self.buttons = []
        self.create_buttons()

        self.card_descriptions = self.load_card_descriptions(project_root)

        # 이미지 에셋 로드 (화살표 추가)
        self.load_assets(project_root)

        # 페이지네이션 관련 변수 추가
        self.current_page = 0
        self.total_pages = (len(self.card_descriptions) + self.CARDS_PER_PAGE - 1)
        self.current_state = "main_menu"

        # 멀티플레이 로비 관련
        self.server_ip = ""
        self.room_code_input = ""
        self.active_input = None   # "ip" or "room_code"
        self.lobby_status = ""     # 상태 메시지 표시
        self._setup_lobby_buttons()

    def load_card_descriptions(self, project_root):
        descriptions = [
            {"name": "공격 카드", "desc": "상대에게 기물 공격력만큼 데미지를 줍니다.", "image": "attack.png"},  #
            {"name": "방어 카드", "desc": "다음 공격을 100% 방어합니다.", "image": "defense.png"},  #
            {"name": "특수 카드(폰)", "desc": "형태 변화: 1턴 동안 킹을 제외한 다른 기물로 랜덤 변신. 변신한 기물의 공격력, 방어력을 적용. 카드를 사용한 자리에는 변신한 기물의 특수 카드 1장이 들어옴.", "image": "ps.png"},
            {"name": "특수 카드(룩)", "desc": "대포: 상대 카드가 방어 카드가 아닐 시 즉시 피해(+50), 상태 효과(스턴 한 턴, 화염 도트 두 턴): 스턴, 화염 도트(+5). 방어 카드일 시 즉시 피해(+30).", "image": "rs.png"},
            {"name": "특수 카드(나이트)", "desc": "돌진: 상대 카드가 방어 아닐 시 즉시 피해(+40), 상태 효과(스턴 한 턴, 방어력 0화 두 턴): 스턴, 방어력 0화. 방어 시 즉시 피해(+40).", "image": "ns.png"},
            {"name": "특수 카드(비숍)", "desc": "원소: 불, 전기, 독 중 랜덤 효과를 부여합니다. 상대 카드 종류에 따라 효과 상이.", "image": "bs.png"},
            {"name": "특수 카드(비숍)", "desc": "불 원소: 방어 카드가 아닐 시 즉시 피해(+40), 상태 효과(한 턴 동안 지속): 화염 도트 피해(+20)(상대 방어력 적용 안됨). 방어 카드일 시 즉시 피해(+40).", "image": "fc.png"},
            {"name": "특수 카드(비숍)", "desc": "전기 원소: 방어 카드가 아닐 시 즉시 피해(+20), 상태 효과(세 턴 동안 지속): 스턴(30% 확률로 턴을 쉼), 감전 피해(+5)(상대 방어력 적용 안됨). 방어 카드일 시 즉시 피해(+20).", "image": "lc.png"},
            {"name": "특수 카드(비숍)", "desc": "독 원소: 방어 카드가 아닐 시 즉시 피해(+10), 상태 효과(두 턴 동안 지속): 독 도트 피해(+10)(상대 방어력 적용 안됨), 능력치 감소: 상대 기물의 방어력, 공격력을 (-20) 방어 카드일 시 즉시 피해(+10).", "image": "pc.png"},
            {"name": "특수 카드(퀸)", "desc": "치유: 최대 체력의 5%를 두 턴마다 지속적으로 회복합니다. 최대 중첩 3회.", "image": "qs.png"},
            {"name": "특수 카드(킹)", "desc": "체크메이트: 현재 체스판에 살아있는 아군 기물을 끌어와 함께 전투. 끌려온 기물: 기존 기물의 능력치의 절반을 가지고 특수 카드 사용 불가, 죽으면 체스판에서 해당 기물 제거. 공격 우선순위: 끌려온 기물이 먼저 공격. 끌려온 기물이 죽어야 킹을 공격. 공격 카드 사용 시 킹과 끌려온 기물이 개별 공격을 가함.", "image": "ks.png"},
            {"name": "특수 카드(킹)", "desc": "능력치 강화: 끌려온 기물이 아직 죽지 않은 상태에서 다시 '체크메이트' 카드를 사용하면, 이미 끌려온 기물의 능력치가 2배로 증가. 최대 중첩 2회", "image": "ks.png"},
        ]

        self.card_images_loaded = {}
        assets_card_path = resource_path(os.path.join("assets", "cards"))
        for card_info in descriptions:
            img_path = os.path.join(assets_card_path, card_info["image"])
            try:
                image = pygame.image.load(img_path).convert_alpha()
                # 이미지 크기 조절 (설명 화면에 맞게)
                self.card_images_loaded[card_info["image"]] = pygame.transform.scale(image, (80, 110))
            except pygame.error as e:
                print(f"경고: 카드 이미지 로드 실패: {img_path} - {e}. 기본 이미지 사용.")
                # 기본 이미지 로드 (없다면 직접 생성하거나 오류 처리 필요)
                default_img = pygame.Surface((80, 110), pygame.SRCALPHA)
                pygame.draw.rect(default_img, (100, 100, 100), default_img.get_rect(), 2)
                self.card_images_loaded[card_info["image"]] = default_img

        return descriptions

    def load_assets(self, project_root):
        assets_dir = resource_path("assets")
        images_dir = os.path.join(assets_dir, "images")

        # 화살표 이미지 로드 (예시 경로, 실제 경로에 맞게 수정 필요)
        self.arrow_left_img = None
        self.arrow_right_img = None

        arrow_left_path = os.path.join(images_dir, "arrow_left.png")  # 예시 이미지 파일명
        arrow_right_path = os.path.join(images_dir, "arrow_right.png")  # 예시 이미지 파일명

        try:
            # 왼쪽 화살표
            if os.path.exists(arrow_left_path):
                self.arrow_left_img = pygame.image.load(arrow_left_path).convert_alpha()
                self.arrow_left_img = pygame.transform.scale(self.arrow_left_img, (40, 40))  # 크기 조정
            else:
                print(f"경고: 왼쪽 화살표 이미지 없음: {arrow_left_path}. 도형으로 대체.")
                self.arrow_left_img = self.create_arrow_surface("left", (255, 255, 255))  # 흰색 화살표

            # 오른쪽 화살표
            if os.path.exists(arrow_right_path):
                self.arrow_right_img = pygame.image.load(arrow_right_path).convert_alpha()
                self.arrow_right_img = pygame.transform.scale(self.arrow_right_img, (40, 40))  # 크기 조정
            else:
                print(f"경고: 오른쪽 화살표 이미지 없음: {arrow_right_path}. 도형으로 대체.")
                self.arrow_right_img = self.create_arrow_surface("right", (255, 255, 255))  # 흰색 화살표

        except pygame.error as e:
            print(f"화살표 이미지 로드 중 오류 발생: {e}. 도형으로 대체합니다.")
            self.arrow_left_img = self.create_arrow_surface("left", (255, 255, 255))
            self.arrow_right_img = self.create_arrow_surface("right", (255, 255, 255))

    def create_arrow_surface(self, direction, color, size=40):
        # 이미지가 없을 경우 화살표 도형을 그리는 함수
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        if direction == "left":
            points = [(size, 0), (0, size // 2), (size, size)]
        else:  # right
            points = [(0, 0), (size, size // 2), (0, size)]
        pygame.draw.polygon(surface, color, points)
        return surface

    def create_buttons(self):
        button_width = self.BUTTON_WIDTH
        button_height = self.BUTTON_HEIGHT
        y_start = self.screen_height // 2 - button_height * 2

        # '시작' 버튼
        self.start_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            y_start,
            button_width, button_height
        )
        self.buttons.append({"text": "시작", "rect": self.start_button_rect, "action": "show_mode_select"})

        # '설명' 버튼
        self.description_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            y_start + button_height + self.BUTTON_SPACING,
            button_width, button_height
        )
        self.buttons.append({"text": "설명", "rect": self.description_button_rect, "action": "show_description"})

        # '설정' 버튼
        self.options_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            y_start + (button_height + self.BUTTON_SPACING) * 2,
            button_width, button_height
        )
        self.buttons.append({"text": "설정", "rect": self.options_button_rect, "action": "options"})

        # '종료' 버튼
        self.exit_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            y_start + (button_height + self.BUTTON_SPACING) * 3,
            button_width, button_height
        )
        self.buttons.append({"text": "종료", "rect": self.exit_button_rect, "action": "exit_game"})

        # 설명 화면용 뒤로가기 버튼
        self.back_button_rect = pygame.Rect(
            self.screen_width - 150,
            self.screen_height - 70,
            120, 50
        )
        self.description_buttons = [{"text": "뒤로", "rect": self.back_button_rect, "action": "back_to_main_menu"}]

        # 모드 선택 화면 버튼
        mode_y = self.screen_height // 2 - button_height
        self.single_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            mode_y,
            button_width, button_height
        )
        self.multi_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            mode_y + button_height + self.BUTTON_SPACING,
            button_width, button_height
        )
        self.mode_back_button_rect = pygame.Rect(
            (self.screen_width - button_width) // 2,
            mode_y + (button_height + self.BUTTON_SPACING) * 2,
            button_width, button_height
        )
        self.mode_buttons = [
            {"text": "싱글", "rect": self.single_button_rect, "action": "start_single"},
            {"text": "멀티", "rect": self.multi_button_rect, "action": "start_multi"},
            {"text": "뒤로",       "rect": self.mode_back_button_rect, "action": "back_to_main_menu"},
        ]

    def draw(self):
        if self.current_state == "main_menu":
            self.draw_main_menu()
        elif self.current_state == "mode_select":
            self.draw_mode_select()
        elif self.current_state == "multi_lobby":
            self.draw_multi_lobby()
        elif self.current_state == "description_screen":
            self.draw_description_screen()

    def draw_outlined_text(self, font, text, color, center, outline_color=(0, 0, 0)):
        """배경과 무관하게 잘 보이도록 외곽선이 있는 텍스트를 그립니다."""
        outline = font.render(text, True, outline_color)
        main = font.render(text, True, color)
        ox = center[0] - main.get_width() // 2
        oy = center[1] - main.get_height() // 2
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
            self.screen.blit(outline, (ox + dx, oy + dy))
        self.screen.blit(main, (ox, oy))

    def draw_main_menu(self):
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill(self.COLOR_BACKGROUND)

        self.draw_outlined_text(self.font, "체스 카드 배틀", self.COLOR_TITLE,
                                (self.screen_width // 2, self.screen_height // 4))

        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            color = self.hover_color if button["rect"].collidepoint(mouse_pos) else self.button_color
            pygame.draw.rect(self.screen, color, button["rect"], border_radius=10)
            self.draw_outlined_text(self.button_font, button["text"], self.text_color,
                                    button["rect"].center)

    def draw_mode_select(self):
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill(self.COLOR_BACKGROUND)

        self.draw_outlined_text(self.font, "모드 선택", self.COLOR_TITLE,
                                (self.screen_width // 2, self.screen_height // 4))

        mouse_pos = pygame.mouse.get_pos()
        for button in self.mode_buttons:
            color = self.hover_color if button["rect"].collidepoint(mouse_pos) else self.button_color
            pygame.draw.rect(self.screen, color, button["rect"], border_radius=10)
            self.draw_outlined_text(self.button_font, button["text"], self.text_color,
                                    button["rect"].center)

    def _setup_lobby_buttons(self):
        cx = self.screen_width // 2
        bw, bh = 220, 55
        # 메인 로비 버튼
        self.lobby_quick_btn  = pygame.Rect(cx - bw // 2, 280, bw, bh)
        self.lobby_create_btn = pygame.Rect(cx - bw // 2, 360, bw, bh)
        self.lobby_join_btn   = pygame.Rect(cx - bw // 2, 440, bw, bh)
        self.lobby_back_btn   = pygame.Rect(cx - bw // 2, 540, bw, bh)
        # 입력 패널 확인/취소 버튼
        self.lobby_confirm_btn = pygame.Rect(cx - bw // 2, 520, bw, bh)
        self.lobby_cancel_btn  = pygame.Rect(cx - bw // 2, 590, 100, 44)
        # 현재 입력 패널 모드: None / "create" / "join"
        self.lobby_panel = None

    def draw_multi_lobby(self):
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
            # 배경 이미지 위에 반투명 어두운 오버레이
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(self.COLOR_BACKGROUND)

        cx = self.screen_width // 2

        # 제목
        self.draw_outlined_text(self.font, "멀티", self.COLOR_TITLE, (cx, 90))

        # 상태 메시지
        if self.lobby_status:
            self.draw_outlined_text(self.description_font, self.lobby_status, (255, 220, 80), (cx, 200))

        mouse_pos = pygame.mouse.get_pos()

        if self.lobby_panel is None:
            # ── 메인 로비 화면 ──────────────────────────────────────────
            btns = [
                (self.lobby_quick_btn,  "빠른 매칭"),
                (self.lobby_create_btn, "방 만들기"),
                (self.lobby_join_btn,   "방 참가"),
                (self.lobby_back_btn,   "뒤로"),
            ]
            for rect, text in btns:
                color = self.hover_color if rect.collidepoint(mouse_pos) else self.button_color
                pygame.draw.rect(self.screen, color, rect, border_radius=10)
                self.draw_outlined_text(self.button_font, text, self.COLOR_TEXT, rect.center)

        else:
            # ── 입력 패널 (방 참가 — 방 코드 입력) ─────────────────────
            self.draw_outlined_text(self.button_font, "방 참가", self.COLOR_TITLE, (cx, 250))

            self.draw_outlined_text(self.button_font, "방 코드", self.COLOR_TEXT, (cx - 50, 310))
            code_box = pygame.Rect(cx - 150, 330, 300, 44)
            box_color2 = (80, 80, 120) if self.active_input == "room_code" else (60, 60, 80)
            pygame.draw.rect(self.screen, box_color2, code_box, border_radius=6)
            pygame.draw.rect(self.screen, (180, 180, 255), code_box, 2, border_radius=6)
            code_surf = self.description_font.render(
                self.room_code_input + ("|" if self.active_input == "room_code" else ""), True, (255, 255, 255))
            self.screen.blit(code_surf, (code_box.x + 8, code_box.y + 10))
            self._code_box = code_box

            confirm_rect = pygame.Rect(cx - 110, 420, 100, 44)
            cancel_rect  = pygame.Rect(cx + 10,  420, 100, 44)
            for rect, text in [(confirm_rect, "확인"), (cancel_rect, "취소")]:
                color = self.hover_color if rect.collidepoint(mouse_pos) else self.button_color
                pygame.draw.rect(self.screen, color, rect, border_radius=8)
                self.draw_outlined_text(self.button_font, text, self.COLOR_TEXT, rect.center)

            self._panel_confirm_rect = confirm_rect
            self._panel_cancel_rect  = cancel_rect

    def wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        return lines

    def draw_description_screen(self):
        # 카드 설명 화면을 그립니다.
        self.screen.fill(self.COLOR_DESCRIPTION_BG)

        title_text = self.font.render("카드 설명", True, self.COLOR_TITLE)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 50))
        self.screen.blit(title_text, title_rect)

        start_x_desc = self.screen_width // 2 - 150
        content_start_y = 100
        line_height = self.description_font.get_linesize()

        # 현재 페이지에 해당하는 카드들만 가져오기
        start_index = self.current_page * self.CARDS_PER_PAGE
        end_index = min(start_index + self.CARDS_PER_PAGE, len(self.card_descriptions))  # 전체 카드 수를 넘지 않도록
        cards_to_display = self.card_descriptions[start_index:end_index]

        current_y_drawing_offset = content_start_y  # 페이지 스크롤 대신 고정 시작 위치

        for i, card_info in enumerate(cards_to_display):
            img_x = self.screen_width // 2 - 250
            img_y = current_y_drawing_offset + 10

            name_text = self.card_name_font.render(card_info["name"], True, self.COLOR_TEXT)
            name_rect = name_text.get_rect(topleft=(start_x_desc, current_y_drawing_offset + 20))

            wrapped_desc_lines = self.wrap_text(card_info["desc"], self.description_font,
                                                 self.DESCRIPTION_TEXT_WIDTH_LIMIT)

            image = self.card_images_loaded.get(card_info["image"])
            if image:
                self.screen.blit(image, (img_x, img_y))

            self.screen.blit(name_text, name_rect)

            desc_y_start = current_y_drawing_offset + 20 + name_text.get_height() + 10
            for line in wrapped_desc_lines:
                desc_line_surface = self.description_font.render(line, True, self.COLOR_DESCRIPTION_TEXT)
                self.screen.blit(desc_line_surface, (start_x_desc, desc_y_start))
                desc_y_start += line_height

            # 다음 카드 블록의 시작 위치 계산
            card_block_actual_height = max(110,
                                           name_text.get_height() + len(wrapped_desc_lines) * line_height + 10) + 20
            current_y_drawing_offset += card_block_actual_height

        # 페이지 번호 표시
        page_info_text = f"{self.current_page + 1} / {self.total_pages}"
        page_info_surface = self.button_font.render(page_info_text, True, self.COLOR_TEXT)
        page_info_rect = page_info_surface.get_rect(center=(self.screen_width // 2, self.screen_height - 45))
        self.screen.blit(page_info_surface, page_info_rect)

        # 뒤로 버튼 그리기
        mouse_pos = pygame.mouse.get_pos()
        for button in self.description_buttons:
            current_color = self.button_color
            if button["rect"].collidepoint(mouse_pos):
                current_color = self.hover_color

            pygame.draw.rect(self.screen, current_color, button["rect"], border_radius=10)
            button_text_surface = self.button_font.render(button["text"], True, self.text_color)
            button_text_rect = button_text_surface.get_rect(center=button["rect"].center)
            self.screen.blit(button_text_surface, button_text_rect)

        # 화살표 버튼 그리기 및 활성화/비활성화 처리
        arrow_button_size = 40  # 화살표 이미지 크기
        arrow_padding = 10  # 페이지 정보 텍스트와 화살표 사이 간격

        # 왼쪽 화살표 (이전 페이지)
        if self.arrow_left_img:
            # 화살표 이미지를 page_info_rect 왼쪽에 배치
            prev_arrow_x = page_info_rect.left - arrow_button_size - arrow_padding
            prev_arrow_y = page_info_rect.centery - arrow_button_size // 2
            self.prev_arrow_rect = pygame.Rect(prev_arrow_x, prev_arrow_y, arrow_button_size, arrow_button_size)

            display_arrow_left = self.arrow_left_img.copy()
            if self.current_page <= 0:  # 첫 페이지이면 비활성화
                display_arrow_left.fill((128, 128, 128, 255), special_flags=pygame.BLEND_MULT)  # 어둡게 만듦

            self.screen.blit(display_arrow_left, self.prev_arrow_rect.topleft)
        else:  # 이미지가 없으면 도형으로 그림 (대체 로직)
            self.prev_arrow_rect = pygame.Rect(page_info_rect.left - arrow_button_size - arrow_padding, page_info_rect.centery - arrow_button_size // 2, arrow_button_size, arrow_button_size)
            arrow_color = self.COLOR_TEXT
            if self.current_page <= 0:
                arrow_color = (128, 128, 128)  # 비활성화 색
            pygame.draw.polygon(self.screen, arrow_color,[(self.prev_arrow_rect.right, self.prev_arrow_rect.top), (self.prev_arrow_rect.left, self.prev_arrow_rect.centery), (self.prev_arrow_rect.right, self.prev_arrow_rect.bottom)])

        # 오른쪽 화살표 (다음 페이지)
        if self.arrow_right_img:
            next_arrow_x = page_info_rect.right + arrow_padding
            next_arrow_y = page_info_rect.centery - arrow_button_size // 2
            self.next_arrow_rect = pygame.Rect(next_arrow_x, next_arrow_y, arrow_button_size, arrow_button_size)

            display_arrow_right = self.arrow_right_img.copy()
            if self.current_page >= self.total_pages - 1:  # 마지막 페이지이면 비활성화
                display_arrow_right.fill((128, 128, 128, 255), special_flags=pygame.BLEND_MULT)  # 어둡게 만듦

            self.screen.blit(display_arrow_right, self.next_arrow_rect.topleft)
        else:  # 이미지가 없으면 도형으로 그림 (대체 로직)
            self.next_arrow_rect = pygame.Rect(
                page_info_rect.right + arrow_padding,
                page_info_rect.centery - arrow_button_size // 2,
                arrow_button_size, arrow_button_size
            )
            arrow_color = self.COLOR_TEXT
            if self.current_page >= self.total_pages - 1:
                arrow_color = (128, 128, 128)  # 비활성화 색
            pygame.draw.polygon(self.screen, arrow_color,[(self.next_arrow_rect.left, self.next_arrow_rect.top), (self.next_arrow_rect.right, self.next_arrow_rect.centery), (self.next_arrow_rect.left, self.next_arrow_rect.bottom)])

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.current_state == "main_menu":
                for button in self.buttons:
                    if button["rect"].collidepoint(event.pos):
                        if button["action"] == "show_mode_select":
                            self.current_state = "mode_select"
                            return None
                        elif button["action"] == "show_description":
                            self.current_state = "description_screen"
                            self.current_page = 0
                            return None
                        return button["action"]

            elif self.current_state == "mode_select":
                for button in self.mode_buttons:
                    if button["rect"].collidepoint(event.pos):
                        if button["action"] == "back_to_main_menu":
                            self.current_state = "main_menu"
                            return None
                        elif button["action"] == "start_multi":
                            self.current_state = "multi_lobby"
                            self.lobby_status = ""
                            return None
                        return button["action"]

            elif self.current_state == "multi_lobby":
                if self.lobby_panel is None:
                    if self.lobby_quick_btn.collidepoint(event.pos):
                        return {"action": "multi_quick"}
                    elif self.lobby_create_btn.collidepoint(event.pos):
                        return {"action": "multi_create"}
                    elif self.lobby_join_btn.collidepoint(event.pos):
                        self.lobby_panel = "join"
                        self.active_input = "room_code"
                        self.room_code_input = ""
                    elif self.lobby_back_btn.collidepoint(event.pos):
                        self.current_state = "mode_select"
                        self.lobby_status = ""
                        self.active_input = None
                else:
                    # 입력창 클릭 (방 참가 시 방 코드)
                    if hasattr(self, '_code_box') and self._code_box and self._code_box.collidepoint(event.pos):
                        self.active_input = "room_code"
                    # 확인/취소
                    elif hasattr(self, '_panel_confirm_rect') and self._panel_confirm_rect.collidepoint(event.pos):
                        code = self.room_code_input.strip()
                        if not code:
                            self.lobby_status = "방 코드를 입력해주세요."
                        else:
                            self.lobby_panel = None
                            self.active_input = None
                            return {"action": "multi_join", "code": code}
                    elif hasattr(self, '_panel_cancel_rect') and self._panel_cancel_rect.collidepoint(event.pos):
                        self.lobby_panel = None
                        self.active_input = None
                        self.lobby_status = ""

            elif self.current_state == "description_screen":
                    # 뒤로가기 버튼 처리
                    for button in self.description_buttons:
                        if button["rect"].collidepoint(event.pos):
                            if button["action"] == "back_to_main_menu":
                                self.current_state = "main_menu"
                            return button["action"]

                    # 화살표 버튼 처리
                    if hasattr(self, 'prev_arrow_rect') and self.prev_arrow_rect.collidepoint(event.pos):
                        if self.current_page > 0:
                            self.current_page -= 1
                            print(f"DEBUG: 이전 페이지로 이동. 현재 페이지: {self.current_page + 1}/{self.total_pages}")
                    elif hasattr(self, 'next_arrow_rect') and self.next_arrow_rect.collidepoint(event.pos):
                        if self.current_page < self.total_pages - 1:
                            self.current_page += 1
                            print(f"DEBUG: 다음 페이지로 이동. 현재 페이지: {self.current_page + 1}/{self.total_pages}")

        if event.type == pygame.KEYDOWN and self.current_state == "multi_lobby":
            if self.active_input == "room_code":
                if event.key == pygame.K_BACKSPACE:
                    self.room_code_input = self.room_code_input[:-1]
                elif len(self.room_code_input) < 6 and event.unicode.isalnum():
                    self.room_code_input += event.unicode.upper()

        return None