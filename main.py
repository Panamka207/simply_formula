import pygame
import random
import sys
import json
import os

pygame.init()

# ========== КОНСТАНТЫ ==========
WIDTH, HEIGHT = 600, 600
FPS = 60
SAVE_FILE = 'save.json'

LANES = [150, 300, 450]
CAR_SIZE = (60, 100)
PLAYER_Y = HEIGHT - 150
ENEMY_SPAWN_Y = -100
ENEMY_DESPAWN_Y = HEIGHT
SPAWN_INTERVAL_MS = 1000
SPEED_INCREASE_INTERVAL = 150  # вдвое меньше — тот же реальный интервал при 30 FPS
ANIM_SPEED = 5                 # медленнее анимация машин
SAVE_EVERY_N_SCORE = 10

CAR_STATS = {
    'car1': {'price': 0,   'speed': 5,  'label': 'Базовая'},
    'car2': {'price': 50,  'speed': 7,  'label': 'Быстрая'},
    'car3': {'price': 150, 'speed': 9,  'label': 'Гоночная'},
    'car4': {'price': 300, 'speed': 12, 'label': 'Легенда'},
}

SHOP_CAR_LIST = ['car1', 'car2', 'car3', 'car4']


def DEFAULT_PROFILE(): return {'highscore': 0,
                               'coins': 0, 'owned_cars': ['car1']}


# ========== ЭКРАН ==========
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simply Formula")
clock = pygame.time.Clock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

bg_image = pygame.image.load(os.path.join(
    BASE_DIR, 'assets', 'images', 'background.png')).convert()
bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
bg_y = 0

# ========== ШРИФТЫ ==========
fonts = {
    'big':   pygame.font.SysFont(None, 80),
    'mid':   pygame.font.SysFont(None, 50),
    'small': pygame.font.SysFont(None, 40),
}

# ========== ДАННЫЕ (мультиплеер) ==========
# Формат save.json: {"players": {"ник": {highscore, coins, owned_cars}, ...}}


def load_all_players():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            save = json.load(f)
        # миграция старого формата (один игрок)
        if 'players' not in save:
            old_nick = save.get('nickname', 'Player1')
            players = {old_nick: {
                'highscore':  save.get('highscore', 0),
                'coins':      save.get('coins', 0),
                'owned_cars': save.get('owned_cars', ['car1']),
            }}
            save = {'players': players}
            with open(SAVE_FILE, 'w') as f:
                json.dump(save, f)
        return save['players']
    return {}


def save_all_players(players):
    with open(SAVE_FILE, 'w') as f:
        json.dump({'players': players}, f)


def get_or_create_profile(players, nickname):
    if nickname not in players:
        players[nickname] = DEFAULT_PROFILE()
    return players[nickname]


# глобальный реестр игроков
all_players = load_all_players()

# текущий профиль (заполняется после ввода ника)
current_nick = ''
profile = DEFAULT_PROFILE()   # активный профиль игрока

# ========== ЗАГРУЗКА МАШИН ==========


def load_cars(path, size):
    cars = {}
    for folder in sorted(os.listdir(path)):
        folder_path = os.path.join(path, folder)
        if os.path.isdir(folder_path):
            frames = []
            for file in sorted(os.listdir(folder_path)):
                if file.endswith(".png"):
                    img = pygame.image.load(os.path.join(
                        folder_path, file)).convert_alpha()
                    img = pygame.transform.scale(img, size)
                    frames.append(img)
            if frames:
                cars[folder] = frames
    return cars


cars = load_cars(os.path.join(BASE_DIR, 'assets', 'images', 'cars'), CAR_SIZE)

# ========== СОСТОЯНИЕ ИГРЫ ==========


class GameState:
    def __init__(self):
        self.selected_car = 'car1'
        self.reset()

    def reset(self):
        self.score = 0
        self.enemy_speed = CAR_STATS[self.selected_car]['speed']
        self.speed_timer = 0
        self.enemies = []
        self.current_lane = 1
        self.player_anim_frame = 0
        self.player_anim_timer = 0

    @property
    def player_frames(self):
        return cars[self.selected_car]

    @property
    def enemy_car_names(self):
        return [n for n in cars.keys() if n != self.selected_car]

    @property
    def player_rect(self):
        x = LANES[self.current_lane] - CAR_SIZE[0] // 2
        return pygame.Rect(x, PLAYER_Y, CAR_SIZE[0], CAR_SIZE[1])


gs = GameState()
game_state = 'nickname'
nickname_input = ''
pending_save = False

spawn_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)

# ========== ЗАГРУЗКА ПРОФИЛЯ ИГРОКА ==========


def apply_profile():
    """Применяет текущий профиль к игровому состоянию."""
    gs.selected_car = profile.get('owned_cars', ['car1'])[-1]
    # выбираем последнюю купленную как активную, но только если она есть в cars
    if gs.selected_car not in cars:
        gs.selected_car = 'car1'
    gs.enemy_speed = CAR_STATS[gs.selected_car]['speed']

# ========== СПАВН ВРАГА ==========


def spawn_enemy():
    lane = random.choice(LANES)
    rect = pygame.Rect(lane - CAR_SIZE[0] // 2,
                       ENEMY_SPAWN_Y, CAR_SIZE[0], CAR_SIZE[1])
    name = random.choice(
        gs.enemy_car_names) if gs.enemy_car_names else gs.selected_car
    return {'rect': rect, 'frames': cars[name], 'anim_frame': 0, 'anim_timer': 0, 'counted': False}

# ========== ЛОГИКА ==========


def update_game():
    global game_state, pending_save

    gs.speed_timer += 1
    if gs.speed_timer > SPEED_INCREASE_INTERVAL:
        gs.enemy_speed = CAR_STATS[gs.selected_car]['speed'] + gs.score * 0.1
        gs.speed_timer = 0

    for enemy in gs.enemies:
        enemy['rect'].y += gs.enemy_speed

    # сначала — столкновение
    for enemy in gs.enemies:
        if gs.player_rect.colliderect(enemy['rect']):
            game_state = 'game_over'
            if gs.score > profile['highscore']:
                profile['highscore'] = gs.score
            all_players[current_nick] = profile
            save_all_players(all_players)
            pending_save = False
            return

    # потом — очки
    for enemy in gs.enemies:
        if enemy['rect'].y > PLAYER_Y and not enemy['counted']:
            gs.score += 1
            enemy['counted'] = True
            profile['coins'] += 1
            pending_save = True

    if pending_save and gs.score % SAVE_EVERY_N_SCORE == 0:
        all_players[current_nick] = profile
        save_all_players(all_players)
        pending_save = False

    gs.enemies = [e for e in gs.enemies if e['rect'].y < ENEMY_DESPAWN_Y]

# ========== АНИМАЦИЯ ==========


def next_frame(entity, frames_list):
    entity['anim_timer'] += 1
    if entity['anim_timer'] >= ANIM_SPEED:
        entity['anim_timer'] = 0
        entity['anim_frame'] = (entity['anim_frame'] + 1) % len(frames_list)
    return frames_list[entity['anim_frame']]

# ========== ВСПОМОГАТЕЛЬНАЯ ОТРИСОВКА ==========


def blit_center(surface, y):
    screen.blit(surface, (WIDTH // 2 - surface.get_width() // 2, y))

# ========== ОТРИСОВКА ЭКРАНОВ ==========


def draw_game():
    global bg_y
    bg_y = (bg_y + gs.enemy_speed) % HEIGHT
    screen.blit(bg_image, (0, bg_y))
    screen.blit(bg_image, (0, bg_y - HEIGHT))

    gs.player_anim_timer += 1
    if gs.player_anim_timer >= ANIM_SPEED:
        gs.player_anim_timer = 0
        gs.player_anim_frame = (gs.player_anim_frame +
                                1) % len(gs.player_frames)
    screen.blit(gs.player_frames[gs.player_anim_frame], gs.player_rect)

    for enemy in gs.enemies:
        screen.blit(next_frame(enemy, enemy['frames']), enemy['rect'])

    screen.blit(fonts['small'].render(
        f'Игрок: {current_nick}', True, (200, 200, 200)), (20, 0))
    screen.blit(fonts['small'].render(
        f'Счет: {gs.score}', True, (255, 255, 255)), (20, 30))
    screen.blit(fonts['small'].render(
        f'Монеты: {profile["coins"]}', True, (255, 215, 0)), (20, 60))


def draw_menu():
    screen.fill((0, 0, 0))
    blit_center(fonts['big'].render(
        "Simply Formula", True, (255, 255, 255)), 120)
    blit_center(fonts['small'].render(
        f'Игрок: {current_nick}', True, (100, 200, 255)), 230)
    blit_center(fonts['small'].render(
        f'Рекорд: {profile["highscore"]}', True, (255, 255, 255)), 270)
    blit_center(fonts['small'].render(
        f'Монеты: {profile["coins"]}', True, (255, 215, 0)), 310)
    blit_center(fonts['small'].render(
        "ENTER - Играть", True, (255, 255, 255)), 370)
    blit_center(fonts['small'].render("S - Магазин", True, (255, 215, 0)), 410)
    blit_center(fonts['small'].render(
        "ESC - Выход", True, (255, 255, 255)), 450)


def draw_nickname():
    screen.fill((0, 0, 0))
    blit_center(fonts['mid'].render(
        'Введите никнейм:', True, (255, 255, 255)), 180)
    blit_center(fonts['mid'].render(
        nickname_input + '|', True, (0, 255, 0)), 240)

    # подсказка: существующие игроки
    if all_players:
        hint = fonts['small'].render(
            'Известные игроки:', True, (150, 150, 150))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 320))
        for i, name in enumerate(list(all_players.keys())[:5]):
            color = (100, 200, 255) if name == nickname_input else (
                120, 120, 120)
            t = fonts['small'].render(name, True, color)
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 355 + i * 35))

    blit_center(fonts['small'].render(
        'ENTER — подтвердить', True, (100, 100, 100)), 540)


def draw_game_over():
    screen.fill((0, 0, 0))
    blit_center(fonts['big'].render('Игра окончена', True, (255, 0, 0)), 80)
    blit_center(fonts['small'].render(
        f'Игрок: {current_nick}', True, (100, 200, 255)), 200)
    blit_center(fonts['small'].render(
        f'Счет: {gs.score}', True, (255, 255, 255)), 250)
    blit_center(fonts['small'].render(
        f'Рекорд: {profile["highscore"]}', True, (255, 255, 255)), 300)
    blit_center(fonts['small'].render(
        'R — играть снова', True, (255, 255, 255)), 400)
    blit_center(fonts['small'].render(
        'M — в меню', True, (200, 200, 200)), 440)


def draw_pause():
    screen.fill((0, 0, 0))
    blit_center(fonts['big'].render("ПАУЗА", True, (255, 255, 0)), 200)
    blit_center(fonts['small'].render(
        "P — продолжить", True, (255, 255, 255)), 300)


def draw_shop():
    screen.fill((0, 0, 0))
    blit_center(fonts['big'].render("МАГАЗИН", True, (255, 215, 0)), 30)
    screen.blit(fonts['small'].render(
        f'Монеты: {profile["coins"]}', True, (255, 215, 0)), (20, 20))

    for i, car_name in enumerate(SHOP_CAR_LIST):
        stats = CAR_STATS[car_name]
        y = 130 + i * 90

        if car_name == gs.selected_car:
            color, status = (0, 255, 0), '[ ВЫБРАНА ]'
        elif car_name in profile['owned_cars']:
            color, status = (100, 200, 100), f'[ куплена — нажми {i+1} ]'
        elif profile['coins'] >= stats['price']:
            color, status = (255, 255, 255), f'[ нажми {i+1} чтобы купить ]'
        else:
            color, status = (100, 100, 100), '[ недостаточно монет ]'

        screen.blit(
            fonts['small'].render(
                f"{i+1}. {stats['label']}  скорость:{stats['speed']}  цена:{stats['price']}  {status}",
                True, color),
            (20, y))

    blit_center(fonts['small'].render(
        'ESC — назад', True, (150, 150, 150)), 520)


DRAW_FUNCS = {
    'game':      draw_game,
    'menu':      draw_menu,
    'nickname':  draw_nickname,
    'game_over': draw_game_over,
    'pause':     draw_pause,
    'shop':      draw_shop,
}

# ========== ОБРАБОТКА СОБЫТИЙ ==========


def handle_events():
    global game_state, nickname_input, pending_save, current_nick, profile

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

        if game_state == 'nickname':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and nickname_input.strip():
                    current_nick = nickname_input.strip()
                    profile = get_or_create_profile(all_players, current_nick)
                    all_players[current_nick] = profile
                    save_all_players(all_players)
                    apply_profile()
                    game_state = 'menu'
                elif event.key == pygame.K_BACKSPACE:
                    nickname_input = nickname_input[:-1]
                elif len(nickname_input) < 10:
                    nickname_input += event.unicode

        elif game_state == 'game':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and gs.current_lane > 0:
                    gs.current_lane -= 1
                elif event.key == pygame.K_RIGHT and gs.current_lane < 2:
                    gs.current_lane += 1
                elif event.key == pygame.K_p:
                    game_state = 'pause'
            if event.type == spawn_event:
                gs.enemies.append(spawn_enemy())

        elif game_state == 'game_over':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # играть снова тем же игроком
                    game_state = 'game'
                elif event.key == pygame.K_m:
                    game_state = 'menu'

        elif game_state == 'menu':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_state = 'game'
                elif event.key == pygame.K_s:
                    game_state = 'shop'
                elif event.key == pygame.K_ESCAPE:
                    # сохраняем и выходим
                    all_players[current_nick] = profile
                    save_all_players(all_players)
                    return False

        elif game_state == 'pause':
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                game_state = 'game'

        elif game_state == 'shop':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = 'menu'
                for i, car_name in enumerate(SHOP_CAR_LIST):
                    if event.key == getattr(pygame, f'K_{i+1}'):
                        if car_name in profile['owned_cars']:
                            gs.selected_car = car_name
                            gs.enemy_speed = CAR_STATS[car_name]['speed']
                        elif profile['coins'] >= CAR_STATS[car_name]['price']:
                            profile['coins'] -= CAR_STATS[car_name]['price']
                            profile['owned_cars'].append(car_name)
                            all_players[current_nick] = profile
                            save_all_players(all_players)

    return True


# ========== ГЛАВНЫЙ ЦИКЛ ==========
prev_state = None
running = True

while running:
    clock.tick(FPS)

    if game_state == 'game' and prev_state != 'game':
        gs.reset()
    prev_state = game_state

    running = handle_events()
    if not running:
        break

    if game_state == 'game':
        update_game()

    if game_state in DRAW_FUNCS:
        DRAW_FUNCS[game_state]()

    if game_state == 'game_over' and pending_save:
        all_players[current_nick] = profile
        save_all_players(all_players)
        pending_save = False

    pygame.display.flip()

pygame.quit()
sys.exit()
