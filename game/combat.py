import random
import math


# ─── Mob variant definitions ──────────────────────────────────────────────────

# Shiny: tougher, more XP/gold, better loot.
# Blighted: hardest to kill, most gold, moderate XP boost.
COMBAT_VARIANTS = {
    'normal': {
        'label': 'Normal',
        'icon': '',
        'hp_mult': 1.0, 'atk_mult': 1.0, 'def_mult': 1.0,
        'xp_mult': 1.0, 'gold_mult': 1.0, 'loot_mult': 1.0,
    },
    'shiny': {
        'label': 'Shiny',
        'icon': '✨',
        'hp_mult': 1.5, 'atk_mult': 1.3, 'def_mult': 1.2,
        'xp_mult': 2.0, 'gold_mult': 1.5, 'loot_mult': 1.75,
    },
    'blighted': {
        'label': 'Blighted',
        'icon': '☠️',
        'hp_mult': 1.3, 'atk_mult': 1.6, 'def_mult': 1.1,
        'xp_mult': 1.5, 'gold_mult': 2.0, 'loot_mult': 1.4,
    },
}


def roll_variant():
    """Randomly decide whether a mob is Shiny, Blighted, or Normal."""
    roll = random.random()
    if roll < 0.05:
        return 'blighted'
    if roll < 0.15:
        return 'shiny'
    return 'normal'


def scale_enemy_stats(enemy, player_level):
    """Scale enemy stats based on player level for challenge."""
    scale = 1 + (player_level - enemy.base_level) * 0.15
    scale = max(0.5, min(scale, 3.0))  # cap scaling between 50% and 300%
    return {
        'hp': int(enemy.base_hp * scale),
        'attack': int(enemy.base_attack * scale),
        'defense': int(enemy.base_defense * scale),
        'xp': int(enemy.xp_reward * scale),
        'gold': int(enemy.gold_reward * scale),
        'level': max(enemy.base_level, player_level - 1),
    }


def run_combat(player, enemy, player_uses_skill=False, variant='normal'):
    """
    Simulate a full combat between player and enemy.
    Returns a dict with outcome, xp, gold, drops, log, and variant info.
    """
    v = COMBAT_VARIANTS.get(variant, COMBAT_VARIANTS['normal'])

    stats = scale_enemy_stats(enemy, player.level)
    # Apply variant multipliers to enemy stats
    enemy_hp = int(stats['hp'] * v['hp_mult'])
    enemy_max_hp = enemy_hp
    enemy_attack = int(stats['attack'] * v['atk_mult'])
    enemy_defense = int(stats['defense'] * v['def_mult'])
    enemy_level = stats['level']
    base_xp = int(stats['xp'] * v['xp_mult'])
    base_gold = int(stats['gold'] * v['gold_mult'])

    player_attack = player.compute_attack()
    player_defense = player.compute_defense()
    player_crit = player.compute_crit_chance()

    log_lines = []
    turns = 0
    max_turns = 30  # prevent infinite loops

    variant_prefix = f"{v['icon']} {v['label']} " if v['icon'] else ''
    log_lines.append(f"⚔️ Battle started: {player.name} (Lv {player.level}) vs {variant_prefix}{enemy.name} (Lv {enemy_level})")
    log_lines.append(f"Your HP: {player.current_hp}/{player.max_hp} | Enemy HP: {enemy_hp}")

    while player.current_hp > 0 and enemy_hp > 0 and turns < max_turns:
        turns += 1

        # Player attacks enemy
        raw_damage = max(1, player_attack - enemy_defense + random.randint(-2, 4))
        is_crit = random.random() < player_crit
        if is_crit:
            raw_damage = int(raw_damage * 1.75)
            log_lines.append(f"Turn {turns}: 💥 CRITICAL HIT! You deal {raw_damage} damage to {enemy.name}!")
        else:
            log_lines.append(f"Turn {turns}: You deal {raw_damage} damage to {enemy.name}.")
        enemy_hp -= raw_damage
        player.total_damage_dealt += raw_damage

        if enemy_hp <= 0:
            break

        # Enemy attacks player
        enemy_raw = max(1, enemy_attack - player_defense + random.randint(-2, 3))
        # Dodge chance from dexterity
        dodge_chance = min(0.3, player.dexterity * 0.01)
        if random.random() < dodge_chance:
            log_lines.append(f"Turn {turns}: 💨 You dodge {enemy.name}'s attack!")
        else:
            player.current_hp -= enemy_raw
            player.current_hp = max(0, player.current_hp)
            log_lines.append(f"Turn {turns}: {enemy.name} deals {enemy_raw} damage to you. HP: {player.current_hp}/{player.max_hp}")

    # Determine outcome
    if enemy_hp <= 0:
        xp_gained = base_xp
        gold_gained = base_gold + random.randint(0, base_gold // 2)
        log_lines.append(f"\n🏆 Victory! You defeated {variant_prefix}{enemy.name}!")
        log_lines.append(f"Gained: {xp_gained} XP | {gold_gained} Gold")
        outcome = 'win'
    elif player.current_hp <= 0:
        xp_gained = base_xp // 4  # partial XP on loss
        gold_gained = 0
        log_lines.append(f"\n💀 Defeat! {enemy.name} has defeated you.")
        log_lines.append(f"Consolation: {xp_gained} XP")
        outcome = 'loss'
    else:
        # timeout
        xp_gained = base_xp // 2
        gold_gained = base_gold // 3
        log_lines.append(f"\n⏰ The battle timed out! Both fighters withdraw.")
        outcome = 'flee'

    return {
        'outcome': outcome,
        'xp_gained': xp_gained,
        'gold_gained': gold_gained,
        'turns': turns,
        'log': '\n'.join(log_lines),
        'enemy_level': enemy_level,
        'variant': variant,
        'loot_mult': v['loot_mult'],
    }


def pick_random_enemy(enemies_qs, player_level):
    """
    Pick a random enemy from queryset, weighted towards enemies near player level.
    Higher level enemies have a small random chance of appearing.
    """
    if not enemies_qs.exists():
        return None

    enemies = list(enemies_qs)
    weights = []
    for e in enemies:
        diff = abs(e.base_level - player_level)
        # Enemies within 2 levels get max weight; harder enemies get reduced weight
        if diff <= 2:
            weight = 10
        elif diff <= 5:
            weight = 5
        elif e.base_level > player_level:
            # Harder enemies: small chance
            weight = max(1, 3 - (e.base_level - player_level))
        else:
            weight = max(1, 8 - diff)
        weights.append(weight)

    return random.choices(enemies, weights=weights, k=1)[0]


def roll_loot(enemy, possible_items):
    """Roll for loot drop from an enemy. Returns an Item or None."""
    if not possible_items:
        return None
    if random.random() > enemy.loot_chance:
        return None

    # Rarity weights: higher rarity = lower chance
    rarity_weights = {
        'common': 50,
        'uncommon': 25,
        'rare': 15,
        'epic': 7,
        'legendary': 3,
    }

    weighted_items = [(item, rarity_weights.get(item.rarity, 10)) for item in possible_items]
    items = [i[0] for i in weighted_items]
    weights = [i[1] for i in weighted_items]

    return random.choices(items, weights=weights, k=1)[0]


def open_chest(chest, player, all_items):
    """
    Open a chest and return rewards dict with gold and items list.
    """
    gold = random.randint(chest.gold_min, chest.gold_max)
    items_found = []

    chest_items = list(chest.possible_items.all())
    if not chest_items:
        chest_items = list(all_items)

    # Guaranteed items
    for _ in range(chest.guaranteed_items):
        if chest_items:
            item = random.choice(chest_items)
            items_found.append(item)

    # Bonus item roll
    if random.random() < chest.bonus_item_chance and chest_items:
        item = random.choice(chest_items)
        items_found.append(item)

    return {'gold': gold, 'items': items_found}
