import pygame
import random

from .Card import Card, SpecialEffectProcessor, Player
from .CardGUI import CardBattleGUI


class CardBattle:
    def __init__(self, screen, player_piece_type, opponent_piece_type,
                 player_color="white", opponent_color="black",
                 player_ally_pieces=None, opponent_ally_pieces=None,
                 net=None, is_master=True):
        self.screen = screen
        self.net = net          # 멀티넷용 NetworkClient (None이면 싱글/AI)
        self.is_master = is_master  # True: 계산 담당 / False: 카드만 전송
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

        self.player_ally_pieces = list(player_ally_pieces) if player_ally_pieces else []
        self.opponent_ally_pieces = list(opponent_ally_pieces) if opponent_ally_pieces else []

        self.dead_summoned_pieces = []

        self.game_log = []
        self._net_recv = None   # 네트워크로 수신한 메시지 저장
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
        sp = king_player.summoned_piece
        if sp and sp.health <= 0:
            self.game_log.append(
                f"  {king_player.role}의 소환 기물({sp.piece_type.upper()}) 사망! 체스판에서 제거됩니다.")
            color = 'w' if king_player.role == "Player" else 'b'
            self.dead_summoned_pieces.append((color, sp.piece_type))
            king_player.summoned_piece = None

    # ─────────────────────────────────────────────────────────────────────────
    def _poll_net(self):
        """네트워크 메시지를 폴링해서 card_action을 _net_recv에 저장."""
        if self.net and self.net.connected and self._net_recv is None:
            for msg in self.net.poll():
                if msg.get("type") == "card_action":
                    self._net_recv = msg
                    break

    # ─────────────────────────────────────────────────────────────────────────
    def _wait_for_net(self, timeout_ms=15000):
        """상대방 card_action 메시지가 올 때까지 대기. 수신된 메시지 반환."""
        wait_start = pygame.time.get_ticks()
        while True:
            if self._net_recv is not None:
                result = self._net_recv
                self._net_recv = None
                return result
            if pygame.time.get_ticks() - wait_start > timeout_ms:
                return None
            self._poll_net()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
            pygame.time.wait(30)

    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        running = True
        clock = pygame.time.Clock()

        while running:
            time_left = max(0.0,
                self.turn_time_limit - (pygame.time.get_ticks() - self.timer_start_time) / 1000)

            # 네트워크 메시지 미리 폴링
            self._poll_net()

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
        # ── 내 카드 결정 ──────────────────────────────────────────────────
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

        # ── 멀티넷 ────────────────────────────────────────────────────────
        if self.net and self.net.connected:
            my_card_idx = self.player_selected_card_index  # 이미 play_card로 손패에서 제거됨

            if self.is_master:
                # 마스터: 상대 카드 인덱스 수신 대기 → 계산 → 결과 전송
                recv = self._wait_for_net()
                opp_idx = recv.get("card_idx", -1) if recv else -1

                opponent_stunned = self.opponent.is_status_active('stun')
                if not opponent_stunned and opp_idx != -1 and 0 <= opp_idx < len(self.opponent.hand):
                    self.opponent_played_card = self.opponent.play_card(opp_idx)
                else:
                    self.opponent_played_card = None
                self.game_log.append(
                    f"상대방: '{self.opponent_played_card.name if self.opponent_played_card else '없음'}' 카드 사용.")

                # 내 카드 인덱스 전송 (슬레이브가 화면에 표시하도록)
                self.net.send_card_action({
                    "card_idx": my_card_idx,
                    "player_card": self.player_played_card.name if self.player_played_card else "none",
                    "opponent_card": self.opponent_played_card.name if self.opponent_played_card else "none",
                })

            else:
                # 슬레이브: 내 카드 인덱스 전송 → 마스터 결과 수신
                self.net.send_card_action({"card_idx": my_card_idx})

                recv = self._wait_for_net()
                if recv:
                    # 마스터가 보낸 결과로 화면 표시용 카드 설정
                    p_name = recv.get("player_card", "none")
                    o_name = recv.get("opponent_card", "none")
                    # 슬레이브 입장에서 player=상대방, opponent=나
                    # 화면 표시만 맞추면 되므로 이름으로 더미 카드 생성
                    self.opponent_played_card = Card(o_name, 0, "attack", "") if o_name != "none" else None
                    # player_played_card는 이미 위에서 설정됨
                    self.game_log.append(
                        f"상대방: '{self.opponent_played_card.name if self.opponent_played_card else '없음'}' 카드 사용.")

                    # 슬레이브는 실제 전투 계산을 건너뜀 (마스터가 이미 계산)
                    self.gui.draw("Player", 0, self.player_selected_card_index,
                                  self.player_played_card, self.opponent_played_card)
                    pygame.display.flip()
                    pygame.time.wait(1200)

                    # 마스터로부터 턴 결과(전체 상태) 수신
                    recv2 = self._wait_for_net()
                    if recv2 and recv2.get("type2") == "turn_result":
                        # 슬레이브 입장에서 player=상대방(마스터의 opponent), opponent=나(마스터의 player)
                        # 마스터가 보낸 player_state = 마스터 자신(슬레이브의 opponent)
                        # 마스터가 보낸 opponent_state = 슬레이브 자신(슬레이브의 player)
                        def _apply_state(target, state):
                            if not state:
                                return
                            target.health = state.get("health", target.health)
                            target.max_health = state.get("max_health", target.max_health)
                            target.attack = state.get("attack", target.attack)
                            target.defense = state.get("defense", target.defense)
                            target.piece_type = state.get("piece_type", target.piece_type)
                            target.statuses = state.get("statuses", target.statuses)
                            target.heal_stack_count = state.get("heal_stack_count", target.heal_stack_count)
                            target.summon_boost_count = state.get("summon_boost_count", target.summon_boost_count)
                            sp_data = state.get("summoned_piece")
                            if sp_data:
                                if not target.summoned_piece:
                                    target.summoned_piece = SpecialEffectProcessor.create_piece_player(
                                        sp_data["piece_type"])
                                target.summoned_piece.piece_type = sp_data["piece_type"]
                                target.summoned_piece.attack = sp_data["attack"]
                                target.summoned_piece.defense = sp_data["defense"]
                                target.summoned_piece.health = sp_data["health"]
                                target.summoned_piece.max_health = sp_data["max_health"]
                            else:
                                target.summoned_piece = None

                        # 마스터의 player_state → 슬레이브의 opponent
                        # 마스터의 opponent_state → 슬레이브의 player
                        _apply_state(self.opponent, recv2.get("player_state"))
                        _apply_state(self.player, recv2.get("opponent_state"))

                        # 소환 기물 사망 동기화
                        for dead in recv2.get("dead_summoned", []):
                            if tuple(dead) not in self.dead_summoned_pieces:
                                self.dead_summoned_pieces.append(tuple(dead))

                        winner_role = recv2.get("winner")
                        if winner_role:
                            self.is_game_over = True
                            self.winner = self.player if winner_role == "Player" else self.opponent
                    if not self.is_game_over:
                        pygame.time.wait(800)
                        self._start_new_turn()
                    return

        # ── 싱글/로컬 또는 마스터의 실제 계산 ───────────────────────────
        else:
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

        # 마스터면 턴 결과를 슬레이브에게 전송 (전체 상태 동기화)
        if self.net and self.net.connected and self.is_master:
            winner_role = self.winner.role if self.winner else None

            def _player_state(p):
                sp = None
                if p.summoned_piece:
                    sp = {
                        "piece_type": p.summoned_piece.piece_type,
                        "attack": p.summoned_piece.attack,
                        "defense": p.summoned_piece.defense,
                        "health": p.summoned_piece.health,
                        "max_health": p.summoned_piece.max_health,
                    }
                return {
                    "health": p.health,
                    "max_health": p.max_health,
                    "attack": p.attack,
                    "defense": p.defense,
                    "piece_type": p.piece_type,
                    "summoned_piece": sp,
                    "statuses": p.statuses,
                    "heal_stack_count": p.heal_stack_count,
                    "summon_boost_count": p.summon_boost_count,
                }

            self.net.send_card_action({
                "type2": "turn_result",
                "player_state": _player_state(self.player),
                "opponent_state": _player_state(self.opponent),
                "winner": winner_role,
                "dead_summoned": list(self.dead_summoned_pieces),
            })

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

        if p_is_defense:
            self.player.has_100_percent_defense = True
            self.game_log.append("플레이어: 방어 카드 → 킹 모든 공격 차단 (소환 기물은 그대로 맞음).")
        if o_is_defense:
            self.opponent.has_100_percent_defense = True
            self.game_log.append("상대방: 방어 카드 → 킹 모든 공격 차단 (소환 기물은 그대로 맞음).")

        if player_card and player_card.effect_type == "special" and player_card.effect == "checkmate_summon":
            self._apply_special(player_card, self.player, self.opponent, o_is_defense, opponent_card,
                                ally_pieces=self.player_ally_pieces)

        if opponent_card and opponent_card.effect_type == "special" and opponent_card.effect == "checkmate_summon":
            self._apply_special(opponent_card, self.opponent, self.player, p_is_defense, player_card,
                                ally_pieces=self.opponent_ally_pieces)

        if player_card and player_card.effect_type == "special" and player_card.effect != "checkmate_summon":
            self._apply_special(player_card, self.player, self.opponent, o_is_defense, opponent_card)

        if opponent_card and opponent_card.effect_type == "special" and opponent_card.effect != "checkmate_summon":
            self._apply_special(opponent_card, self.opponent, self.player, p_is_defense, player_card)

        if player_card and player_card.effect_type == "attack":
            self.game_log.append("플레이어 공격!")
            self._do_attack(attacker=self.player, defender=self.opponent)

        if opponent_card and opponent_card.effect_type == "attack":
            self.game_log.append("상대방 공격!")
            self._do_attack(attacker=self.opponent, defender=self.player)

        self._check_summoned_piece_death(self.player)
        self._check_summoned_piece_death(self.opponent)

        self.game_log.append(
            f"결과 → 플레이어: {self.player.health}/{self.player.max_health}HP  "
            f"상대방: {self.opponent.health}/{self.opponent.max_health}HP")

    # ─────────────────────────────────────────────────────────────────────────
    def _apply_special(self, card, user, opponent, opponent_played_defense, opponent_card,
                       ally_pieces=None):
        effect_result = SpecialEffectProcessor.use(
            card.effect,
            user_player=user,
            opponent_player=opponent,
            opponent_played_defense=opponent_played_defense,
            opponent_card_type=(opponent_card.effect_type if opponent_card else None),
            all_ally_pieces=ally_pieces if ally_pieces is not None else self.player_ally_pieces,
            current_turn_number=self.turn_number
        )

        self.game_log.extend(effect_result.get("log", []))

        has_summon = opponent.summoned_piece and opponent.summoned_piece.health > 0

        dmg = effect_result.get("damage", 0)
        if dmg > 0:
            if has_summon:
                sp = opponent.summoned_piece
                actual = sp.take_damage(dmg, ignore_defense=effect_result.get("ignore_defense", False))
                self.game_log.append(
                    f"  → 소환({sp.piece_type.upper()})에게 즉시 {actual} 데미지. "
                    f"소환 체력: {sp.health}/{sp.max_health}")
            else:
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
                    opponent.apply_status(**si)

        if effect_result.get("card_to_add_to_hand"):
            user.hand.append(effect_result["card_to_add_to_hand"])
        if effect_result.get("card_to_add_to_deck"):
            user.deck.append(effect_result["card_to_add_to_deck"])
            random.shuffle(user.deck)

    # ─────────────────────────────────────────────────────────────────────────
    def _do_attack(self, attacker, defender):
        if attacker.summoned_piece and attacker.summoned_piece.health > 0:
            sp = attacker.summoned_piece
            self._deal_damage(attacker=sp, defender=defender,
                              base_dmg=sp.attack,
                              label=f"{attacker.role}_소환({sp.piece_type.upper()})")
            self._deal_damage(attacker=attacker, defender=defender,
                              base_dmg=attacker.attack, label=attacker.role)
        else:
            self._deal_damage(attacker=attacker, defender=defender,
                              base_dmg=attacker.attack, label=attacker.role)

        defender.has_100_percent_defense = False

    def _deal_damage(self, attacker, defender, base_dmg, label):
        if defender.summoned_piece and defender.summoned_piece.health > 0:
            sp = defender.summoned_piece
            taken = sp.take_damage(base_dmg)
            self.game_log.append(
                f"  {label} → 소환({sp.piece_type.upper()}) "
                f"{taken} 데미지. 소환 체력: {sp.health}/{sp.max_health}")
        else:
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