from django.contrib import admin
from .models import Player, Enemy, Item, Skill, PlayerInventory, CombatLog, Chest, PlayerChest


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'level', 'experience', 'gold', 'stat_points']
    search_fields = ['name', 'user__username']


@admin.register(Enemy)
class EnemyAdmin(admin.ModelAdmin):
    list_display = ['name', 'enemy_type', 'base_level', 'base_hp', 'base_attack', 'xp_reward', 'gold_reward']
    list_filter = ['enemy_type', 'base_level']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'item_type', 'rarity', 'attack_bonus', 'defense_bonus', 'hp_bonus', 'level_required']
    list_filter = ['item_type', 'rarity']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'skill_type', 'tier', 'level_required', 'stat_points_cost', 'parent_skill']
    list_filter = ['skill_type', 'tier']


@admin.register(PlayerInventory)
class PlayerInventoryAdmin(admin.ModelAdmin):
    list_display = ['player', 'item', 'quantity', 'equipped']


@admin.register(CombatLog)
class CombatLogAdmin(admin.ModelAdmin):
    list_display = ['player', 'enemy_name', 'enemy_level', 'outcome', 'xp_gained', 'gold_gained', 'created_at']
    list_filter = ['outcome']


@admin.register(Chest)
class ChestAdmin(admin.ModelAdmin):
    list_display = ['name', 'chest_type', 'gold_min', 'gold_max', 'guaranteed_items', 'level_required']


@admin.register(PlayerChest)
class PlayerChestAdmin(admin.ModelAdmin):
    list_display = ['player', 'chest', 'quantity']

