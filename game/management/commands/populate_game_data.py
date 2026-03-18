from django.core.management.base import BaseCommand
from game.models import Enemy, Item, Skill, Chest


class Command(BaseCommand):
    help = 'Populate the database with initial game data'

    def handle(self, *args, **options):
        self.create_enemies()
        self.create_items()
        self.create_skills()
        self.create_chests()
        self.stdout.write(self.style.SUCCESS('Game data populated successfully!'))

    def create_enemies(self):
        enemies_data = [
            # Tier 1 (Lv 1-5)
            dict(name='Goblin Scout', description='A small, sneaky goblin.', enemy_type='normal',
                 base_level=1, icon='👺', base_hp=30, base_attack=6, base_defense=1,
                 xp_reward=15, gold_reward=5, loot_chance=0.25),
            dict(name='Rat King', description='A giant rat with a makeshift crown.', enemy_type='normal',
                 base_level=2, icon='🐀', base_hp=40, base_attack=7, base_defense=1,
                 xp_reward=20, gold_reward=7, loot_chance=0.20),
            dict(name='Forest Bandit', description='A desperate outlaw hiding in the woods.', enemy_type='normal',
                 base_level=3, icon='🗡️', base_hp=55, base_attack=9, base_defense=3,
                 xp_reward=28, gold_reward=15, loot_chance=0.35),
            dict(name='Slime', description='A gelatinous blob of goo.', enemy_type='normal',
                 base_level=1, icon='🟢', base_hp=25, base_attack=4, base_defense=0,
                 xp_reward=10, gold_reward=3, loot_chance=0.15),
            dict(name='Goblin Warrior', description='A goblin armed with a rusty sword.', enemy_type='elite',
                 base_level=4, icon='👹', base_hp=70, base_attack=12, base_defense=4,
                 xp_reward=45, gold_reward=20, loot_chance=0.50),
            # Tier 2 (Lv 5-10)
            dict(name='Orc Grunt', description='A brutish orc warrior.', enemy_type='normal',
                 base_level=5, icon='🪓', base_hp=90, base_attack=15, base_defense=5,
                 xp_reward=50, gold_reward=25, loot_chance=0.30),
            dict(name='Dark Mage', description='A mage who has turned to dark magic.', enemy_type='normal',
                 base_level=6, icon='🧙', base_hp=75, base_attack=18, base_defense=3,
                 xp_reward=60, gold_reward=30, loot_chance=0.40),
            dict(name='Cave Troll', description='A massive troll that lurks in caves.', enemy_type='elite',
                 base_level=7, icon='👊', base_hp=140, base_attack=20, base_defense=8,
                 xp_reward=90, gold_reward=45, loot_chance=0.55),
            dict(name='Undead Knight', description='A reanimated knight sworn to eternal battle.', enemy_type='elite',
                 base_level=8, icon='💀', base_hp=120, base_attack=22, base_defense=10,
                 xp_reward=100, gold_reward=50, loot_chance=0.55),
            # Tier 3 (Lv 10+)
            dict(name='Dragon Whelp', description='A young but dangerous dragon.', enemy_type='elite',
                 base_level=10, icon='🐉', base_hp=180, base_attack=28, base_defense=12,
                 xp_reward=140, gold_reward=70, loot_chance=0.60),
            dict(name='Lich', description='An undead sorcerer of immense power.', enemy_type='boss',
                 base_level=12, icon='☠️', base_hp=250, base_attack=35, base_defense=15,
                 xp_reward=200, gold_reward=100, loot_chance=0.80),
            dict(name='Ancient Dragon', description='A massive ancient dragon with centuries of battle experience.',
                 enemy_type='boss', base_level=15, icon='🔥', base_hp=400, base_attack=50, base_defense=20,
                 xp_reward=350, gold_reward=200, loot_chance=0.90),
        ]
        created = 0
        for data in enemies_data:
            _, was_created = Enemy.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created += 1
        self.stdout.write(f'  Created {created} enemies.')

    def create_items(self):
        items_data = [
            # Weapons
            dict(name='Rusty Sword', description='A worn old sword.', item_type='weapon', rarity='common',
                 icon='🗡️', attack_bonus=3, level_required=1, gold_value=10),
            dict(name='Iron Sword', description='A sturdy iron blade.', item_type='weapon', rarity='common',
                 icon='⚔️', attack_bonus=6, level_required=3, gold_value=25),
            dict(name='Steel Blade', description='A well-crafted steel sword.', item_type='weapon', rarity='uncommon',
                 icon='⚔️', attack_bonus=10, level_required=5, gold_value=60),
            dict(name='Shadow Dagger', description='A dagger that seems to absorb light.', item_type='weapon',
                 rarity='rare', icon='🗡️', attack_bonus=14, level_required=7, gold_value=120),
            dict(name='Enchanted Sword', description='A magically enhanced blade.', item_type='weapon',
                 rarity='epic', icon='✨', attack_bonus=20, level_required=10, gold_value=300),
            dict(name='Dragonslayer', description='A legendary blade forged to slay dragons.', item_type='weapon',
                 rarity='legendary', icon='🌟', attack_bonus=35, level_required=14, gold_value=1000),
            # Armor
            dict(name='Leather Tunic', description='Basic leather protection.', item_type='armor', rarity='common',
                 icon='🛡️', defense_bonus=3, hp_bonus=10, level_required=1, gold_value=15),
            dict(name='Chain Mail', description='Interlocked metal rings provide decent protection.', item_type='armor',
                 rarity='common', icon='🛡️', defense_bonus=6, hp_bonus=20, level_required=3, gold_value=40),
            dict(name='Iron Plate', description='Heavy iron armor.', item_type='armor', rarity='uncommon',
                 icon='⚔️', defense_bonus=10, hp_bonus=30, level_required=5, gold_value=90),
            dict(name='Shadow Mail', description='Armor woven from shadows.', item_type='armor', rarity='rare',
                 icon='🌑', defense_bonus=15, hp_bonus=50, level_required=8, gold_value=200),
            dict(name='Dragon Scale Armor', description='Armor crafted from dragon scales.', item_type='armor',
                 rarity='epic', icon='🐉', defense_bonus=22, hp_bonus=80, level_required=12, gold_value=500),
            # Potions
            dict(name='Small Health Potion', description='Restores 50 HP.', item_type='potion', rarity='common',
                 icon='🧪', hp_restore=50, level_required=1, gold_value=20),
            dict(name='Health Potion', description='Restores 120 HP.', item_type='potion', rarity='uncommon',
                 icon='💊', hp_restore=120, level_required=3, gold_value=50),
            dict(name='Large Health Potion', description='Restores 250 HP.', item_type='potion', rarity='rare',
                 icon='🍶', hp_restore=250, level_required=7, gold_value=100),
        ]
        created = 0
        for data in items_data:
            _, was_created = Item.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created += 1
        self.stdout.write(f'  Created {created} items.')

    def create_skills(self):
        # Tier 1 Skills
        s1, _ = Skill.objects.get_or_create(name='Power Strike', defaults=dict(
            description='Your attacks hit harder. +5 attack.',
            skill_type='attack', tier=1, level_required=1, stat_points_cost=1,
            attack_bonus=5, icon='💪'
        ))
        s2, _ = Skill.objects.get_or_create(name='Iron Skin', defaults=dict(
            description='Toughen your skin. +5 defense.',
            skill_type='defense', tier=1, level_required=1, stat_points_cost=1,
            defense_bonus=5, icon='🛡️'
        ))
        s3, _ = Skill.objects.get_or_create(name='Vital Force', defaults=dict(
            description='Expand your life force. +30 max HP.',
            skill_type='defense', tier=1, level_required=1, stat_points_cost=1,
            hp_bonus=30, icon='❤️'
        ))
        s4, _ = Skill.objects.get_or_create(name='Swift Strikes', defaults=dict(
            description='Learn to strike more precisely. +5% crit chance.',
            skill_type='attack', tier=1, level_required=2, stat_points_cost=1,
            crit_chance_bonus=0.05, icon='⚡'
        ))

        # Tier 2 Skills (require Tier 1)
        s5, _ = Skill.objects.get_or_create(name='Berserker Rage', defaults=dict(
            description='Channel rage into power. +12 attack.',
            skill_type='attack', tier=2, level_required=5, stat_points_cost=2,
            attack_bonus=12, parent_skill=s1, icon='😡'
        ))
        s6, _ = Skill.objects.get_or_create(name='Steel Fortress', defaults=dict(
            description='Near-impenetrable defense. +12 defense, +20 HP.',
            skill_type='defense', tier=2, level_required=5, stat_points_cost=2,
            defense_bonus=12, hp_bonus=20, parent_skill=s2, icon='🏰'
        ))
        s7, _ = Skill.objects.get_or_create(name='Battle Hardened', defaults=dict(
            description='Veteran combat experience. +50 max HP.',
            skill_type='defense', tier=2, level_required=5, stat_points_cost=2,
            hp_bonus=50, parent_skill=s3, icon='⚔️'
        ))
        s8, _ = Skill.objects.get_or_create(name='Assassin\'s Mark', defaults=dict(
            description='Master of critical strikes. +10% crit chance.',
            skill_type='attack', tier=2, level_required=6, stat_points_cost=2,
            crit_chance_bonus=0.10, parent_skill=s4, icon='🎯'
        ))

        # Tier 3 Skills (require Tier 2)
        s9, _ = Skill.objects.get_or_create(name='Warlord\'s Edge', defaults=dict(
            description='The power of a warlord. +25 attack.',
            skill_type='attack', tier=3, level_required=10, stat_points_cost=3,
            attack_bonus=25, parent_skill=s5, icon='👑'
        ))
        s10, _ = Skill.objects.get_or_create(name='Titan\'s Guard', defaults=dict(
            description='Legendary defensive mastery. +25 defense, +100 HP.',
            skill_type='defense', tier=3, level_required=10, stat_points_cost=3,
            defense_bonus=25, hp_bonus=100, parent_skill=s6, icon='🗿'
        ))
        s11, _ = Skill.objects.get_or_create(name='Champion\'s Vitality', defaults=dict(
            description='A champion\'s body and spirit. +150 max HP.',
            skill_type='defense', tier=3, level_required=10, stat_points_cost=3,
            hp_bonus=150, parent_skill=s7, icon='🏆'
        ))
        s12, _ = Skill.objects.get_or_create(name='Death\'s Touch', defaults=dict(
            description='Every strike can be lethal. +15% crit chance, +10 attack.',
            skill_type='attack', tier=3, level_required=11, stat_points_cost=3,
            crit_chance_bonus=0.15, attack_bonus=10, parent_skill=s8, icon='💀'
        ))
        self.stdout.write('  Created/verified skills.')

    def create_chests(self):
        chests_data = [
            dict(name='Wooden Chest', chest_type='wooden', icon='📦',
                 gold_min=10, gold_max=50, guaranteed_items=1, bonus_item_chance=0.2, level_required=1),
            dict(name='Silver Chest', chest_type='silver', icon='🎁',
                 gold_min=50, gold_max=150, guaranteed_items=1, bonus_item_chance=0.5, level_required=5),
            dict(name='Golden Chest', chest_type='golden', icon='💰',
                 gold_min=150, gold_max=500, guaranteed_items=2, bonus_item_chance=0.7, level_required=8),
            dict(name='Legendary Chest', chest_type='legendary', icon='✨',
                 gold_min=500, gold_max=1500, guaranteed_items=3, bonus_item_chance=1.0, level_required=12),
        ]
        created = 0
        for data in chests_data:
            chest, was_created = Chest.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created += 1
            # Add some items to each chest
            all_items = list(Item.objects.all())
            if all_items:
                chest.possible_items.set(all_items)
        self.stdout.write(f'  Created {created} chests.')
