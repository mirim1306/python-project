import pygame
import random

from CardGame.Card import Card, SpecialEffectProcessor, Player
from CardGame.CardGUI import CardBattleGUI


class CardBattle:
    def __init__(self, screen, player_piece_type, opponent_piece_type,
                 player_color="white", opponent_color="black",
                 player_ally_pieces=None, opponent_ally_pieces=None):
        self.screen = screen
        self.player = SpecialEffectProcessor.create_player(player_piece_type, "Player", player_color)
        self.opponent = SpecialEffectProcessor.create_player(opponent_piece_type, "Opponent", opponent_color)

        self.gui = CardBattleGUI(screen, {"player": self.player, "opponent": self.opponent})

        self.player_selected_card_index = -1
        self.player_played_card = None
        self.opponent_played_card = None

        self.turn_number = 0
        self.is_game_over = False
        self.winner = None

        self.timer_start_time = 0
        self.turn_time_limit = 10

        # 체스판 위 각 진영의 실제 기물 목록 (킹 소환에 사용)
        # 예: ['p', 'n', 'b'] — 킹 자신은 제외됨
        self.player_ally_pieces = list(player_ally_pieces) if player_ally_pieces else []
        self.opponent_ally_pieces = list(opponent_ally_pieces) if opponent_ally_pieces else []

        # 소환 기물 사망 추적: (color, piece_char) 형태로 쌓임
        # ChessCard에서 배틀 종료 후 이 목록을 읽어 체스판에서 제거
        self.dead_summoned_pieces = []

        self.game_log = []
        self._start_new_turn()

    # ─────────────────────────────────────────────────────────────────────────
    def _start_new_turn(self):
        self.turn_number += 1

        if len(self.player.hand) < 3:
            self.player.draw_card()
        if len(self.opponent.hand) < 3:
            self.opponent.draw_card()

        self.player_selected_card_index = -1
        self.player_played_card = None
        self.opponent_played_card = None

        self.player.update_statuses(self.turn_number)
        self.opponent.update_statuses(self.turn_number)
        if self.player.summoned_piece:
            self.player.summoned_piece.update_statuses(self.turn_number)
        if self.opponent.summoned_piece:
            self.opponent.summoned_piece.update_statuses(self.turn_number)

        # 상태효과 도트로 소환 기물이 죽었을 때도 체크
        self._check_summoned_piece_death(self.player)
        self._check_summoned_piece_death(self.opponent)

        self.timer_start_time = pygame.time.get_ticks()

        self.game_log.append(f"\n--- 턴 {self.turn_number} 시작 ---")
        self.game_log.append(
            f"플레이어 체력: {self.player.health}/{self.player.max_health} "
            f"공격:{self.player.attack} 방어:{self.player.defense}")
        self.game_log.append(
            f"상대방 체력: {self.opponent.health}/{self.opponent.max_health} "
            f"공격:{self.opponent.attack} 방어:{self.opponent.defense}")

    # ─────────────────────────────────────────────────────────────────────────
    def _check_summoned_piece_death(self, king_player):
        """소환 기물 체력이 0 이하면 사망 처리 및 체스판 제거 목록에 추가."""
        sp = king_player.summoned_piece
        if sp and sp.health <= 0:
            self.game_log.append(
                f"  {king_player.role}의 소환 기물({sp.piece_type.upper()}) 사망! 체스판에서 제거됩니다.")
            # color 파악: player=white, opponent=black (CardBattle 생성 시 color 인자)
            color = 'w' if king_player.role == "Player" else 'b'
            self.dead_summoned_pieces.append((color, sp.piece_type))
            king_player.summoned_piece = None

    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        running = True
        clock = pygame.time.Clock()

        while running:
            time_left = max(0.0,
                self.turn_time_limit - (pygame.time.get_ticks() - self.timer_start_time) / 1000)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"

                if not self.is_game_over:
                    if not self.player.is_status_active('stun'):
                        click_result = self.gui.handle_click(
                            event, self.gui.player_hand_rect, self.player.hand)
                        if click_result and click_result["type"] == "card_clicked":
                            if self.player_selected_card_index == -1:
                                idx = click_result["index"]
                                if 0 <= idx < len(self.player.hand):
                                    self.player_selected_card_index = idx
                                    self.game_log.append(
                                        f"플레이어가 '{self.player.hand[idx].name}' 선택.")

            card_chosen = (self.player_selected_card_index != -1
                           and self.player_played_card is None)
            time_up = (time_left <= 0 and self.player_played_card is None)

            if not self.is_game_over and (card_chosen or time_up):
                self._resolve_turn(time_left)

            if not self.is_game_over:
                self.gui.draw(
                    "Player", time_left,
                    self.player_selected_card_index,
                    self.player_played_card,
                    self.opponent_played_card
                )
                self.gui.update_log(self.game_log)
                pygame.display.flip()
            else:
                self._display_game_over_screen()
                running = False

            clock.tick(60)

        return self.winner

    # ─────────────────────────────────────────────────────────────────────────
    def _resolve_turn(self, time_left):
        player_stunned = self.player.is_status_active('stun')
        if not player_stunned and self.player_selected_card_index != -1:
            self.player_played_card = self.player.play_card(self.player_selected_card_index)
            self.game_log.append(f"플레이어: '{self.player_played_card.name}' 카드 사용.")
        else:
            self.player_played_card = None
            if player_stunned:
                self.game_log.append("플레이어: 스턴 상태 → 카드 사용 불가.")
            else:
                self.game_log.append("플레이어: 시간 초과 → 카드 없음.")

        opponent_stunned = self.opponent.is_status_active('stun')
        if not opponent_stunned and self.opponent.hand:
            opp_idx = self._opponent_ai_choose()
            self.opponent_played_card = self.opponent.play_card(opp_idx)
            self.game_log.append(f"상대방: '{self.opponent_played_card.name}' 카드 사용.")
        else:
            self.opponent_played_card = None
            self.game_log.append("상대방: 스턴 or 손패 없음 → 카드 없음.")

        self.gui.draw(
            "Player", 0,
            self.player_selected_card_index,
            self.player_played_card,
            self.opponent_played_card
        )
        pygame.display.flip()
        pygame.time.wait(1200)

        self._process_selected_cards(self.player_played_card, self.opponent_played_card)
        self._check_game_over()

        if not self.is_game_over:
            pygame.time.wait(800)
            self._start_new_turn()

    # ─────────────────────────────────────────────────────────────────────────
    def _opponent_ai_choose(self):
        hand = self.opponent.hand
        if not hand:
            return 0

        defense_indices = [i for i, c in enumerate(hand) if c.effect_type == "defense"]
        attack_indices  = [i for i, c in enumerate(hand) if c.effect_type == "attack"]
        special_indices = [i for i, c in enumerate(hand) if c.effect_type == "special"]

        hp_ratio = self.opponent.health / self.opponent.max_health if self.opponent.max_health else 1.0

        if hp_ratio < 0.30:
            if self.opponent.piece_type == 'q' and special_indices:
                return special_indices[0]
            if defense_indices:
                return random.choice(defense_indices)

        if special_indices and random.random() < 0.30:
            return random.choice(special_indices)

        if attack_indices:
            return random.choice(attack_indices)

        return random.randrange(len(hand))

    # ─────────────────────────────────────────────────────────────────────────
    def _process_selected_cards(self, player_card, opponent_card):
        self.game_log.append(f"\n--- 턴 {self.turn_number} 카드 처리 ---")
        self.game_log.append(f"  플레이어: {player_card.name if player_card else '없음'}")
        self.game_log.append(f"  상대방:   {opponent_card.name if opponent_card else '없음'}")

        p_is_defense = bool(player_card and player_card.effect_type == "defense")
        o_is_defense = bool(opponent_card and opponent_card.effect_type == "defense")

        # ── 방어 카드: 킹만 보호, 소환 기물은 항상 피해를 받음 ────────────
        if p_is_defense:
            self.player.has_100_percent_defense = True
            self.game_log.append("플레이어: 방어 카드 → 킹 모든 공격 차단 (소환 기물은 그대로 맞음).")
        if o_is_defense:
            self.opponent.has_100_percent_defense = True
            self.game_log.append("상대방: 방어 카드 → 킹 모든 공격 차단 (소환 기물은 그대로 맞음).")

        # ── 킹 체크메이트 특수 카드 먼저 처리 ────────────────────────────
        if player_card and player_card.effect_type == "special" and player_card.effect == "checkmate_summon":
            self._apply_special(player_card, self.player, self.opponent, o_is_defense, opponent_card,
                                ally_pieces=self.player_ally_pieces)

        if opponent_card and opponent_card.effect_type == "special" and opponent_card.effect == "checkmate_summon":
            self._apply_special(opponent_card, self.opponent, self.player, p_is_defense, player_card,
                                ally_pieces=self.opponent_ally_pieces)

        # ── 나머지 특수 카드: 소환 기물에 우선순위로 적용 ────────────────
        if player_card and player_card.effect_type == "special" and player_card.effect != "checkmate_summon":
            self._apply_special(player_card, self.player, self.opponent, o_is_defense, opponent_card)

        if opponent_card and opponent_card.effect_type == "special" and opponent_card.effect != "checkmate_summon":
            self._apply_special(opponent_card, self.opponent, self.player, p_is_defense, player_card)

        # ── 공격 카드 ─────────────────────────────────────────────────────
        if player_card and player_card.effect_type == "attack":
            self.game_log.append("플레이어 공격!")
            self._do_attack(attacker=self.player, defender=self.opponent)

        if opponent_card and opponent_card.effect_type == "attack":
            self.game_log.append("상대방 공격!")
            self._do_attack(attacker=self.opponent, defender=self.player)

        # 소환 기물 사망 체크
        self._check_summoned_piece_death(self.player)
        self._check_summoned_piece_death(self.opponent)

        self.game_log.append(
            f"결과 → 플레이어: {self.player.health}/{self.player.max_health}HP  "
            f"상대방: {self.opponent.health}/{self.opponent.max_health}HP")

    # ─────────────────────────────────────────────────────────────────────────
    def _apply_special(self, card, user, opponent, opponent_played_defense, opponent_card,
                       ally_pieces=None):
        """특수 카드 효과 적용.
        - opponent_played_defense: 상대가 방어 카드를 냈는지 → 특수 카드 효과(데미지/상태효과) 결정에 사용
        - 소환 기물 있음: 피해/상태효과를 소환 기물에게 적용 (방어 카드 차단 없음)
        - 소환 기물 없음: 방어 카드 있으면 킹 차단
        """
        effect_result = SpecialEffectProcessor.use(
            card.effect,
            user_player=user,
            opponent_player=opponent,
            opponent_played_defense=opponent_played_defense,  # 항상 원래 값 유지
            opponent_card_type=(opponent_card.effect_type if opponent_card else None),
            all_ally_pieces=ally_pieces if ally_pieces is not None else self.player_ally_pieces,
            current_turn_number=self.turn_number
        )

        self.game_log.extend(effect_result.get("log", []))

        has_summon = opponent.summoned_piece and opponent.summoned_piece.health > 0

        dmg = effect_result.get("damage", 0)
        if dmg > 0:
            if has_summon:
                # 소환 기물이 먼저 맞음 (방어 카드 무관)
                sp = opponent.summoned_piece
                actual = sp.take_damage(dmg, ignore_defense=effect_result.get("ignore_defense", False))
                self.game_log.append(
                    f"  → 소환({sp.piece_type.upper()})에게 즉시 {actual} 데미지. "
                    f"소환 체력: {sp.health}/{sp.max_health}")
            else:
                # 특수 카드 즉시 피해는 방어 카드와 무관하게 항상 들어감
                # (방어 카드 여부는 Card.py에서 데미지값/상태효과 결정에만 사용)
                saved = opponent.has_100_percent_defense
                opponent.has_100_percent_defense = False
                actual = opponent.take_damage(dmg, ignore_defense=effect_result.get("ignore_defense", False))
                opponent.has_100_percent_defense = saved
                self.game_log.append(
                    f"  → {opponent.role}에게 즉시 {actual} 데미지. "
                    f"체력: {opponent.health}/{opponent.max_health}")

        for status_info in effect_result.get("statuses", []):
            si = {k: v for k, v in status_info.items() if k != "target"}
            tgt = status_info.get("target", "opponent")
            if tgt == "user":
                user.apply_status(**si)
            else:
                if has_summon:
                    opponent.summoned_piece.apply_status(**si)
                else:
                    # 상태효과는 방어 카드가 있으면 차단 (상대가 방어 카드를 낸 경우 statuses가 비어있음)
                    opponent.apply_status(**si)

        if effect_result.get("card_to_add_to_hand"):
            user.hand.append(effect_result["card_to_add_to_hand"])
        if effect_result.get("card_to_add_to_deck"):
            user.deck.append(effect_result["card_to_add_to_deck"])
            random.shuffle(user.deck)

    # ─────────────────────────────────────────────────────────────────────────
    def _do_attack(self, attacker, defender):
        """공격 카드 처리.
        - 방어 카드는 킹만 보호, 소환 기물은 항상 맞음
        - 소환 기물 먼저 공격, 그 다음 킹 (킹은 방어 카드로 차단 가능)
        """
        if attacker.summoned_piece and attacker.summoned_piece.health > 0:
            sp = attacker.summoned_piece
            # 소환 기물 공격 → defender 소환 기물이 있으면 먼저 맞음, 없으면 킹 (킹은 방어 차단 가능)
            self._deal_damage(attacker=sp, defender=defender,
                              base_dmg=sp.attack,
                              label=f"{attacker.role}_소환({sp.piece_type.upper()})")
            # 킹 공격 → 킹 방어 차단 가능
            self._deal_damage(attacker=attacker, defender=defender,
                              base_dmg=attacker.attack, label=attacker.role)
        else:
            self._deal_damage(attacker=attacker, defender=defender,
                              base_dmg=attacker.attack, label=attacker.role)

        # 모든 공격 후 방어 플래그 소모
        defender.has_100_percent_defense = False

    def _deal_damage(self, attacker, defender, base_dmg, label):
        """실제 데미지 적용.
        - defender에 소환 기물 있으면 소환 기물이 먼저 맞음 (방어 카드 무관, 항상 맞음)
        - 소환 기물 없으면 킹이 맞음 (방어 카드 있으면 차단)
        """
        if defender.summoned_piece and defender.summoned_piece.health > 0:
            # 소환 기물은 방어 카드와 무관하게 항상 맞음
            sp = defender.summoned_piece
            taken = sp.take_damage(base_dmg)
            self.game_log.append(
                f"  {label} → 소환({sp.piece_type.upper()}) "
                f"{taken} 데미지. 소환 체력: {sp.health}/{sp.max_health}")
        else:
            # 소환 없음 → 킹이 맞음 (방어 카드 있으면 차단)
            if defender.has_100_percent_defense:
                self.game_log.append(f"  {label} → {defender.role} 방어 카드로 차단!")
            else:
                taken = defender.take_damage(base_dmg)
                self.game_log.append(
                    f"  {label} → {defender.role} "
                    f"{taken} 데미지. 체력: {defender.health}/{defender.max_health}")

    # ─────────────────────────────────────────────────────────────────────────
    def _check_game_over(self):
        if self.player.health <= 0:
            self.is_game_over = True
            self.winner = self.opponent
            self.game_log.append(f"플레이어 기물 사망! {self.opponent.role} 승리!")
        elif self.opponent.health <= 0:
            self.is_game_over = True
            self.winner = self.player
            self.game_log.append(f"상대방 기물 사망! {self.player.role} 승리!")

    # ─────────────────────────────────────────────────────────────────────────
    def _display_game_over_screen(self):
        self.gui.draw("Player", 0, -1, self.player_played_card, self.opponent_played_card)
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.Font(None, 72)
        msg = f"{self.winner.role} 승리!" if self.winner else "무승부!"
        text = font.render(msg, True, (255, 220, 50))
        self.screen.blit(text, text.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 2)))
        pygame.display.flip()
        pygame.time.wait(2500)