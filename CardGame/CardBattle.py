import pygame
import random

from .Card import Card, SpecialEffectProcessor, Player


class CardBattle:
    def __init__(self, screen, player_piece_type, opponent_piece_type,
                 player_color="white", opponent_color="black",
                 player_ally_pieces=None, opponent_ally_pieces=None,
                 net=None, is_master=True):
        self.screen = screen
        self.net = net
        self.is_master = is_master

        self.player   = SpecialEffectProcessor.create_player(player_piece_type,   "Player",   player_color)
        self.opponent = SpecialEffectProcessor.create_player(opponent_piece_type,  "Opponent", opponent_color)

        from .CardGUI import CardBattleGUI
        self.gui = CardBattleGUI(screen, {"player": self.player, "opponent": self.opponent})

        self.player_selected_card_index = -1
        self.player_played_card  = None
        self.opponent_played_card = None

        self.turn_number     = 0
        self.is_game_over    = False
        self.winner          = None
        self.timer_start_time = 0
        self.turn_time_limit  = 10

        self.player_ally_pieces   = list(player_ally_pieces)   if player_ally_pieces   else []
        self.opponent_ally_pieces = list(opponent_ally_pieces) if opponent_ally_pieces else []

        self.dead_summoned_pieces = []
        self.game_log = []

        self._net_queue = []   # 수신된 card_action 메시지 큐

        self._start_new_turn()

    # ──────────────────────────────────────────────────────────────────────────
    # 네트워크 유틸
    # ──────────────────────────────────────────────────────────────────────────
    def _drain_net(self):
        """백그라운드 수신 버퍼에서 card_action 메시지를 큐로 이동."""
        if self.net and self.net.connected:
            for msg in self.net.poll():
                if msg.get("type") == "card_action":
                    self._net_queue.append(msg)

    def _wait_msg(self, timeout_ms=20000):
        """card_action 메시지가 올 때까지 블로킹 대기. 수신된 메시지 반환."""
        deadline = pygame.time.get_ticks() + timeout_ms
        while True:
            self._drain_net()
            if self._net_queue:
                return self._net_queue.pop(0)
            if pygame.time.get_ticks() > deadline:
                return None
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
            pygame.time.wait(20)

    def _send(self, data: dict):
        if self.net and self.net.connected:
            data["type"] = "card_action"
            self.net.send(data)

    # ──────────────────────────────────────────────────────────────────────────
    # 상태 직렬화 / 역직렬화
    # ──────────────────────────────────────────────────────────────────────────
    def _serialize_player(self, p):
        sp = None
        if p.summoned_piece:
            s = p.summoned_piece
            sp = {
                "piece_type":  s.piece_type,
                "attack":      s.attack,
                "defense":     s.defense,
                "health":      s.health,
                "max_health":  s.max_health,
                "statuses":    s.statuses,
            }
        return {
            "health":            p.health,
            "max_health":        p.max_health,
            "attack":            p.attack,
            "defense":           p.defense,
            "piece_type":        p.piece_type,
            "statuses":          p.statuses,
            "heal_stack_count":  p.heal_stack_count,
            "summon_boost_count":p.summon_boost_count,
            "has_100_percent_defense": p.has_100_percent_defense,
            "hand":    [c.to_dict() for c in p.hand],
            "summoned_piece": sp,
        }

    def _apply_state(self, target, state):
        """직렬화된 상태를 Player 객체에 적용."""
        if not state:
            return
        target.health            = state["health"]
        target.max_health        = state["max_health"]
        target.attack            = state["attack"]
        target.defense           = state["defense"]
        target.piece_type        = state["piece_type"]
        target.statuses          = state["statuses"]
        target.heal_stack_count  = state["heal_stack_count"]
        target.summon_boost_count= state["summon_boost_count"]
        target.has_100_percent_defense = state["has_100_percent_defense"]

        # 손패 동기화
        target.hand = [
            Card(c["name"], c["power"], c["effect_type"], c["description"], c.get("effect"))
            for c in state["hand"]
        ]

        # 소환 기물 동기화
        sp_data = state.get("summoned_piece")
        if sp_data:
            if not target.summoned_piece or target.summoned_piece.piece_type != sp_data["piece_type"]:
                target.summoned_piece = SpecialEffectProcessor.create_piece_player(sp_data["piece_type"])
            target.summoned_piece.piece_type = sp_data["piece_type"]
            target.summoned_piece.attack     = sp_data["attack"]
            target.summoned_piece.defense    = sp_data["defense"]
            target.summoned_piece.health     = sp_data["health"]
            target.summoned_piece.max_health = sp_data["max_health"]
            target.summoned_piece.statuses   = sp_data["statuses"]
        else:
            target.summoned_piece = None

    # ──────────────────────────────────────────────────────────────────────────
    # 턴 시작
    # ──────────────────────────────────────────────────────────────────────────
    def _start_new_turn(self):
        self.turn_number += 1

        if len(self.player.hand) < 3:
            self.player.draw_card()
        if len(self.opponent.hand) < 3:
            self.opponent.draw_card()

        self.player_selected_card_index = -1
        self.player_played_card  = None
        self.opponent_played_card = None

        # 슬레이브는 상태 업데이트를 마스터 결과에서 받으므로 직접 하지 않음
        if not (self.net and self.net.connected and not self.is_master):
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

    # ──────────────────────────────────────────────────────────────────────────
    def _check_summoned_piece_death(self, king_player):
        sp = king_player.summoned_piece
        if sp and sp.health <= 0:
            self.game_log.append(
                f"  {king_player.role}의 소환 기물({sp.piece_type.upper()}) 사망!")
            color = 'w' if king_player.role == "Player" else 'b'
            self.dead_summoned_pieces.append((color, sp.piece_type))
            king_player.summoned_piece = None

    # ──────────────────────────────────────────────────────────────────────────
    # 메인 루프
    # ──────────────────────────────────────────────────────────────────────────
    def run(self):
        clock = pygame.time.Clock()

        while True:
            time_left = max(0.0,
                self.turn_time_limit - (pygame.time.get_ticks() - self.timer_start_time) / 1000.0)

            # 백그라운드 수신 (run 루프 중 메시지 놓치지 않도록)
            self._drain_net()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return "quit"
                if not self.is_game_over:
                    if not self.player.is_status_active('stun'):
                        cr = self.gui.handle_click(ev, self.gui.player_hand_rect, self.player.hand)
                        if cr and cr["type"] == "card_clicked":
                            if self.player_selected_card_index == -1:
                                idx = cr["index"]
                                if 0 <= idx < len(self.player.hand):
                                    self.player_selected_card_index = idx
                                    self.game_log.append(
                                        f"플레이어가 '{self.player.hand[idx].name}' 선택.")

            card_chosen = (self.player_selected_card_index != -1
                           and self.player_played_card is None)
            time_up = (time_left <= 0 and self.player_played_card is None)

            if not self.is_game_over and (card_chosen or time_up):
                result = self._resolve_turn()
                if result == "quit":
                    return "quit"

            if not self.is_game_over:
                self.gui.draw("Player", time_left,
                              self.player_selected_card_index,
                              self.player_played_card,
                              self.opponent_played_card)
                self.gui.update_log(self.game_log)
                pygame.display.flip()
            else:
                self._display_game_over_screen()
                return self.winner

            clock.tick(60)

    # ──────────────────────────────────────────────────────────────────────────
    # 턴 처리
    # ──────────────────────────────────────────────────────────────────────────
    def _resolve_turn(self):
        # ── 1. 내 카드 결정 ───────────────────────────────────────────────
        player_stunned = self.player.is_status_active('stun')
        if not player_stunned and self.player_selected_card_index != -1:
            self.player_played_card = self.player.play_card(self.player_selected_card_index)
            self.game_log.append(f"플레이어: '{self.player_played_card.name}' 카드 사용.")
        else:
            self.player_played_card = None
            self.game_log.append(
                "플레이어: 스턴 → 카드 없음." if player_stunned else "플레이어: 시간 초과 → 카드 없음.")

        # ── 2. 멀티넷 ─────────────────────────────────────────────────────
        if self.net and self.net.connected:
            my_card_data = self.player_played_card.to_dict() if self.player_played_card else None

            if self.is_master:
                # ── 마스터: 상대 카드 수신 ───────────────────────────────
                recv = self._wait_msg()
                if recv is None:
                    return  # 타임아웃

                opp_card_data = recv.get("my_card")
                opp_stunned   = self.opponent.is_status_active('stun')

                if not opp_stunned and opp_card_data:
                    opp_idx = next(
                        (i for i, c in enumerate(self.opponent.hand)
                         if c.name == opp_card_data["name"]), None)
                    if opp_idx is not None:
                        self.opponent_played_card = self.opponent.play_card(opp_idx)
                    else:
                        # 손패에 없으면 카드 객체 직접 생성
                        self.opponent_played_card = Card(
                            opp_card_data["name"], opp_card_data["power"],
                            opp_card_data["effect_type"], opp_card_data["description"],
                            opp_card_data.get("effect"))
                else:
                    self.opponent_played_card = None

                self.game_log.append(
                    f"상대방: '{self.opponent_played_card.name if self.opponent_played_card else '없음'}' 카드 사용.")

                # ── 마스터: 전투 계산 ────────────────────────────────────
                self.gui.draw("Player", 0, self.player_selected_card_index,
                              self.player_played_card, self.opponent_played_card)
                pygame.display.flip()
                pygame.time.wait(1200)

                self._process_selected_cards(self.player_played_card, self.opponent_played_card)
                self._check_game_over()

                # ── 마스터: 전체 상태 전송 ───────────────────────────────
                winner_role = self.winner.role if self.winner else None
                self._send({
                    "subtype":        "turn_result",
                    "player_state":   self._serialize_player(self.player),
                    "opponent_state": self._serialize_player(self.opponent),
                    "player_card":    my_card_data,
                    "opponent_card":  self.opponent_played_card.to_dict() if self.opponent_played_card else None,
                    "dead_summoned":  [list(d) for d in self.dead_summoned_pieces],
                    "winner":         winner_role,
                    "turn_number":    self.turn_number,
                })

                if not self.is_game_over:
                    pygame.time.wait(800)
                    self._start_new_turn()

            else:
                # ── 슬레이브: 내 카드 전송 ──────────────────────────────
                self._send({"subtype": "card_choice", "my_card": my_card_data})

                # ── 슬레이브: 마스터 결과 수신 ──────────────────────────
                recv = self._wait_msg()
                if recv is None:
                    return  # 타임아웃

                # 카드 표시용 객체 복원
                pc_data = recv.get("player_card")
                oc_data = recv.get("opponent_card")

                def _card_from(d):
                    if not d:
                        return None
                    return Card(d["name"], d["power"], d["effect_type"],
                                d["description"], d.get("effect"))

                # 슬레이브 입장: master의 player → 내 opponent, master의 opponent → 내 player
                self.opponent_played_card = _card_from(pc_data)   # 상대(마스터)가 낸 카드
                self.player_played_card   = _card_from(oc_data)   # 내(슬레이브)가 낸 카드 (확인용)

                self.game_log.append(
                    f"상대방: '{self.opponent_played_card.name if self.opponent_played_card else '없음'}' 카드 사용.")

                # 화면 표시
                self.gui.draw("Player", 0, self.player_selected_card_index,
                              self.player_played_card, self.opponent_played_card)
                pygame.display.flip()
                pygame.time.wait(1200)

                # ── 슬레이브: 전체 상태 적용 ────────────────────────────
                # master의 player_state  → 슬레이브의 opponent
                # master의 opponent_state→ 슬레이브의 player
                self._apply_state(self.opponent, recv.get("player_state"))
                self._apply_state(self.player,   recv.get("opponent_state"))

                # 소환 기물 사망 동기화
                for d in recv.get("dead_summoned", []):
                    entry = tuple(d)
                    if entry not in self.dead_summoned_pieces:
                        self.dead_summoned_pieces.append(entry)

                winner_role = recv.get("winner")
                if winner_role:
                    self.is_game_over = True
                    self.winner = (self.player   if winner_role == "Opponent"   # master의 opponent=슬레이브의 player
                                   else self.opponent)

                self.game_log.append(
                    f"결과 → 플레이어: {self.player.health}/{self.player.max_health}HP  "
                    f"상대방: {self.opponent.health}/{self.opponent.max_health}HP")

                if not self.is_game_over:
                    pygame.time.wait(800)
                    self._start_new_turn()

        # ── 3. 싱글 / 로컬 ───────────────────────────────────────────────
        else:
            opp_stunned = self.opponent.is_status_active('stun')
            if not opp_stunned and self.opponent.hand:
                opp_idx = self._opponent_ai_choose()
                self.opponent_played_card = self.opponent.play_card(opp_idx)
                self.game_log.append(f"상대방: '{self.opponent_played_card.name}' 카드 사용.")
            else:
                self.opponent_played_card = None
                self.game_log.append("상대방: 스턴 or 손패 없음 → 카드 없음.")

            self.gui.draw("Player", 0, self.player_selected_card_index,
                          self.player_played_card, self.opponent_played_card)
            pygame.display.flip()
            pygame.time.wait(1200)

            self._process_selected_cards(self.player_played_card, self.opponent_played_card)
            self._check_game_over()

            if not self.is_game_over:
                pygame.time.wait(800)
                self._start_new_turn()

    # ──────────────────────────────────────────────────────────────────────────
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

    # ──────────────────────────────────────────────────────────────────────────
    def _process_selected_cards(self, player_card, opponent_card):
        self.game_log.append(f"\n--- 턴 {self.turn_number} 카드 처리 ---")
        self.game_log.append(f"  플레이어: {player_card.name if player_card else '없음'}")
        self.game_log.append(f"  상대방:   {opponent_card.name if opponent_card else '없음'}")

        p_is_defense = bool(player_card   and player_card.effect_type   == "defense")
        o_is_defense = bool(opponent_card and opponent_card.effect_type == "defense")

        if p_is_defense:
            self.player.has_100_percent_defense = True
            self.game_log.append("플레이어: 방어 카드 → 킹 차단.")
        if o_is_defense:
            self.opponent.has_100_percent_defense = True
            self.game_log.append("상대방: 방어 카드 → 킹 차단.")

        # 킹 체크메이트 먼저
        if player_card and player_card.effect == "checkmate_summon":
            self._apply_special(player_card, self.player, self.opponent,
                                o_is_defense, opponent_card, self.player_ally_pieces)
        if opponent_card and opponent_card.effect == "checkmate_summon":
            self._apply_special(opponent_card, self.opponent, self.player,
                                p_is_defense, player_card, self.opponent_ally_pieces)

        # 나머지 특수
        if player_card and player_card.effect_type == "special" and player_card.effect != "checkmate_summon":
            self._apply_special(player_card, self.player, self.opponent, o_is_defense, opponent_card)
        if opponent_card and opponent_card.effect_type == "special" and opponent_card.effect != "checkmate_summon":
            self._apply_special(opponent_card, self.opponent, self.player, p_is_defense, player_card)

        # 공격
        if player_card and player_card.effect_type == "attack":
            self.game_log.append("플레이어 공격!")
            self._do_attack(self.player, self.opponent)
        if opponent_card and opponent_card.effect_type == "attack":
            self.game_log.append("상대방 공격!")
            self._do_attack(self.opponent, self.player)

        self._check_summoned_piece_death(self.player)
        self._check_summoned_piece_death(self.opponent)

        self.game_log.append(
            f"결과 → 플레이어: {self.player.health}/{self.player.max_health}HP  "
            f"상대방: {self.opponent.health}/{self.opponent.max_health}HP")

    # ──────────────────────────────────────────────────────────────────────────
    def _apply_special(self, card, user, opponent, opponent_played_defense,
                       opponent_card, ally_pieces=None):
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
                    f"  → 소환({sp.piece_type.upper()})에게 {actual} 데미지. "
                    f"소환 체력: {sp.health}/{sp.max_health}")
            else:
                saved = opponent.has_100_percent_defense
                opponent.has_100_percent_defense = False
                actual = opponent.take_damage(dmg, ignore_defense=effect_result.get("ignore_defense", False))
                opponent.has_100_percent_defense = saved
                self.game_log.append(
                    f"  → {opponent.role}에게 {actual} 데미지. 체력: {opponent.health}/{opponent.max_health}")

        for si in effect_result.get("statuses", []):
            tgt = si.get("target", "opponent")
            s = {k: v for k, v in si.items() if k != "target"}
            if tgt == "user":
                user.apply_status(**s)
            else:
                if has_summon:
                    opponent.summoned_piece.apply_status(**s)
                else:
                    opponent.apply_status(**s)

        if effect_result.get("card_to_add_to_hand"):
            user.hand.append(effect_result["card_to_add_to_hand"])
        if effect_result.get("card_to_add_to_deck"):
            user.deck.append(effect_result["card_to_add_to_deck"])
            random.shuffle(user.deck)

    # ──────────────────────────────────────────────────────────────────────────
    def _do_attack(self, attacker, defender):
        if attacker.summoned_piece and attacker.summoned_piece.health > 0:
            sp = attacker.summoned_piece
            self._deal_damage(sp, defender, sp.attack,
                              f"{attacker.role}_소환({sp.piece_type.upper()})")
            self._deal_damage(attacker, defender, attacker.attack, attacker.role)
        else:
            self._deal_damage(attacker, defender, attacker.attack, attacker.role)
        defender.has_100_percent_defense = False

    def _deal_damage(self, attacker, defender, base_dmg, label):
        if defender.summoned_piece and defender.summoned_piece.health > 0:
            sp = defender.summoned_piece
            taken = sp.take_damage(base_dmg)
            self.game_log.append(
                f"  {label} → 소환({sp.piece_type.upper()}) {taken} 데미지. "
                f"소환 체력: {sp.health}/{sp.max_health}")
        else:
            if defender.has_100_percent_defense:
                self.game_log.append(f"  {label} → {defender.role} 방어 카드로 차단!")
            else:
                taken = defender.take_damage(base_dmg)
                self.game_log.append(
                    f"  {label} → {defender.role} {taken} 데미지. "
                    f"체력: {defender.health}/{defender.max_health}")

    # ──────────────────────────────────────────────────────────────────────────
    def _check_game_over(self):
        if self.player.health <= 0:
            self.is_game_over = True
            self.winner = self.opponent
            self.game_log.append(f"플레이어 기물 사망! {self.opponent.role} 승리!")
        elif self.opponent.health <= 0:
            self.is_game_over = True
            self.winner = self.player
            self.game_log.append(f"상대방 기물 사망! {self.player.role} 승리!")

    # ──────────────────────────────────────────────────────────────────────────
    def _display_game_over_screen(self):
        from .CardGUI import CardBattleGUI
        self.gui.draw("Player", 0, -1, self.player_played_card, self.opponent_played_card)
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        font = pygame.font.Font(None, 72)
        msg  = f"{self.winner.role} 승리!" if self.winner else "무승부!"
        text = font.render(msg, True, (255, 220, 50))
        self.screen.blit(text, text.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 2)))
        pygame.display.flip()
        pygame.time.wait(2500)