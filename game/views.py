from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

import random

from .models import Player, Enemy, Item, Skill, PlayerInventory, CombatLog, Chest, PlayerChest, ForgeState
from .combat import run_combat, pick_random_enemy, roll_loot, open_chest


# ─── Auth ────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('game:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        character_name = request.POST.get('character_name', '').strip()

        if not username or not password or not character_name:
            messages.error(request, 'All fields are required.')
        elif password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            user = User.objects.create_user(username=username, password=password)
            player = Player.objects.create(user=user, name=character_name)
            player.max_hp = player.compute_max_hp()
            player.current_hp = player.max_hp
            player.save()
            login(request, user)
            messages.success(request, f'Welcome, {character_name}! Your adventure begins.')
            return redirect('game:dashboard')
    return render(request, 'game/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('game:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('game:dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'game/login.html')


def logout_view(request):
    logout(request)
    return redirect('game:login')


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    player = get_object_or_404(Player, user=request.user)
    recent_combats = player.combat_logs.all()[:5]
    chests = player.chests.select_related('chest').all()
    return render(request, 'game/dashboard.html', {
        'player': player,
        'recent_combats': recent_combats,
        'chests': chests,
        'attack': player.compute_attack(),
        'defense': player.compute_defense(),
        'crit_chance': round(player.compute_crit_chance() * 100, 1),
    })


# ─── Combat ──────────────────────────────────────────────────────────────────

@login_required
def combat_select(request):
    player = get_object_or_404(Player, user=request.user)
    all_enemies = Enemy.objects.all().order_by('base_level')

    # Normal enemies (within level range)
    normal_enemies = [e for e in all_enemies if abs(e.base_level - player.level) <= 3]
    # Hard challenges (stronger enemies)
    hard_enemies = [e for e in all_enemies if e.base_level > player.level + 3]

    return render(request, 'game/combat_select.html', {
        'player': player,
        'normal_enemies': normal_enemies,
        'hard_enemies': hard_enemies,
        'all_enemies': all_enemies,
    })


@login_required
def combat_fight(request, enemy_id):
    player = get_object_or_404(Player, user=request.user)
    enemy = get_object_or_404(Enemy, pk=enemy_id)

    if not player.is_alive():
        player.current_hp = player.max_hp // 2
        player.save()
        messages.info(request, 'You rested and recovered some HP.')

    result = run_combat(player, enemy)

    # Apply results
    leveled_up = player.add_experience(result['xp_gained'])
    player.gold += result['gold_gained']

    dropped_item = None
    if result['outcome'] == 'win':
        player.enemies_defeated += 1
        # Roll for loot
        all_items = list(Item.objects.exclude(item_type='chest').all())
        # Filter items appropriate to player level
        suitable = [i for i in all_items if i.level_required <= player.level + 3]
        if not suitable:
            suitable = all_items
        dropped_item = roll_loot(enemy, suitable)
        if dropped_item:
            inv, created = PlayerInventory.objects.get_or_create(
                player=player, item=dropped_item,
                defaults={'quantity': 0}
            )
            inv.quantity += 1
            inv.save()
            result['log'] += f"\n🎁 Loot drop: {dropped_item.icon} {dropped_item.name} ({dropped_item.rarity})!"

        # Chance for chest drop (5% base, scales up with enemy type)
        chest_chance = 0.05
        if enemy.enemy_type == 'elite':
            chest_chance = 0.15
        elif enemy.enemy_type == 'boss':
            chest_chance = 0.40

        import random
        if random.random() < chest_chance:
            chests = Chest.objects.filter(level_required__lte=player.level)
            if chests.exists():
                chest_obj = random.choice(list(chests))
                pc, _ = PlayerChest.objects.get_or_create(
                    player=player, chest=chest_obj, defaults={'quantity': 0}
                )
                pc.quantity += 1
                pc.save()
                result['log'] += f"\n📦 Chest found: {chest_obj.icon} {chest_obj.name}!"

    player.save()

    CombatLog.objects.create(
        player=player,
        enemy_name=enemy.name,
        enemy_level=result['enemy_level'],
        player_level=player.level,
        outcome=result['outcome'],
        xp_gained=result['xp_gained'],
        gold_gained=result['gold_gained'],
        item_dropped=dropped_item,
        turns=result['turns'],
        log_text=result['log'],
    )

    return render(request, 'game/combat_result.html', {
        'player': player,
        'enemy': enemy,
        'result': result,
        'dropped_item': dropped_item,
        'leveled_up': leveled_up,
        'attack': player.compute_attack(),
        'defense': player.compute_defense(),
    })


@login_required
def combat_random(request):
    """Fight a random enemy based on player level."""
    player = get_object_or_404(Player, user=request.user)
    enemy = pick_random_enemy(Enemy.objects.all(), player.level)
    if not enemy:
        messages.error(request, 'No enemies found. Check back later!')
        return redirect('game:combat_select')
    return redirect('game:combat_fight', enemy_id=enemy.pk)


# ─── Skills ──────────────────────────────────────────────────────────────────

@login_required
def skill_tree(request):
    player = get_object_or_404(Player, user=request.user)
    all_skills = Skill.objects.all().order_by('tier', 'level_required')
    learned_ids = set(player.skills.values_list('id', flat=True))

    # Map skill_type to branch column (1=Strike, 2=Bellows, 3=Metallurgy)
    BRANCH_MAP = {'attack': 1, 'utility': 2, 'defense': 3}
    BRANCH_NAMES = {1: 'The Art of the Strike', 2: 'The Automated Bellows', 3: 'Metallurgical Secrets'}
    BRANCH_ICONS = {1: '⚔️', 2: '🔥', 3: '⚗️'}

    skill_data = []
    for skill in all_skills:
        can_learn = (
            skill.id not in learned_ids
            and player.level >= skill.level_required
            and player.stat_points >= skill.stat_points_cost
            and (skill.parent_skill_id is None or skill.parent_skill_id in learned_ids)
        )
        branch = BRANCH_MAP.get(skill.skill_type, 1)
        skill_data.append({
            'skill': skill,
            'learned': skill.id in learned_ids,
            'can_learn': can_learn,
            'branch': branch,
            'branch_name': BRANCH_NAMES.get(branch, ''),
            'branch_icon': BRANCH_ICONS.get(branch, ''),
        })

    return render(request, 'game/skill_tree.html', {
        'player': player,
        'skill_data': skill_data,
        'branch_names': BRANCH_NAMES,
        'branch_icons': BRANCH_ICONS,
    })


@login_required
@require_POST
def learn_skill(request, skill_id):
    player = get_object_or_404(Player, user=request.user)
    skill = get_object_or_404(Skill, pk=skill_id)

    if player.skills.filter(pk=skill_id).exists():
        messages.error(request, 'You already know this skill.')
    elif player.level < skill.level_required:
        messages.error(request, f'Requires level {skill.level_required}.')
    elif player.stat_points < skill.stat_points_cost:
        messages.error(request, f'Need {skill.stat_points_cost} stat points.')
    elif skill.parent_skill and not player.skills.filter(pk=skill.parent_skill_id).exists():
        messages.error(request, f'Requires "{skill.parent_skill.name}" first.')
    else:
        player.stat_points -= skill.stat_points_cost
        player.skills.add(skill)
        player.recalculate_stats()
        messages.success(request, f'Learned skill: {skill.name}!')

    return redirect('game:skill_tree')


# ─── Stats ───────────────────────────────────────────────────────────────────

@login_required
def stats_view(request):
    player = get_object_or_404(Player, user=request.user)
    stat_list = [
        ('Strength', '💪', 'Increases attack damage', player.strength),
        ('Dexterity', '🏃', 'Increases crit & dodge chance', player.dexterity),
        ('Intelligence', '🧠', 'Increases magical power', player.intelligence),
        ('Vitality', '❤️', 'Increases max HP', player.vitality),
    ]
    dodge_chance = round(min(30, player.dexterity * 1.0), 1)
    return render(request, 'game/stats.html', {
        'player': player,
        'attack': player.compute_attack(),
        'defense': player.compute_defense(),
        'crit_chance': round(player.compute_crit_chance() * 100, 1),
        'dodge_chance': dodge_chance,
        'stat_list': stat_list,
    })


@login_required
@require_POST
def allocate_stat(request):
    player = get_object_or_404(Player, user=request.user)
    stat = request.POST.get('stat')
    valid_stats = ['strength', 'dexterity', 'intelligence', 'vitality']

    if stat not in valid_stats:
        messages.error(request, 'Invalid stat.')
    elif player.stat_points < 1:
        messages.error(request, 'No stat points available.')
    else:
        current = getattr(player, stat)
        setattr(player, stat, current + 1)
        player.stat_points -= 1
        player.recalculate_stats()
        messages.success(request, f'{stat.capitalize()} increased!')

    return redirect('game:stats')


# ─── Inventory ───────────────────────────────────────────────────────────────

@login_required
def inventory(request):
    player = get_object_or_404(Player, user=request.user)
    inv_items = player.inventory.select_related('item').all()
    return render(request, 'game/inventory.html', {
        'player': player,
        'inventory': inv_items,
    })


@login_required
@require_POST
def equip_item(request, inv_id):
    player = get_object_or_404(Player, user=request.user)
    inv = get_object_or_404(PlayerInventory, pk=inv_id, player=player)
    item = inv.item

    if item.item_type in ('weapon', 'armor'):
        # Unequip other items of same type
        PlayerInventory.objects.filter(
            player=player, item__item_type=item.item_type, equipped=True
        ).update(equipped=False)
        inv.equipped = not inv.equipped
        inv.save()
        player.recalculate_stats()
        action = 'Equipped' if inv.equipped else 'Unequipped'
        messages.success(request, f'{action} {item.name}.')
    else:
        messages.error(request, 'This item cannot be equipped.')

    return redirect('game:inventory')


@login_required
@require_POST
def use_item(request, inv_id):
    player = get_object_or_404(Player, user=request.user)
    inv = get_object_or_404(PlayerInventory, pk=inv_id, player=player)
    item = inv.item

    if item.item_type == 'potion' and item.hp_restore > 0:
        healed = min(item.hp_restore, player.max_hp - player.current_hp)
        player.current_hp += healed
        player.save()
        inv.quantity -= 1
        if inv.quantity <= 0:
            inv.delete()
        else:
            inv.save()
        messages.success(request, f'Used {item.name}. Restored {healed} HP.')
    else:
        messages.error(request, 'This item cannot be used directly.')

    return redirect('game:inventory')


# ─── Chests ──────────────────────────────────────────────────────────────────

@login_required
def chests_view(request):
    player = get_object_or_404(Player, user=request.user)
    player_chests = player.chests.select_related('chest').filter(quantity__gt=0)
    return render(request, 'game/chests.html', {
        'player': player,
        'player_chests': player_chests,
    })


@login_required
@require_POST
def open_chest_view(request, player_chest_id):
    player = get_object_or_404(Player, user=request.user)
    pc = get_object_or_404(PlayerChest, pk=player_chest_id, player=player)

    if pc.quantity <= 0:
        messages.error(request, 'No chests of this type remaining.')
        return redirect('game:chests')

    all_items = Item.objects.all()
    rewards = open_chest(pc.chest, player, all_items)

    player.gold += rewards['gold']
    for item in rewards['items']:
        inv, _ = PlayerInventory.objects.get_or_create(
            player=player, item=item, defaults={'quantity': 0}
        )
        inv.quantity += 1
        inv.save()

    player.save()
    pc.quantity -= 1
    if pc.quantity <= 0:
        pc.delete()
    else:
        pc.save()

    return render(request, 'game/chest_open.html', {
        'player': player,
        'chest': pc.chest,
        'rewards': rewards,
    })


# ─── Combat history ──────────────────────────────────────────────────────────

@login_required
def combat_history(request):
    player = get_object_or_404(Player, user=request.user)
    logs = player.combat_logs.all()[:20]
    return render(request, 'game/combat_history.html', {
        'player': player,
        'logs': logs,
    })


# Seconds between each auto-strike when the Apprentice skill is active.
# Steam Powered Bellows halves this interval.
_AUTO_STRIKE_INTERVAL = 2.0
_AUTO_TEMPER_CHECK_MS = 3000  # ms, used in forge.html JS


def _compute_forge_bonuses(player_skills):
    """Return a dict of forge bonus values derived from learned skills."""
    skill_names = {s.name for s in player_skills}
    return {
        'heat_per_click': 10.0 + sum(s.attack_bonus for s in player_skills),
        'density_multiplier': 1.5 if 'Quenching Mastery' in skill_names else 1.0,
        'ember_chance': sum(s.crit_chance_bonus for s in player_skills),
        'has_apprentice': 'Apprentice' in skill_names,
        'has_steam': 'Steam Powered Bellows' in skill_names,
        'has_catalyst': 'Magical Catalyst' in skill_names,
        'has_soul_binding': 'Soul Binding' in skill_names,
    }


@login_required
def forge_view(request):
    player = get_object_or_404(Player, user=request.user)
    forge_state, created = ForgeState.objects.get_or_create(player=player)

    player_skills = list(player.skills.all())
    bonuses = _compute_forge_bonuses(player_skills)

    # ── Offline progress (Steam Powered Bellows) ──────────────────────────
    if not created and bonuses['has_steam']:
        elapsed = (timezone.now() - forge_state.last_active).total_seconds()
        offline_strikes = int(elapsed / _AUTO_STRIKE_INTERVAL)
        if offline_strikes > 0:
            offline_heat = offline_strikes * bonuses['heat_per_click']
            forge_state.heat = min(
                forge_state.heat + offline_heat, forge_state.get_heat_limit()
            )
            # Auto-temper if Magical Catalyst is active; cache limit per loop
            if bonuses['has_catalyst']:
                retain = 0.25 if bonuses['has_soul_binding'] else 0.0
                while forge_state.can_temper():
                    forge_state.temper_count += 1
                    if forge_state.material_grade < 3:
                        forge_state.material_grade += 1
                    forge_state.heat *= retain
                    forge_state.density *= retain
                    # Re-evaluate limit after grade change; stop if no longer full
                    if forge_state.heat < forge_state.get_heat_limit():
                        break
            forge_state.save()

    auto_interval = _AUTO_STRIKE_INTERVAL / 2 if bonuses['has_steam'] else _AUTO_STRIKE_INTERVAL

    return render(request, 'game/forge.html', {
        'player': player,
        'forge': forge_state,
        'has_auto_strike': bonuses['has_apprentice'],
        'has_steam': bonuses['has_steam'],
        'has_catalyst': bonuses['has_catalyst'],
        'auto_interval': auto_interval,
        'auto_temper_check_ms': _AUTO_TEMPER_CHECK_MS,
    })


@login_required
@require_POST
def forge_strike(request):
    player = get_object_or_404(Player, user=request.user)
    forge_state, _ = ForgeState.objects.get_or_create(player=player)

    player_skills = list(player.skills.all())
    bonuses = _compute_forge_bonuses(player_skills)

    heat_limit = forge_state.get_heat_limit()
    new_heat = min(forge_state.heat + bonuses['heat_per_click'], heat_limit)
    forge_state.heat = new_heat
    forge_state.density += 1.0 * bonuses['density_multiplier']
    forge_state.total_strikes += 1

    ember_gained = 0
    if bonuses['ember_chance'] > 0 and random.random() < bonuses['ember_chance']:
        forge_state.ember_dust += 1.0
        ember_gained = 1

    forge_state.save()

    return JsonResponse({
        'heat': round(forge_state.heat, 1),
        'heat_limit': round(heat_limit, 1),
        'heat_percent': forge_state.heat_percent(),
        'density': round(forge_state.density, 1),
        'ember_dust': round(forge_state.ember_dust, 1),
        'total_strikes': forge_state.total_strikes,
        'can_temper': forge_state.can_temper(),
        'material_grade': forge_state.get_material_name(),
        'blade_voice': forge_state.get_blade_voice(),
        'ember_gained': ember_gained,
    })


@login_required
@require_POST
def forge_temper(request):
    player = get_object_or_404(Player, user=request.user)
    forge_state, _ = ForgeState.objects.get_or_create(player=player)

    if not forge_state.can_temper():
        return JsonResponse({'error': 'Heat limit not reached yet!'}, status=400)

    player_skills = list(player.skills.all())
    bonuses = _compute_forge_bonuses(player_skills)
    retain = 0.25 if bonuses['has_soul_binding'] else 0.0

    forge_state.temper_count += 1
    if forge_state.material_grade < 3:
        forge_state.material_grade += 1
    forge_state.heat = forge_state.heat * retain
    forge_state.density = forge_state.density * retain
    forge_state.save()

    return JsonResponse({
        'heat': round(forge_state.heat, 1),
        'heat_limit': round(forge_state.get_heat_limit(), 1),
        'heat_percent': forge_state.heat_percent(),
        'density': round(forge_state.density, 1),
        'material_grade': forge_state.get_material_name(),
        'temper_count': forge_state.temper_count,
        'can_temper': forge_state.can_temper(),
        'blade_voice': forge_state.get_blade_voice(),
        'message': f'Blade tempered! New grade: {forge_state.get_material_name()}',
    })

