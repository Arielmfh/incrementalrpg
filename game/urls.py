from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'game'

urlpatterns = [
    # Root redirect to dashboard/login
    path('', RedirectView.as_view(url='/game/', permanent=False)),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Game
    path('game/', views.dashboard, name='dashboard'),
    path('game/combat/', views.combat_select, name='combat_select'),
    path('game/combat/random/', views.combat_random, name='combat_random'),
    path('game/combat/<int:enemy_id>/', views.combat_fight, name='combat_fight'),
    path('game/combat/history/', views.combat_history, name='combat_history'),
    path('game/skills/', views.skill_tree, name='skill_tree'),
    path('game/skills/<int:skill_id>/learn/', views.learn_skill, name='learn_skill'),
    path('game/stats/', views.stats_view, name='stats'),
    path('game/stats/allocate/', views.allocate_stat, name='allocate_stat'),
    path('game/inventory/', views.inventory, name='inventory'),
    path('game/inventory/<int:inv_id>/equip/', views.equip_item, name='equip_item'),
    path('game/inventory/<int:inv_id>/use/', views.use_item, name='use_item'),
    path('game/chests/', views.chests_view, name='chests'),
    path('game/chests/<int:player_chest_id>/open/', views.open_chest_view, name='open_chest'),
]
