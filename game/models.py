from django.db import models
from django.contrib.auth.models import User
import math


class Skill(models.Model):
    SKILL_TYPES = [
        ('attack', 'Attack'),
        ('defense', 'Defense'),
        ('utility', 'Utility'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    skill_type = models.CharField(max_length=20, choices=SKILL_TYPES, default='attack')
    tier = models.IntegerField(default=1)  # 1=basic, 2=advanced, 3=elite
    level_required = models.IntegerField(default=1)
    stat_points_cost = models.IntegerField(default=1)
    parent_skill = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children'
    )
    # Bonus values granted when skill is learned
    attack_bonus = models.IntegerField(default=0)
    defense_bonus = models.IntegerField(default=0)
    hp_bonus = models.IntegerField(default=0)
    crit_chance_bonus = models.FloatField(default=0.0)
    icon = models.CharField(max_length=50, default='⚔️')

    def __str__(self):
        return f"{self.name} (Tier {self.tier})"


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player')
    name = models.CharField(max_length=100)

    # Core stats
    level = models.IntegerField(default=1)
    experience = models.IntegerField(default=0)
    stat_points = models.IntegerField(default=0)

    # Base stats
    strength = models.IntegerField(default=5)    # increases attack
    dexterity = models.IntegerField(default=5)   # increases crit chance and dodge
    intelligence = models.IntegerField(default=5)  # increases magic damage
    vitality = models.IntegerField(default=5)    # increases max HP

    # Derived stats (computed from base stats + skills)
    max_hp = models.IntegerField(default=100)
    current_hp = models.IntegerField(default=100)
    gold = models.IntegerField(default=50)

    # Skills learned
    skills = models.ManyToManyField('Skill', blank=True, related_name='players')

    # Tracking
    enemies_defeated = models.IntegerField(default=0)
    total_damage_dealt = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def xp_for_next_level(self):
        return int(100 * (self.level ** 1.5))

    def xp_progress_percent(self):
        needed = self.xp_for_next_level()
        if needed == 0:
            return 100
        return min(100, int((self.experience / needed) * 100))

    def compute_attack(self):
        skill_bonus = sum(s.attack_bonus for s in self.skills.all())
        equipped_bonus = sum(
            inv.item.attack_bonus for inv in self.inventory.filter(equipped=True)
        )
        forge_bonus = 0
        try:
            forge_bonus = self.forge_state.blade_attack_bonus
        except Exception:
            pass
        return 5 + self.strength * 2 + skill_bonus + equipped_bonus + forge_bonus

    def compute_defense(self):
        skill_bonus = sum(s.defense_bonus for s in self.skills.all())
        equipped_bonus = sum(
            inv.item.defense_bonus for inv in self.inventory.filter(equipped=True)
        )
        forge_bonus = 0
        try:
            forge_bonus = self.forge_state.blade_defense_bonus
        except Exception:
            pass
        return 2 + self.vitality + skill_bonus + equipped_bonus + forge_bonus

    def compute_crit_chance(self):
        skill_bonus = sum(s.crit_chance_bonus for s in self.skills.all())
        return min(0.75, 0.05 + self.dexterity * 0.01 + skill_bonus)

    def compute_max_hp(self):
        skill_bonus = sum(s.hp_bonus for s in self.skills.all())
        equipped_bonus = sum(
            inv.item.hp_bonus for inv in self.inventory.filter(equipped=True)
        )
        return 80 + self.vitality * 10 + self.level * 10 + skill_bonus + equipped_bonus

    def recalculate_stats(self):
        self.max_hp = self.compute_max_hp()
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp
        self.save()

    def add_experience(self, amount):
        self.experience += amount
        leveled_up = False
        while self.experience >= self.xp_for_next_level():
            self.experience -= self.xp_for_next_level()
            self.level += 1
            self.stat_points += 3
            self.max_hp = self.compute_max_hp()
            self.current_hp = self.max_hp  # Full heal on level up
            leveled_up = True
        self.save()
        return leveled_up

    def is_alive(self):
        return self.current_hp > 0

    def hp_percent(self):
        if self.max_hp == 0:
            return 0
        return max(0, int((self.current_hp / self.max_hp) * 100))

    def __str__(self):
        return f"{self.name} (Level {self.level})"


class Enemy(models.Model):
    ENEMY_TYPES = [
        ('normal', 'Normal'),
        ('elite', 'Elite'),
        ('boss', 'Boss'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    enemy_type = models.CharField(max_length=20, choices=ENEMY_TYPES, default='normal')
    base_level = models.IntegerField(default=1)
    icon = models.CharField(max_length=10, default='👹')

    # Base stats (scaled by level in combat)
    base_hp = models.IntegerField(default=50)
    base_attack = models.IntegerField(default=8)
    base_defense = models.IntegerField(default=2)

    # Rewards
    xp_reward = models.IntegerField(default=20)
    gold_reward = models.IntegerField(default=10)
    loot_chance = models.FloatField(default=0.3)  # chance to drop an item

    def __str__(self):
        return f"{self.name} (Lv {self.base_level})"


class Item(models.Model):
    ITEM_TYPES = [
        ('weapon', 'Weapon'),
        ('armor', 'Armor'),
        ('potion', 'Potion'),
        ('chest', 'Chest'),
        ('material', 'Material'),
    ]
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='weapon')
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    icon = models.CharField(max_length=10, default='🗡️')

    # Stat bonuses
    attack_bonus = models.IntegerField(default=0)
    defense_bonus = models.IntegerField(default=0)
    hp_bonus = models.IntegerField(default=0)
    hp_restore = models.IntegerField(default=0)  # for potions

    level_required = models.IntegerField(default=1)
    gold_value = models.IntegerField(default=5)

    def rarity_color(self):
        colors = {
            'common': 'text-secondary',
            'uncommon': 'text-success',
            'rare': 'text-primary',
            'epic': 'text-purple',
            'legendary': 'text-warning',
        }
        return colors.get(self.rarity, 'text-secondary')

    def __str__(self):
        return f"{self.name} ({self.rarity})"


class PlayerInventory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    equipped = models.BooleanField(default=False)
    obtained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'item')

    def __str__(self):
        return f"{self.player.name} - {self.item.name} x{self.quantity}"


class CombatLog(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='combat_logs')
    enemy_name = models.CharField(max_length=100)
    enemy_level = models.IntegerField(default=1)
    player_level = models.IntegerField(default=1)
    outcome = models.CharField(max_length=20, choices=[('win', 'Win'), ('loss', 'Loss'), ('flee', 'Flee')])
    xp_gained = models.IntegerField(default=0)
    gold_gained = models.IntegerField(default=0)
    item_dropped = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    turns = models.IntegerField(default=0)
    log_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.player.name} vs {self.enemy_name} - {self.outcome}"


class Chest(models.Model):
    CHEST_TYPES = [
        ('wooden', 'Wooden Chest'),
        ('silver', 'Silver Chest'),
        ('golden', 'Golden Chest'),
        ('legendary', 'Legendary Chest'),
    ]

    name = models.CharField(max_length=100)
    chest_type = models.CharField(max_length=20, choices=CHEST_TYPES, default='wooden')
    icon = models.CharField(max_length=10, default='📦')
    gold_min = models.IntegerField(default=10)
    gold_max = models.IntegerField(default=50)
    guaranteed_items = models.IntegerField(default=1)
    bonus_item_chance = models.FloatField(default=0.3)
    level_required = models.IntegerField(default=1)
    possible_items = models.ManyToManyField(Item, blank=True, related_name='chest_sources')

    def __str__(self):
        return self.name


class PlayerChest(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='chests')
    chest = models.ForeignKey(Chest, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    obtained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'chest')

    def __str__(self):
        return f"{self.player.name} - {self.chest.name} x{self.quantity}"


class EncounteredEnemy(models.Model):
    """Tracks which enemies a player has discovered/fought at least once."""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='encountered_enemies')
    enemy = models.ForeignKey(Enemy, on_delete=models.CASCADE)
    times_fought = models.IntegerField(default=0)
    times_won = models.IntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'enemy')

    def __str__(self):
        return f"{self.player.name} × {self.enemy.name}"


class ForgeState(models.Model):
    """Tracks the state of a player's Infinite Blade forge."""

    MATERIAL_GRADES = [
        (0, 'Bronze'),
        (1, 'Steel'),
        (2, 'Mythril'),
        (3, 'Star-Iron'),
    ]
    HEAT_LIMIT_BASE = 1000.0
    # Density thresholds for blade sentience messages
    _VOICE_THRESHOLD_MAX   = 1000
    _VOICE_THRESHOLD_HIGH  = 500
    _VOICE_THRESHOLD_MID   = 100
    _VOICE_THRESHOLD_LOW   = 10

    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='forge_state')
    heat = models.FloatField(default=0.0)
    density = models.FloatField(default=0.0)
    material_grade = models.IntegerField(default=0)
    temper_count = models.IntegerField(default=0)
    ember_dust = models.FloatField(default=0.0)
    total_strikes = models.IntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)
    # Cached combat bonuses granted to the player by the current blade
    blade_attack_bonus = models.IntegerField(default=0)
    blade_defense_bonus = models.IntegerField(default=0)

    def get_material_name(self):
        return dict(self.MATERIAL_GRADES).get(self.material_grade, 'Unknown')

    def get_heat_limit(self):
        """Max heat before tempering, scaled by material grade and Carbon Folding skill."""
        base = self.HEAT_LIMIT_BASE * (1 + self.material_grade * 0.5)
        if self.player.skills.filter(name='Carbon Folding').exists():
            base *= 1.5
        return base

    def heat_percent(self):
        limit = self.get_heat_limit()
        if limit == 0:
            return 0
        return min(100.0, round((self.heat / limit) * 100, 1))

    def can_temper(self):
        return self.heat >= self.get_heat_limit()

    def compute_blade_stats(self):
        """Return (attack_bonus, defense_bonus) from current material grade + density."""
        g = self.material_grade
        d = self.density
        # Each grade tier provides a base bonus and improves density scaling.
        attack = g * 8 + int(d / max(1, 10 - g * 2))
        defense = g * 3 + int(d / max(1, 30 - g * 5))
        return attack, defense

    def update_blade_bonuses(self):
        """Recompute and cache the blade combat bonuses. Call after heat/grade changes."""
        self.blade_attack_bonus, self.blade_defense_bonus = self.compute_blade_stats()

    def get_blade_voice(self):
        """Sentience lines that grow as the blade evolves."""
        if self.material_grade == 3 and self.density >= self._VOICE_THRESHOLD_MAX:
            return "I am complete. I am legend. Feed me more souls."
        if self.material_grade >= 2:
            return "My edge cuts through reality itself… do not stop."
        if self.material_grade >= 1:
            return "I feel… different. Stronger. Hungrier."
        if self.density >= self._VOICE_THRESHOLD_HIGH:
            return "Temper me, smith. I am ready to be reborn."
        if self.density >= self._VOICE_THRESHOLD_MID:
            return "Strike harder. I can feel your power."
        if self.density >= self._VOICE_THRESHOLD_LOW:
            return "I hunger for more heat…"
        return "…"

    def __str__(self):
        return f"{self.player.name}'s Forge [{self.get_material_name()}]"

