import pygame
import os

class CardBattleGUI:
    def __init__(self, screen, players):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.players = players

        self.summoned_image_size = (75, 75)

        # 색상 정의 (기존과 동일)
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (100, 100, 100)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        self.YELLOW = (255, 255, 0)
        self.LIGHT_BLUE = (173, 216, 230)  # 카드 공개 배경색

        self.font_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts', 'OTF', 'MaruBuri-Regular.otf')
        try:
            self.large_font = pygame.font.Font(self.font_path, 38)
            self.medium_font = pygame.font.Font(self.font_path, 22)
            self.small_font = pygame.font.Font(self.font_path, 17)
            self.card_desc_font = pygame.font.Font(self.font_path, 14)
        except FileNotFoundError:
            print(f"폰트 파일 '{self.font_path}'을(를) 찾을 수 없습니다. 기본 폰트를 사용합니다.")
            self.large_font = pygame.font.Font(None, 38)
            self.medium_font = pygame.font.Font(None, 22)
            self.small_font = pygame.font.Font(None, 17)
            self.card_desc_font = pygame.font.Font(None, 14)

        # 상단 능력치 정보 창
        self.player_info_rect = pygame.Rect(50, 20, 320, 155)
        self.opponent_info_rect = pygame.Rect(self.width - 50 - 320, 20, 320, 155)

        # 기물 이미지 영역
        self.player_piece_rect = pygame.Rect(self.player_info_rect.centerx - 60, self.player_info_rect.bottom + 10, 120, 120)
        self.opponent_piece_rect = pygame.Rect(self.opponent_info_rect.centerx - 60, self.opponent_info_rect.bottom + 10, 120, 120)

        # 소환된 기물 표시 위치
        self.summoned_player_display_rect = pygame.Rect(self.player_piece_rect.right + 20, self.player_piece_rect.top + 20, 95, 95)
        self.summoned_opponent_display_rect = pygame.Rect(self.opponent_piece_rect.left - 95 - 20, self.opponent_piece_rect.top + 20, 95, 95)

        # 선택한 카드 영역 (중앙)
        self.played_card_display_rect = pygame.Rect(self.width / 2 - 145, 310, 290, 230)

        # 손패 영역 (하단)
        self.player_hand_rect = pygame.Rect(50, self.height - 210, self.width - 100, 180)
        self.opponent_hand_rect = pygame.Rect(50, self.height - 210, self.width - 100, 180)

        # 카드 설명창
        self.card_description_rect = pygame.Rect(self.width / 2 + 120, self.height - 280, 230, 120)

        # 이미지 로드 및 속성 초기화 추가
        self.piece_images = self._load_piece_images()
        self.card_images = self._load_card_images()
        self.card_back_image = self.card_images["default_card"] # 임시로 기본 카드 이미지를 뒷면으로 사용

        self.game_log_display = [] # 로그 표시를 위한 리스트 (업데이트 필요)

    def _load_image(self, path, size=None):
        try:
            full_path = os.path.join(os.path.dirname(__file__), '..', path)
            image = pygame.image.load(full_path).convert_alpha()
            if size:
                image = pygame.transform.scale(image, size)
            return image
        except pygame.error as e:
            print(f"이미지 로드 오류: {full_path} - {e}")
            return pygame.Surface(size if size else (50, 50), pygame.SRCALPHA)

    def _load_piece_images(self):
        piece_size = (120, 120)
        summoned_piece_size = self.summoned_image_size

        images_config = {
            "p": {"w": "wp.png", "b": "bp.png"},
            "r": {"w": "wr.png", "b": "br.png"},
            "n": {"w": "wn.png", "b": "bn.png"},
            "b": {"w": "wb.png", "b": "bb.png"},
            "q": {"w": "wq.png", "b": "bq.png"},
            "k": {"w": "wk.png", "b": "bk.png"},
        }

        loaded_images = {}
        for piece_type_key, colors_dict in images_config.items():
            loaded_images[piece_type_key] = {}
            for color_key, filename in colors_dict.items():
                # 이미지 경로를 'assets/' 접두사와 결합
                loaded_images[piece_type_key][color_key] = self._load_image(os.path.join("assets", filename), piece_size)
                loaded_images[piece_type_key][f"summoned_{color_key}"] = self._load_image(os.path.join("assets", filename), summoned_piece_size)
        return loaded_images

    def _load_card_images(self):
        card_size = (100, 145)
        # 카드 이미지 경로
        images = {
            "attack": self._load_image("assets/cards/attack.png", card_size),
            "defense": self._load_image("assets/cards/defense.png", card_size),
            "ps": self._load_image("assets/cards/ps.png", card_size), # 카드 이름 매칭 확인
            "rs": self._load_image("assets/cards/rs.png", card_size),
            "ns": self._load_image("assets/cards/ns.png", card_size),
            "bs": self._load_image("assets/cards/bs.png", card_size),
            "qs": self._load_image("assets/cards/qs.png", card_size),
            "ks": self._load_image("assets/cards/ks.png", card_size),
            "default_card": self._load_image("assets/card.png", card_size)
        }
        return images

    def draw(self, current_turn_role, time_left, player_selected_card_index, player_played_card, opponent_played_card):
        self.screen.fill(self.GRAY)

        # 1. 상단 능력치 정보 창 그리기
        self._draw_player_info(
            self.players["player"],
            self.player_info_rect,
            self.players["player"].health,
            self.players["player"].attack,
            self.players["player"].defense,
            self.players["player"].statuses
        )

        self._draw_player_info(
            self.players["opponent"],
            self.opponent_info_rect,
            self.players["opponent"].health,
            self.players["opponent"].attack,
            self.players["opponent"].defense,
            self.players["opponent"].statuses
        )

        # 2. 기물 이미지 그리기
        self._draw_piece_image(self.players["player"].piece_type, "w", self.player_piece_rect, is_summoned=False)
        self._draw_piece_image(self.players["opponent"].piece_type, "b", self.opponent_piece_rect, is_summoned=False)


        # 3. '선택한 카드' 영역
        self._draw_played_cards_area(int(time_left), player_played_card, opponent_played_card)

        # 4. 플레이어 손패 그리기
        self.hovered_card = None
        self._draw_hand(self.players["player"].hand, self.player_hand_rect, "player", show_cards=True, selected_index=player_selected_card_index)

        # 5. 소환된 기물 표시 및 능력치 창
        self._draw_summoned_piece(self.players["player"], "player", self.summoned_player_display_rect)
        self._draw_summoned_piece(self.players["opponent"], "opponent", self.summoned_opponent_display_rect)

        # 6. 마우스 오버 시 카드 설명 (손패를 그린 후에 호출되어야 함)
        self._draw_card_hover_description()

    def _draw_summoned_piece(self, player_obj, role_key, display_rect):
        if player_obj.summoned_piece:
            summoned_piece = player_obj.summoned_piece

            color_key = "w" if role_key == "player" else "b"
            image_key = f"summoned_{color_key}"

            piece_image = self.piece_images.get(summoned_piece.piece_type, {}).get(image_key)

            if piece_image:
                # 중앙 정렬
                self.screen.blit(piece_image, piece_image.get_rect(center=display_rect.center))
            else:
                print(f"경고: 소환된 {summoned_piece.piece_type} ({image_key}) 기물 이미지를 찾을 수 없습니다.")
                # 이미지가 없을 경우 대체 사각형이나 텍스트를 그릴 수 있습니다.
                pygame.draw.rect(self.screen, self.BLUE, display_rect, border_radius=5)
                text_surface = self.small_font.render(f"{summoned_piece.piece_type.upper()}", True, self.BLACK)
                self.screen.blit(text_surface, text_surface.get_rect(center=display_rect.center))

            # 소환된 기물 능력치 표시 배경
            info_bg_width = display_rect.width + 20
            info_bg_height = (self.small_font.get_height() * 4) + 10
            info_bg_rect = pygame.Rect(display_rect.left - 10, display_rect.bottom + 5, info_bg_width, info_bg_height)

            pygame.draw.rect(self.screen, self.WHITE, info_bg_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.BLACK, info_bg_rect, 1, border_radius=5)

            current_y = info_bg_rect.top + 5

            # 이름
            name_text = self.small_font.render(f"{summoned_piece.role}", True, self.BLACK)
            self.screen.blit(name_text, (info_bg_rect.left + 5, current_y))
            current_y += name_text.get_height() + 2

            # 체력
            health_color = (0, 255, 0) if summoned_piece.health > summoned_piece.max_health / 2 else (
            255, 255, 0) if summoned_piece.health > summoned_piece.max_health / 4 else (255, 0, 0)
            health_text = self.small_font.render(f"체력: {summoned_piece.health}/{summoned_piece.max_health}", True,
                                                 health_color)
            self.screen.blit(health_text, (info_bg_rect.left + 5, current_y))
            current_y += health_text.get_height() + 2

            # 공격력
            attack_text = self.small_font.render(f"공격력: {summoned_piece.attack}", True, self.BLACK)
            self.screen.blit(attack_text, (info_bg_rect.left + 5, current_y))
            current_y += attack_text.get_height() + 2

            # 방어력
            defense_text = self.small_font.render(f"방어력: {summoned_piece.defense}", True, self.BLACK)
            self.screen.blit(defense_text, (info_bg_rect.left + 5, current_y))

    def _draw_player_info(self, player_obj, rect, current_hp, current_attack, current_defense, statuses):
        pygame.draw.rect(self.screen, self.WHITE, rect, border_radius=10)
        pygame.draw.rect(self.screen, self.BLACK, rect, 2, border_radius=10)

        # 플레이어 이름/역할
        role_text_surf = self.medium_font.render(player_obj.role, True, self.BLACK)
        role_text_rect = role_text_surf.get_rect(topleft=(rect.left + 10, rect.top + 5))
        self.screen.blit(role_text_surf, role_text_rect)

        # 체력 바
        hp_bar_bg_rect = pygame.Rect(rect.left + 10, role_text_rect.bottom + 5, rect.width - 20, 20)
        pygame.draw.rect(self.screen, self.RED, hp_bar_bg_rect, border_radius=5)

        hp_bar_width = int((current_hp / player_obj.max_health) * hp_bar_bg_rect.width)
        hp_bar_rect = pygame.Rect(hp_bar_bg_rect.left, hp_bar_bg_rect.top, hp_bar_width, hp_bar_bg_rect.height)
        pygame.draw.rect(self.screen, self.GREEN, hp_bar_rect, border_radius=5)

        hp_text = self.small_font.render(f"체력: {current_hp}/{player_obj.max_health}", True, self.WHITE)
        hp_text_rect = hp_text.get_rect(center=hp_bar_bg_rect.center)
        self.screen.blit(hp_text, hp_text_rect)

        # 공격력, 방어력 텍스트
        attack_text = self.small_font.render(f"공격력: {current_attack}", True, self.BLACK)
        attack_rect = attack_text.get_rect(topleft=(rect.left + 10, hp_bar_bg_rect.bottom + 5))
        self.screen.blit(attack_text, attack_rect)

        defense_text = self.small_font.render(f"방어력: {current_defense}", True, self.BLACK)
        defense_rect = defense_text.get_rect(topleft=(rect.left + 10, attack_rect.bottom + 5))
        self.screen.blit(defense_text, defense_rect)

        # 상태 효과 텍스트 (줄바꿈 처리 개선)
        status_text_prefix = self.small_font.render(f"상태: ", True, self.BLACK)
        status_prefix_rect = status_text_prefix.get_rect(topleft=(rect.left + 10, defense_rect.bottom + 5))
        self.screen.blit(status_text_prefix, status_prefix_rect)

        status_names = []
        # 상태 이름 매핑을 위한 딕셔너리
        status_display_map = {
            'stun': '스턴', 'poison': '독', 'fire_dot': '화상',
            'electric_dot': '감전', 'defense_zero': '방어력0',
            'stat_debuff': '능력감소', 'periodic_heal': '지속치유'
        }

        for status in statuses:
            if status['duration'] > 0:
                display_name = status_display_map.get(status['type'], status['type'])
                status_names.append(display_name)

        combined_status_text = ", ".join(status_names) if status_names else "없음"

        status_start_x = status_prefix_rect.right
        status_start_y = status_prefix_rect.top
        max_line_width = rect.width - (status_start_x - rect.left) - 10

        # 줄바꿈
        wrapped_lines = self._wrap_text(combined_status_text, self.small_font, max_line_width)

        current_y_for_status = status_start_y
        for line in wrapped_lines:
            line_surf = self.small_font.render(line, True, self.BLUE)
            self.screen.blit(line_surf, (status_start_x, current_y_for_status))
            current_y_for_status += self.small_font.get_height()  # 다음 줄 위치

    def _draw_piece_image(self, piece_type, color_key, rect, is_summoned=False):
        if is_summoned:
            image_key = f"summoned_{color_key}"
        else:
            image_key = color_key

        piece_image = self.piece_images.get(piece_type, {}).get(image_key)

        if piece_image:
            self.screen.blit(piece_image, piece_image.get_rect(center=rect.center))
        else:
            print(f"경고: {piece_type} ({image_key}) 기물 이미지를 찾을 수 없습니다.")
            # 이미지가 없을 경우 대체 사각형이나 텍스트를 그릴 수 있습니다.
            pygame.draw.rect(self.screen, self.BLUE, rect, border_radius=5)
            text_surface = self.medium_font.render(f"{piece_type.upper()}", True, self.WHITE)
            self.screen.blit(text_surface, text_surface.get_rect(center=rect.center))


    def _draw_hand(self, hand_cards, hand_rect, role, show_cards=True, selected_index=-1):
        card_padding = 12
        card_width = 100

        total_card_width = len(hand_cards) * card_width + (len(hand_cards) - 1) * card_padding
        start_x = hand_rect.centerx - total_card_width / 2
        start_y = hand_rect.top

        mouse_pos = pygame.mouse.get_pos()

        for i, card in enumerate(hand_cards):
            card_x = start_x + (card_width + card_padding) * i
            card_y = start_y

            card_image = None
            if show_cards:
                # Card 객체의 name 속성과 card_images 딕셔너리의 키가 일치해야 합니다.
                card_image = self.card_images.get(card.name, self.card_images["default_card"])
            else:
                card_image = self.card_back_image

            card_rect = card_image.get_rect(topleft=(card_x, card_y))

            if i == selected_index:
                # 선택된 카드에 노란색 테두리
                pygame.draw.rect(self.screen, self.YELLOW, card_rect, 3, border_radius=5)

            self.screen.blit(card_image, card_rect)

            # 마우스 오버 감지
            if card_rect.collidepoint(mouse_pos):
                self.hovered_card = card


    def _draw_played_cards_area(self, time_left, player_played_card, opponent_played_card):
        pygame.draw.rect(self.screen, self.WHITE, self.played_card_display_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.BLACK, self.played_card_display_rect, 2, border_radius=10)

        timer_text = self.large_font.render(f"남은 시간: {time_left}초", True, self.BLACK)
        timer_rect = timer_text.get_rect(center=(self.played_card_display_rect.centerx, self.played_card_display_rect.top + 20))
        self.screen.blit(timer_text, timer_rect)

        # '선택한 카드' 레이블을 더 명확하게 플레이어/상대방으로 나눕니다.
        player_label = self.medium_font.render("플레이어", True, self.BLACK)
        opponent_label = self.medium_font.render("상대방", True, self.BLACK)

        card_display_size = (100, 145)
        card_y_pos = timer_rect.bottom + 20

        # 플레이어 레이블 및 카드
        player_label_x = self.played_card_display_rect.centerx - card_display_size[0] - 5 - (player_label.get_width() / 2) + (card_display_size[0] / 2)
        player_label_rect = player_label.get_rect(centerx=self.played_card_display_rect.centerx - card_display_size[0] / 2 - 5, top=card_y_pos - 20)
        self.screen.blit(player_label, player_label_rect)

        if player_played_card:
            player_card_image = self.card_images.get(player_played_card.name, self.card_images["default_card"])
            player_card_rect = player_card_image.get_rect(topleft=(self.played_card_display_rect.centerx - card_display_size[0] - 5, card_y_pos))
            self.screen.blit(player_card_image, player_card_rect)
        else:
            empty_card_image = self.card_images["default_card"]
            empty_card_rect = empty_card_image.get_rect(topleft=(self.played_card_display_rect.centerx - card_display_size[0] - 5, card_y_pos))
            self.screen.blit(empty_card_image, empty_card_rect)

        # 상대방 레이블 및 카드
        opponent_label_x = self.played_card_display_rect.centerx + 5 + (opponent_label.get_width() / 2) - (card_display_size[0] / 2)
        opponent_label_rect = opponent_label.get_rect(centerx=self.played_card_display_rect.centerx + card_display_size[0] / 2 + 5, top=card_y_pos - 20)
        self.screen.blit(opponent_label, opponent_label_rect)

        if opponent_played_card:
            opponent_card_image = self.card_images.get(opponent_played_card.name, self.card_images["default_card"])
            opponent_card_rect = opponent_card_image.get_rect(topleft=(self.played_card_display_rect.centerx + 5, card_y_pos))
            self.screen.blit(opponent_card_image, opponent_card_rect)
        else:
            empty_card_image = self.card_images["default_card"]
            empty_card_rect = empty_card_image.get_rect(topleft=(self.played_card_display_rect.centerx + 5, card_y_pos))
            self.screen.blit(empty_card_image, empty_card_rect)
            no_card_text = self.small_font.render("", True, self.RED)
            self.screen.blit(no_card_text, no_card_text.get_rect(center=empty_card_rect.center))

    def _draw_card_hover_description(self, ):
        if self.hovered_card:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            desc_width = 200
            desc_height = 100

            # 설명창이 화면 밖으로 나가지 않도록 조정
            desc_x = mouse_x + 15
            if desc_x + desc_width > self.width:
                desc_x = mouse_x - desc_width - 15
                if desc_x < 0: # 왼쪽으로도 너무 벗어나면 중앙에서 시작
                    desc_x = (self.width - desc_width) / 2

            desc_y = mouse_y + 15
            if desc_y + desc_height > self.height:
                desc_y = mouse_y - desc_height - 15
                if desc_y < 0: # 위로도 너무 벗어나면 중앙에서 시작
                    desc_y = (self.height - desc_height) / 2

            description_rect = pygame.Rect(desc_x, desc_y, desc_width, desc_height)

            pygame.draw.rect(self.screen, self.WHITE, description_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.BLACK, description_rect, 2, border_radius=5)

            name_surf = self.medium_font.render(self.hovered_card.name, True, self.BLACK)
            self.screen.blit(name_surf, (description_rect.left + 5, description_rect.top + 5))

            type_surf = self.small_font.render(f"종류: {self.hovered_card.effect_type}", True, self.GRAY)
            self.screen.blit(type_surf, (description_rect.left + 5, description_rect.top + 5 + name_surf.get_height() + 5))

            available_desc_height = description_rect.height - (name_surf.get_height() + type_surf.get_height() + 20)
            text_y = description_rect.top + 5 + name_surf.get_height() + type_surf.get_height() + 10

            wrapped_desc_lines = self._wrap_text(self.hovered_card.description, self.card_desc_font, description_rect.width - 10)

            max_lines = int(available_desc_height / self.card_desc_font.get_height())
            for i, line in enumerate(wrapped_desc_lines):
                if i >= max_lines:
                    break
                desc_surf = self.card_desc_font.render(line, True, self.BLACK)
                self.screen.blit(desc_surf, (description_rect.left + 5, text_y))
                text_y += desc_surf.get_height()

    def _wrap_text(self, text, font, max_width):
        # 텍스트를 주어진 폭에 맞춰 줄바꿈합니다.
        words = text.split(' ')
        lines = []
        if not words:
            return lines

        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.render(test_line, True, self.BLACK).get_width() > max_width:
                if current_line:
                    lines.append(' '.join(current_line))
                # 한 단어가 max_width를 초과하는 경우, 그 단어만으로 새 줄 시작
                # 이 로직은 단어가 너무 길 경우 잘리지 않고 한 줄 전체를 차지하게 합니다.
                lines.append(word)
                current_line = []
            else:
                current_line.append(word)

        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def handle_click(self, event, hand_rect, hand_cards):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            card_width = 100
            card_spacing = 12

            if hand_rect.collidepoint(mouse_pos):
                total_card_width = len(hand_cards) * card_width + (len(hand_cards) - 1) * card_spacing
                start_x = hand_rect.centerx - total_card_width / 2

                for i, card in enumerate(hand_cards):
                    card_x = start_x + (card_width + card_spacing) * i
                    card_y = hand_rect.top

                    card_rect = pygame.Rect(card_x, card_y, card_width, 145)
                    if card_rect.collidepoint(mouse_pos):
                        return {"type": "card_clicked", "index": i}
        return None

    def update_log(self, game_log_list):
        # 게임 로그를 업데이트합니다.
        self.game_log_display = game_log_list[-20:] # 최신 20줄만 유지

    def _draw_log(self):
        # 게임 로그를 화면에 그립니다.
        log_bg_rect = self.log_rect
        pygame.draw.rect(self.screen, self.DARK_GRAY, log_bg_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.WHITE, log_bg_rect, 1, border_radius=5)

        current_y = log_bg_rect.top + 5
        for line in self.game_log_display:
            log_surf = self.log_font.render(line, True, self.WHITE)
            self.screen.blit(log_surf, (log_bg_rect.left + 5, current_y))
            current_y += self.log_font.get_height() + 2 # 줄 간격

    def get_hovered_card(self):
        return self.hovered_card