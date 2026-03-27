import random

class Card:
    def __init__(self, name, power, effect_type, description, effect=None):
        self.name = name
        self.power = power
        self.effect_type = effect_type  # "attack", "defense", "special"
        self.description = description
        self.effect = effect

    def to_dict(self):
        return {
            "name": self.name,
            "power": self.power,
            "effect_type": self.effect_type,
            "description": self.description,
            "effect": self.effect
        }


class Player:
    def __init__(self, role, piece_type, attack, defense, health, initial_full_deck_cards):
        self.role = role
        self.piece_type = piece_type

        self.attack = attack
        self.defense = defense
        self.health = health
        self.max_health = health

        self.hand = []
        self.deck = []
        self.discard_pile = []
        self.statuses = []
        self.current_turn_number = 0

        self.selected_card_index = -1

        self.original_piece_type = piece_type
        self.original_stats = {"attack": attack, "defense": defense, "health": health, "max_health": health}
        self.transformed_type = None
        self.transform_duration = 0

        self.transformation_data = {
            "n": {"attack": 30, "defense": 60, "health": 100},
            "b": {"attack": 20, "defense": 40, "health": 100},
            "r": {"attack": 35, "defense": 70, "health": 100},
            "q": {"attack": 30, "defense": 20, "health": 100},
        }

        self.summoned_piece = None
        self.has_100_percent_defense = False
        self.defense_zero = False
        self.summon_boost_count = 0   # 킹 체크메이트 강화 횟수 (최대 2회)
        self.heal_stack_count = 0     # 퀸 치유 중첩 횟수 (최대 3회)

        self._initialize_player_cards(initial_full_deck_cards)

    def _initialize_player_cards(self, all_deck_cards_pool):
        temp_pool = list(all_deck_cards_pool)

        initial_hand_cards = []
        found_types = {'attack': False, 'defense': False, 'special': False}

        i = 0
        while i < len(temp_pool) and (
                not found_types['attack'] or not found_types['defense'] or not found_types['special']):
            card = temp_pool[i]
            if not found_types['attack'] and card.effect_type == "attack":
                initial_hand_cards.append(temp_pool.pop(i))
                found_types['attack'] = True
            elif not found_types['defense'] and card.effect_type == "defense":
                initial_hand_cards.append(temp_pool.pop(i))
                found_types['defense'] = True
            elif not found_types['special'] and card.effect_type == "special":
                initial_hand_cards.append(temp_pool.pop(i))
                found_types['special'] = True
            else:
                i += 1

        while len(initial_hand_cards) < 3 and temp_pool:
            initial_hand_cards.append(temp_pool.pop(0))

        self.hand = initial_hand_cards
        self.deck = temp_pool
        random.shuffle(self.deck)

    def draw_card(self):
        if self.deck:
            card = self.deck.pop(0)
            self.hand.append(card)
            return card
        elif self.discard_pile:
            self.deck = self.discard_pile[:]
            self.discard_pile = []
            random.shuffle(self.deck)
            if self.deck:
                card = self.deck.pop(0)
                self.hand.append(card)
                return card
        return None

    def discard_card(self, card):
        if card in self.hand:
            self.hand.remove(card)
            self.discard_pile.append(card)
        elif card not in self.discard_pile:
            self.discard_pile.append(card)

    def play_card(self, card_index):
        if 0 <= card_index < len(self.hand):
            card = self.hand.pop(card_index)
            self.discard_pile.append(card)
            return card
        return None

    def take_damage(self, damage, ignore_defense=False):
        """데미지를 받습니다. 방어력 카드(has_100_percent_defense)가 있으면 완전 차단."""
        if self.has_100_percent_defense:
            final_damage = 0
            print(f"{self.role}의 100% 방어 효과로 데미지 ({damage})가 막혔습니다.")
            self.has_100_percent_defense = False
        else:
            if ignore_defense or self.defense_zero:
                final_damage = max(0, damage)
            else:
                defense_multiplier = max(0.0, 1 - (self.defense / 100))
                final_damage = max(0, int(damage * defense_multiplier))

        self.health = max(0, self.health - final_damage)
        return final_damage

    def apply_status(self, type, duration, value=0, apply_defense=True, stat_mod=None, start_turn=1):
        new_status = {
            'type': type,
            'duration': duration,
            'value': value,
            'apply_defense': apply_defense,
            'stat_mod': stat_mod,
            'start_turn': start_turn
        }
        self.statuses.append(new_status)
        print(f"DEBUG: {self.role}에게 '{type}' 상태 효과 {duration}턴 적용.")

    def update_statuses(self, current_turn_number):
        self.current_turn_number = current_turn_number

        # 스탯 초기화 (변신 상태 유지)
        if self.transformed_type:
            transformed_data = self.transformation_data.get(self.transformed_type, {})
            self.attack = transformed_data.get("attack", self.original_stats["attack"])
            self.defense = transformed_data.get("defense", self.original_stats["defense"])
        else:
            self.attack = self.original_stats["attack"]
            self.defense = self.original_stats["defense"]

        self.defense_zero = False

        new_statuses = []

        for status in self.statuses:
            if current_turn_number < status['start_turn']:
                # 아직 시작 안 된 상태 효과는 그대로 유지
                new_statuses.append(status)
                continue

            # 상태 효과 처리
            stype = status['type']

            if status['stat_mod']:
                for stat, mod_value in status['stat_mod'].items():
                    if stat == 'attack':
                        self.attack = max(0, self.attack + mod_value)
                    elif stat == 'defense':
                        self.defense = max(0, self.defense + mod_value)

            if stype in ['poison', 'fire_dot', 'electric_dot']:
                # 방어력 무시 도트 피해
                dmg = max(0, status['value'])
                self.health = max(0, self.health - dmg)
                print(f"DEBUG: {self.role} {stype} 피해 {dmg}. 체력: {self.health}/{self.max_health}")

            elif stype == 'electric_stun_chance':
                # 30% 확률 스턴: stun 상태를 임시로 추가
                if random.random() < status['value']:
                    print(f"DEBUG: {self.role} 감전 스턴 발동!")
                    # 이번 턴 바로 적용될 스턴을 추가
                    new_statuses.append({
                        'type': 'stun',
                        'duration': 1,
                        'value': 0,
                        'apply_defense': False,
                        'stat_mod': None,
                        'start_turn': current_turn_number
                    })

            elif stype == 'defense_zero':
                self.defense_zero = True
                self.defense = 0

            elif stype == 'stun':
                print(f"DEBUG: {self.role} 스턴 상태.")

            elif stype == 'periodic_heal':
                # 2턴마다 회복 (홀수 활성 턴에 발동)
                active_turns = current_turn_number - status['start_turn'] + 1
                if active_turns % 2 == 1:
                    heal_val = status['value']
                    self.health = min(self.max_health, self.health + heal_val)
                    print(f"DEBUG: {self.role} 주기 치유 +{heal_val}. 체력: {self.health}/{self.max_health}")

            status['duration'] -= 1
            if status['duration'] > 0:
                new_statuses.append(status)
            else:
                print(f"DEBUG: {self.role}의 '{stype}' 상태 효과 만료.")
                # stat_debuff 만료 시 스탯 복구는 매 턴 초기화 방식이므로 자동 처리됨

        self.statuses = new_statuses
        self.health = max(0, self.health)

    def is_status_active(self, status_type):
        for status in self.statuses:
            if status['type'] == status_type and status['duration'] > 0 and \
                    self.current_turn_number >= status['start_turn']:
                return True
        return False

    def apply_transformation(self, new_piece_type, duration):
        self.transformed_type = new_piece_type
        self.transform_duration = duration
        self.piece_type = new_piece_type

        transformed_data = self.transformation_data.get(new_piece_type, {})
        self.attack = transformed_data.get("attack", self.attack)
        self.defense = transformed_data.get("defense", self.defense)
        print(f"DEBUG: {self.role} -> {new_piece_type.upper()} 변신! 공:{self.attack} 방:{self.defense}")

    def revert_transformation(self):
        if self.transformed_type:
            self.piece_type = self.original_piece_type
            self.attack = self.original_stats["attack"]
            self.defense = self.original_stats["defense"]
            self.transformed_type = None
            self.transform_duration = 0

    def update_stats_from_info(self, info_dict):
        if "attack" in info_dict:
            self.attack = info_dict["attack"]
        if "defense" in info_dict:
            self.defense = info_dict["defense"]
        if "health" in info_dict:
            self.health = min(info_dict["health"], self.max_health)
        if "max_health" in info_dict:
            self.max_health = info_dict["max_health"]
            self.health = min(self.health, self.max_health)
        if "piece_type" in info_dict:
            self.piece_type = info_dict["piece_type"]


class SpecialEffectProcessor:
    _card_data = {
        "p": [
            ("attack", 0, "attack", "적에게 기물 공격력만큼의 데미지를 줍니다.", None),
            ("defense", 0, "defense", "다음 공격을 100% 방어합니다.", None),
            ("ps", 0, "special", "형태 변화: 1턴 동안 킹을 제외한 다른 기물로 랜덤 변신. 변신 기물의 공격력·방어력 적용. 해당 기물의 특수 카드 1장이 덱에 추가됨.", "form_change")
        ],
        "r": [
            ("attack", 0, "attack", "적에게 기물 공격력만큼의 데미지를 줍니다.", None),
            ("defense", 0, "defense", "다음 공격을 100% 방어합니다.", None),
            ("rs", 0, "special", "대포: 방어 카드가 아닐 시 즉시+50, 스턴 1턴, 화염 도트+5(2턴). 방어 카드일 시 즉시+30.", "cannon")
        ],
        "n": [
            ("attack", 0, "attack", "적에게 기물 공격력만큼의 데미지를 줍니다.", None),
            ("defense", 0, "defense", "다음 공격을 100% 방어합니다.", None),
            ("ns", 0, "special", "돌진: 방어 카드가 아닐 시 즉시+40, 스턴 1턴, 방어력 0화(2턴). 방어 카드일 시 즉시+40.", "charge")
        ],
        "b": [
            ("attack", 0, "attack", "적에게 기물 공격력만큼의 데미지를 줍니다.", None),
            ("defense", 0, "defense", "다음 공격을 100% 방어합니다.", None),
            ("bs", 0, "special", "원소: 불/전기/독 랜덤. 불:즉시+40(비방어시 화염도트+20 1턴). 전기:즉시+20(비방어시 감전+5 스턴30% 3턴). 독:즉시+10(비방어시 독도트+10 능력-20 2턴).", "elemental_blast")
        ],
        "q": [
            ("attack", 0, "attack", "적에게 기물 공격력만큼의 데미지를 줍니다.", None),
            ("defense", 0, "defense", "다음 공격을 100% 방어합니다.", None),
            ("qs", 0, "special", "치유: 최대 체력의 5%를 2턴마다 지속 회복. 중첩 가능.", "queen_heal_over_time")
        ],
        "k": [
            ("attack", 0, "attack", "적에게 기물 공격력만큼의 데미지를 줍니다.", None),
            ("defense", 0, "defense", "다음 공격을 100% 방어합니다.", None),
            ("ks", 0, "special", "체크메이트: 아군 기물 소환(능력치 절반, 특수카드 불가). 소환 상태에서 재사용 시 능력치 2배 강화.", "checkmate_summon")
        ]
    }

    _default_deck_composition = {
        "attack": 4,
        "defense": 4,
        "special": 2,
    }

    _piece_initial_data = {
        "p": {"attack": 20, "defense": 20, "health": 100},
        "r": {"attack": 35, "defense": 70, "health": 100},
        "n": {"attack": 30, "defense": 60, "health": 100},
        "b": {"attack": 20, "defense": 40, "health": 100},
        "q": {"attack": 30, "defense": 20, "health": 100},
        "k": {"attack": 50, "defense": 50, "health": 100},
    }

    @staticmethod
    def get_special_card_for_piece_type(piece_type):
        for card_info in SpecialEffectProcessor._card_data.get(piece_type, []):
            if card_info[2] == "special":
                return Card(card_info[0], card_info[1], card_info[2], card_info[3], card_info[4])
        return None

    @staticmethod
    def create_piece_player(piece_type, role="Summoned Piece", color="gray"):
        data = SpecialEffectProcessor._piece_initial_data.get(piece_type)
        if not data:
            raise ValueError(f"알 수 없는 소환 기물 타입: {piece_type}")
        return Player(role, piece_type, data["attack"], data["defense"], data["health"], [])

    @staticmethod
    def create_player(piece_type, role, color):
        data = SpecialEffectProcessor._piece_initial_data.get(piece_type)
        if not data:
            raise ValueError(f"알 수 없는 기물 타입: {piece_type}")

        full_deck_cards = []
        template_cards_info = SpecialEffectProcessor._card_data[piece_type]

        for card_name, power, effect_type, description, effect in template_cards_info:
            count = SpecialEffectProcessor._default_deck_composition.get(effect_type, 0)
            for _ in range(count):
                full_deck_cards.append(Card(card_name, power, effect_type, description, effect))

        player = Player(role, piece_type, data["attack"], data["defense"], data["health"], full_deck_cards)
        return player

    @staticmethod
    def use(effect_name, user_player, opponent_player, opponent_played_defense,
            opponent_card_type, all_ally_pieces=None, current_turn_number=0, player_card_type=None):
        """
        특수 카드 효과를 처리합니다.
        - user_player: 특수 카드를 사용하는 플레이어
        - opponent_player: 상대방
        - 버프 target="user" → user_player에게 적용
        - 디버프 target="opponent" → opponent_player에게 적용
        """
        result = {
            "damage": 0,
            "heal": 0,
            "statuses": [],
            "log": [],
            "ignore_defense": False,
            "card_to_add_to_hand": None,
            "card_to_add_to_deck": None,
            "summoned_piece_info": None,
        }

        # ── 폰: 형태 변화 ──────────────────────────────────────────────
        if effect_name == "form_change":
            transformable_pieces = ['n', 'b', 'r', 'q']
            available = [t for t in transformable_pieces if t != user_player.transformed_type]
            target_type = random.choice(available) if available else random.choice(transformable_pieces)

            user_player.apply_transformation(target_type, 1)
            result["log"].append(
                f"{user_player.role}이/가 {target_type.upper()}(으)로 변신! (1턴 지속)")

            special_card = SpecialEffectProcessor.get_special_card_for_piece_type(target_type)
            if special_card:
                result["card_to_add_to_deck"] = special_card
                result["log"].append(f"→ 덱에 '{special_card.name}' 특수 카드 1장 추가.")

        # ── 룩: 대포 ───────────────────────────────────────────────────
        elif effect_name == "cannon":
            if opponent_played_defense:
                # 상대가 방어 카드 → 즉시 피해 +30 (방어력 적용)
                result["damage"] = 30
                result["ignore_defense"] = False
                result["log"].append(
                    f"{user_player.role}의 '대포': {opponent_player.role}가 방어 중 → 즉시 30 데미지.")
            else:
                # 방어 카드가 아닐 시 → 즉시 +50, 스턴 1턴, 화염 도트 +5 (2턴)
                result["damage"] = 50
                result["ignore_defense"] = False
                next_t = current_turn_number + 1
                result["statuses"].append({
                    "target": "opponent",
                    "type": "stun", "duration": 1, "value": 0,
                    "apply_defense": False, "stat_mod": None, "start_turn": next_t
                })
                result["statuses"].append({
                    "target": "opponent",
                    "type": "fire_dot", "duration": 2, "value": 5,
                    "apply_defense": False, "stat_mod": None, "start_turn": next_t
                })
                result["log"].append(
                    f"{user_player.role}의 '대포': 즉시 50 데미지 + 스턴 1턴 + 화염 도트 5(2턴)!")

        # ── 나이트: 돌진 ───────────────────────────────────────────────
        elif effect_name == "charge":
            # 방어 여부와 무관하게 즉시 +40
            result["damage"] = 40
            result["ignore_defense"] = False

            if opponent_played_defense:
                result["log"].append(
                    f"{user_player.role}의 '돌진': {opponent_player.role} 방어 중 → 즉시 40 데미지.")
            else:
                # 방어 카드가 아닐 시: 스턴 1턴 + 방어력 0화 2턴
                next_t = current_turn_number + 1
                result["statuses"].append({
                    "target": "opponent",
                    "type": "stun", "duration": 1, "value": 0,
                    "apply_defense": False, "stat_mod": None, "start_turn": next_t
                })
                result["statuses"].append({
                    "target": "opponent",
                    "type": "defense_zero", "duration": 2, "value": 0,
                    "apply_defense": False, "stat_mod": None, "start_turn": next_t
                })
                result["log"].append(
                    f"{user_player.role}의 '돌진': 즉시 40 데미지 + 스턴 1턴 + 방어력 0화 2턴!")

        # ── 비숍: 원소 ─────────────────────────────────────────────────
        elif effect_name == "elemental_blast":
            elements = ["fire", "electric", "poison"]
            chosen = random.choice(elements)
            names = {"fire": "불", "electric": "전기", "poison": "독"}
            result["log"].append(f"{user_player.role}의 '원소' 발동! [{names[chosen]}] 원소 선택.")
            next_t = current_turn_number + 1

            if chosen == "fire":
                # 방어/비방어 모두 즉시 +40
                result["damage"] = 40
                result["ignore_defense"] = False
                if not opponent_played_defense:
                    # 비방어: 화염 도트 +20, 1턴, 방어력 무시
                    result["statuses"].append({
                        "target": "opponent",
                        "type": "fire_dot", "duration": 1, "value": 20,
                        "apply_defense": False, "stat_mod": None, "start_turn": next_t
                    })
                    result["log"].append(f"→ 즉시 40 + 화염 도트 20(1턴, 방어력 무시).")
                else:
                    result["log"].append(f"→ 즉시 40 (방어 중).")

            elif chosen == "electric":
                # 방어/비방어 모두 즉시 +20
                result["damage"] = 20
                result["ignore_defense"] = False
                if not opponent_played_defense:
                    # 비방어: 3턴간 30% 스턴 + 감전 도트 +5 (방어력 무시)
                    result["statuses"].append({
                        "target": "opponent",
                        "type": "electric_stun_chance", "duration": 3, "value": 0.3,
                        "apply_defense": False, "stat_mod": None, "start_turn": next_t
                    })
                    result["statuses"].append({
                        "target": "opponent",
                        "type": "electric_dot", "duration": 3, "value": 5,
                        "apply_defense": False, "stat_mod": None, "start_turn": next_t
                    })
                    result["log"].append(f"→ 즉시 20 + 감전 도트 5(3턴) + 스턴 30%(3턴).")
                else:
                    result["log"].append(f"→ 즉시 20 (방어 중).")

            elif chosen == "poison":
                # 방어/비방어 모두 즉시 +10
                result["damage"] = 10
                result["ignore_defense"] = False
                if not opponent_played_defense:
                    # 비방어: 독 도트 +10(2턴) + 공격·방어력 -20(2턴)
                    result["statuses"].append({
                        "target": "opponent",
                        "type": "poison", "duration": 2, "value": 10,
                        "apply_defense": False, "stat_mod": None, "start_turn": next_t
                    })
                    result["statuses"].append({
                        "target": "opponent",
                        "type": "stat_debuff", "duration": 2, "value": 0,
                        "apply_defense": False,
                        "stat_mod": {"attack": -20, "defense": -20},
                        "start_turn": next_t
                    })
                    result["log"].append(f"→ 즉시 10 + 독 도트 10(2턴) + 공격·방어력 -20(2턴).")
                else:
                    result["log"].append(f"→ 즉시 10 (방어 중).")

        # ── 퀸: 치유 ───────────────────────────────────────────────────
        elif effect_name == "queen_heal_over_time":
            MAX_HEAL_STACK = 3
            if user_player.heal_stack_count >= MAX_HEAL_STACK:
                result["log"].append(
                    f"{user_player.role}의 '치유': 이미 최대 중첩({MAX_HEAL_STACK}회)입니다.")
            else:
                heal_amount = max(1, int(user_player.max_health * 0.05))
                user_player.heal_stack_count += 1
                result["statuses"].append({
                    "target": "user",
                    "type": "periodic_heal", "duration": 999, "value": heal_amount,
                    "apply_defense": False, "stat_mod": None, "start_turn": current_turn_number + 1
                })
                result["log"].append(
                    f"{user_player.role}의 '치유': 2턴마다 +{heal_amount} 회복 "
                    f"(중첩 {user_player.heal_stack_count}/{MAX_HEAL_STACK}).")

        # ── 킹: 체크메이트 ─────────────────────────────────────────────
        elif effect_name == "checkmate_summon":
            MAX_BOOST = 2
            if not user_player.summoned_piece:
                user_player.summon_boost_count = 0
                # all_ally_pieces = 체스판 위 아군 기물 목록 (킹 제외, 중복 포함)
                available = list(all_ally_pieces) if all_ally_pieces else []
                if available:
                    summon_type = random.choice(available)
                    sp = SpecialEffectProcessor.create_piece_player(
                        summon_type, role=f"{user_player.role}_소환({summon_type.upper()})")
                    sp.attack = max(1, sp.attack // 2)
                    sp.defense = max(0, sp.defense // 2)
                    sp.max_health = max(1, sp.max_health // 2)
                    sp.health = sp.max_health

                    user_player.summoned_piece = sp
                    # 소환된 기물 타입을 result에 담아 CardBattle이 ally_pieces에서 제거할 수 있게 함
                    result["summoned_piece_type"] = summon_type
                    result["summoned_piece_info"] = {
                        "piece_type": sp.piece_type,
                        "attack": sp.attack, "defense": sp.defense,
                        "health": sp.health, "max_health": sp.max_health
                    }
                    result["log"].append(
                        f"{user_player.role}의 '체크메이트': {summon_type.upper()} 소환! "
                        f"(공:{sp.attack} 방:{sp.defense} 체:{sp.health})")
                else:
                    result["log"].append(f"{user_player.role}: 소환 가능한 기물이 없습니다.")
            else:
                MAX_BOOST = 2
                if user_player.summon_boost_count >= MAX_BOOST:
                    result["log"].append(
                        f"{user_player.role}의 '체크메이트': 강화 최대 횟수({MAX_BOOST}회)에 도달했습니다.")
                else:
                    sp = user_player.summoned_piece
                    sp.attack *= 2
                    sp.defense = min(95, sp.defense * 2)
                    sp.max_health *= 2
                    sp.health = min(sp.health * 2, sp.max_health)
                    user_player.summon_boost_count += 1
                    result["summoned_piece_info"] = {
                        "piece_type": sp.piece_type,
                        "attack": sp.attack, "defense": sp.defense,
                        "health": sp.health, "max_health": sp.max_health
                    }
                    result["log"].append(
                        f"{user_player.role}의 '체크메이트': 소환 기물 2배 강화! "
                        f"({user_player.summon_boost_count}/{MAX_BOOST}회) "
                        f"(공:{sp.attack} 방:{sp.defense} 체:{sp.health}/{sp.max_health})")

        else:
            result["log"].append(f"알 수 없는 특수 효과: {effect_name}")

        return result