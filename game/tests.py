from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Player, Enemy, Item, Skill, PlayerInventory, Chest, PlayerChest, ForgeState
from .combat import run_combat, pick_random_enemy, roll_loot, scale_enemy_stats, open_chest


class PlayerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.player = Player.objects.create(user=self.user, name='Hero', strength=5, dexterity=5,
                                            intelligence=5, vitality=5, level=1)
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()

    def test_xp_for_next_level(self):
        self.assertEqual(self.player.xp_for_next_level(), 100)

    def test_add_experience_no_level(self):
        self.player.add_experience(50)
        self.assertEqual(self.player.experience, 50)
        self.assertEqual(self.player.level, 1)

    def test_add_experience_level_up(self):
        leveled = self.player.add_experience(200)
        self.assertTrue(leveled)
        self.assertEqual(self.player.level, 2)
        self.assertEqual(self.player.stat_points, 3)

    def test_compute_attack(self):
        attack = self.player.compute_attack()
        self.assertEqual(attack, 5 + 5 * 2)  # base 5 + str*2

    def test_compute_defense(self):
        defense = self.player.compute_defense()
        self.assertEqual(defense, 2 + 5)  # base 2 + vit

    def test_compute_max_hp(self):
        hp = self.player.compute_max_hp()
        self.assertEqual(hp, 80 + 5 * 10 + 1 * 10)  # 80 + vit*10 + level*10

    def test_is_alive(self):
        self.assertTrue(self.player.is_alive())
        self.player.current_hp = 0
        self.assertFalse(self.player.is_alive())

    def test_hp_percent(self):
        self.assertEqual(self.player.hp_percent(), 100)
        self.player.current_hp = self.player.max_hp // 2
        self.assertEqual(self.player.hp_percent(), 50)

    def test_recalculate_stats(self):
        old_max = self.player.max_hp
        self.player.vitality += 5
        self.player.recalculate_stats()
        self.assertGreater(self.player.max_hp, old_max)


class CombatTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='fighter', password='pass')
        self.player = Player.objects.create(user=self.user, name='Fighter', strength=10, dexterity=5,
                                            intelligence=5, vitality=10, level=5)
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()

        self.enemy = Enemy.objects.create(
            name='Test Goblin', base_level=5, base_hp=50, base_attack=8, base_defense=2,
            xp_reward=30, gold_reward=15, loot_chance=0.0,
        )

    def test_scale_enemy_stats_same_level(self):
        stats = scale_enemy_stats(self.enemy, 5)
        self.assertEqual(stats['hp'], self.enemy.base_hp)

    def test_scale_enemy_stats_higher_player(self):
        stats = scale_enemy_stats(self.enemy, 8)
        self.assertGreater(stats['hp'], self.enemy.base_hp)

    def test_run_combat_returns_outcome(self):
        result = run_combat(self.player, self.enemy)
        self.assertIn(result['outcome'], ['win', 'loss', 'flee'])
        self.assertIn('log', result)
        self.assertGreaterEqual(result['xp_gained'], 0)
        self.assertGreaterEqual(result['gold_gained'], 0)

    def test_run_combat_win_gives_xp(self):
        # With very strong player, should win
        self.player.strength = 50
        self.player.save()
        result = run_combat(self.player, self.enemy)
        if result['outcome'] == 'win':
            self.assertGreater(result['xp_gained'], 0)

    def test_pick_random_enemy(self):
        Enemy.objects.create(name='Orc', base_level=3, base_hp=60, base_attack=10, base_defense=3,
                             xp_reward=25, gold_reward=12)
        enemy = pick_random_enemy(Enemy.objects.all(), 5)
        self.assertIsNotNone(enemy)

    def test_roll_loot_no_chance(self):
        self.enemy.loot_chance = 0.0
        item = roll_loot(self.enemy, [])
        self.assertIsNone(item)

    def test_roll_loot_with_items(self):
        item = Item.objects.create(name='Test Sword', item_type='weapon', rarity='common', attack_bonus=5)
        self.enemy.loot_chance = 1.0
        dropped = roll_loot(self.enemy, [item])
        self.assertEqual(dropped, item)


class SkillTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='mage', password='pass')
        self.player = Player.objects.create(user=self.user, name='Mage', strength=5, dexterity=5,
                                            intelligence=10, vitality=5, level=5, stat_points=5)
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()
        self.skill = Skill.objects.create(
            name='Power Strike', description='More power.', skill_type='attack',
            tier=1, level_required=1, stat_points_cost=1, attack_bonus=5
        )

    def test_learn_skill_deducts_stat_points(self):
        self.player.skills.add(self.skill)
        self.player.stat_points -= self.skill.stat_points_cost
        self.player.save()
        self.assertEqual(self.player.stat_points, 4)
        self.assertIn(self.skill, self.player.skills.all())

    def test_skill_attack_bonus(self):
        base_attack = self.player.compute_attack()
        self.player.skills.add(self.skill)
        new_attack = self.player.compute_attack()
        self.assertEqual(new_attack, base_attack + self.skill.attack_bonus)


class ChestTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='looter', password='pass')
        self.player = Player.objects.create(user=self.user, name='Looter', level=1, gold=0)
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()
        self.item = Item.objects.create(name='Chest Sword', item_type='weapon', rarity='common', attack_bonus=3)
        self.chest = Chest.objects.create(
            name='Test Chest', chest_type='wooden', gold_min=10, gold_max=10,
            guaranteed_items=1, bonus_item_chance=0.0, level_required=1,
        )
        self.chest.possible_items.add(self.item)

    def test_open_chest_gives_gold(self):
        rewards = open_chest(self.chest, self.player, Item.objects.all())
        self.assertEqual(rewards['gold'], 10)

    def test_open_chest_gives_item(self):
        rewards = open_chest(self.chest, self.player, Item.objects.all())
        self.assertEqual(len(rewards['items']), 1)
        self.assertEqual(rewards['items'][0], self.item)


class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='viewuser', password='pass123')
        self.player = Player.objects.create(user=self.user, name='ViewHero', level=1, gold=50,
                                            strength=5, dexterity=5, intelligence=5, vitality=5,
                                            stat_points=0)
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()
        self.enemy = Enemy.objects.create(
            name='View Goblin', base_level=1, base_hp=30, base_attack=5, base_defense=1,
            xp_reward=10, gold_reward=5, loot_chance=0.0,
        )

    def test_login_get(self):
        resp = self.client.get(reverse('game:login'))
        self.assertEqual(resp.status_code, 200)

    def test_login_post(self):
        resp = self.client.post(reverse('game:login'), {'username': 'viewuser', 'password': 'pass123'})
        self.assertRedirects(resp, reverse('game:dashboard'))

    def test_register_get(self):
        resp = self.client.get(reverse('game:register'))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('game:dashboard'))
        self.assertRedirects(resp, '/login/?next=/game/')

    def test_dashboard_authenticated(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_combat_select(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:combat_select'))
        self.assertEqual(resp.status_code, 200)

    def test_combat_fight(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:combat_fight', args=[self.enemy.pk]))
        self.assertEqual(resp.status_code, 200)
        # Check combat log was created
        self.assertEqual(self.player.combat_logs.count(), 1)

    def test_stats_view(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:stats'))
        self.assertEqual(resp.status_code, 200)

    def test_inventory_view(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:inventory'))
        self.assertEqual(resp.status_code, 200)

    def test_skill_tree_view(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:skill_tree'))
        self.assertEqual(resp.status_code, 200)

    def test_chests_view(self):
        self.client.login(username='viewuser', password='pass123')
        resp = self.client.get(reverse('game:chests'))
        self.assertEqual(resp.status_code, 200)

    def test_allocate_stat(self):
        self.client.login(username='viewuser', password='pass123')
        self.player.stat_points = 3
        self.player.save()
        old_str = self.player.strength
        resp = self.client.post(reverse('game:allocate_stat'), {'stat': 'strength'})
        self.assertRedirects(resp, reverse('game:stats'))
        self.player.refresh_from_db()
        self.assertEqual(self.player.strength, old_str + 1)
        self.assertEqual(self.player.stat_points, 2)

    def test_use_potion(self):
        self.client.login(username='viewuser', password='pass123')
        potion = Item.objects.create(name='Test Potion', item_type='potion', hp_restore=50)
        inv = PlayerInventory.objects.create(player=self.player, item=potion, quantity=1)
        self.player.current_hp = self.player.max_hp - 30
        self.player.save()
        resp = self.client.post(reverse('game:use_item', args=[inv.pk]))
        self.assertRedirects(resp, reverse('game:inventory'))
        self.player.refresh_from_db()
        self.assertGreater(self.player.current_hp, self.player.max_hp - 30)



class ForgeStateModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='smith', password='pass')
        self.player = Player.objects.create(user=self.user, name='Smith', level=1)
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()
        self.forge = ForgeState.objects.create(player=self.player)

    def test_initial_state(self):
        self.assertEqual(self.forge.heat, 0.0)
        self.assertEqual(self.forge.material_grade, 0)
        self.assertEqual(self.forge.get_material_name(), 'Bronze')

    def test_heat_limit_base(self):
        self.assertEqual(self.forge.get_heat_limit(), ForgeState.HEAT_LIMIT_BASE)

    def test_heat_limit_increases_with_grade(self):
        self.forge.material_grade = 1
        self.assertGreater(self.forge.get_heat_limit(), ForgeState.HEAT_LIMIT_BASE)

    def test_heat_limit_carbon_folding_bonus(self):
        carbon = Skill.objects.create(
            name='Carbon Folding', description='x', skill_type='defense',
            tier=1, level_required=1, stat_points_cost=1,
        )
        self.player.skills.add(carbon)
        base_limit = ForgeState.HEAT_LIMIT_BASE
        self.assertAlmostEqual(self.forge.get_heat_limit(), base_limit * 1.5, places=1)

    def test_heat_percent(self):
        self.forge.heat = self.forge.get_heat_limit() / 2
        self.assertAlmostEqual(self.forge.heat_percent(), 50.0, delta=1)

    def test_can_temper_false_when_heat_low(self):
        self.forge.heat = self.forge.get_heat_limit() - 1
        self.assertFalse(self.forge.can_temper())

    def test_can_temper_true_at_limit(self):
        self.forge.heat = self.forge.get_heat_limit()
        self.assertTrue(self.forge.can_temper())

    def test_blade_voice_low(self):
        # Fresh forge — minimal voice
        self.assertEqual(self.forge.get_blade_voice(), '…')

    def test_blade_voice_mid(self):
        self.forge.density = 150
        self.assertIn('harder', self.forge.get_blade_voice())

    def test_material_grade_names(self):
        for grade, name in ForgeState.MATERIAL_GRADES:
            self.forge.material_grade = grade
            self.assertEqual(self.forge.get_material_name(), name)


class ForgeViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='forger', password='pass123')
        self.player = Player.objects.create(
            user=self.user, name='Forger', level=5,
            strength=5, dexterity=5, intelligence=5, vitality=5,
            stat_points=10,
        )
        self.player.max_hp = self.player.compute_max_hp()
        self.player.current_hp = self.player.max_hp
        self.player.save()
        self.client.login(username='forger', password='pass123')

    def test_forge_view_get(self):
        resp = self.client.get(reverse('game:forge'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Infinite Blade', resp.content)

    def test_forge_strike_increases_heat(self):
        resp = self.client.post(
            reverse('game:forge_strike'),
            content_type='application/json',
            data='{}',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('heat', data)
        self.assertGreater(data['heat'], 0)

    def test_forge_strike_increments_total_strikes(self):
        self.client.post(reverse('game:forge_strike'), content_type='application/json', data='{}')
        forge = ForgeState.objects.get(player=self.player)
        self.assertEqual(forge.total_strikes, 1)

    def test_forge_temper_requires_full_heat(self):
        # Temper should fail when heat is 0
        resp = self.client.post(reverse('game:forge_temper'), content_type='application/json', data='{}')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_forge_temper_success(self):
        forge = ForgeState.objects.create(player=self.player, heat=1000.0)
        resp = self.client.post(reverse('game:forge_temper'), content_type='application/json', data='{}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('temper_count', data)
        self.assertEqual(data['temper_count'], 1)

    def test_forge_temper_advances_grade(self):
        ForgeState.objects.create(player=self.player, heat=1000.0, material_grade=0)
        self.client.post(reverse('game:forge_temper'), content_type='application/json', data='{}')
        forge = ForgeState.objects.get(player=self.player)
        self.assertEqual(forge.material_grade, 1)

    def test_forge_temper_caps_at_star_iron(self):
        ForgeState.objects.create(player=self.player, heat=99999.0, material_grade=3)
        resp = self.client.post(reverse('game:forge_temper'), content_type='application/json', data='{}')
        self.assertEqual(resp.status_code, 200)
        forge = ForgeState.objects.get(player=self.player)
        self.assertEqual(forge.material_grade, 3)

    def test_soul_binding_retains_heat(self):
        soul = Skill.objects.create(
            name='Soul Binding', description='x', skill_type='defense',
            tier=3, level_required=1, stat_points_cost=1,
        )
        self.player.skills.add(soul)
        initial_heat = 1000.0
        ForgeState.objects.create(player=self.player, heat=initial_heat, material_grade=0)
        self.client.post(reverse('game:forge_temper'), content_type='application/json', data='{}')
        forge = ForgeState.objects.get(player=self.player)
        self.assertAlmostEqual(forge.heat, initial_heat * 0.25, delta=1)

    def test_forge_view_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('game:forge'))
        self.assertRedirects(resp, '/login/?next=/game/forge/')
