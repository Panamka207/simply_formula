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
SPEED_INCREASE_INTERVAL = 150
ANIM_SPEED = 5
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

# ========== ЗВУКИ ==========
pygame.mixer.init()


def load_sound(filename):
    path = os.path.join(BASE_DIR, 'assets', 'sounds', filename)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None


snd_click = load_sound('click.wav')    # нажатие клавиши / переход
snd_crash = load_sound('crash.wav')    # столкновение
snd_coin = load_sound('coin.wav')     # заработана монета


def play(sound):
    if sound:
        sound.play()


# фоновая музыка
music_path = os.path.join(BASE_DIR, 'assets', 'sounds', 'music.mp3')
if os.path.exists(music_path):
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1)  # -1 = зацикленно

# ========== ШРИФТЫ ==========
fonts = {
    'big':   pygame.font.SysFont(None, 80),
    'mid':   pygame.font.SysFont(None, 50),
    'small': pygame.font.SysFont(None, 40),
}

# ========== ДАННЫЕ (мультиплеер) ==========


def load_all_players():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            save = json.load(f)
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


all_players = load_all_players()

current_nick = ''
profile = DEFAULT_PROFILE()

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
    gs.selected_car = profile.get('owned_cars', ['car1'])[-1]
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
            play(snd_crash)
            pygame.time.set_timer(spawn_event, 0)  # останавливаем спавн врагов
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
            play(snd_coin)
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
    # подсказка пауза — правый верхний угол
    hint = fonts['small'].render('P — пауза', True, (120, 120, 120))
    screen.blit(hint, (WIDTH - hint.get_width() - 10, 10))


def draw_bg_with_overlay():
    """Скроллящийся фон + затемнение — общий для всех экранов меню."""
    global bg_y
    bg_y = (bg_y + 3) % HEIGHT
    screen.blit(bg_image, (0, bg_y))
    screen.blit(bg_image, (0, bg_y - HEIGHT))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))


def draw_button(text, y, font_key='small', base_color=(255, 255, 255), hover_color=(255, 215, 0)):
    """Рисует кнопку по центру, подсвечивает при наведении мыши. Возвращает Rect."""
    mx, my = pygame.mouse.get_pos()
    surf = fonts[font_key].render(text, True, base_color)
    rect = surf.get_rect(center=(WIDTH // 2, y + surf.get_height() // 2))
    color = hover_color if rect.collidepoint(mx, my) else base_color
    surf = fonts[font_key].render(text, True, color)
    screen.blit(surf, rect)
    return rect


def draw_menu():
    draw_bg_with_overlay()
    blit_center(fonts['big'].render(
        "Simply Formula", True, (255, 255, 255)), 120)
    blit_center(fonts['small'].render(
        f'Игрок: {current_nick}', True, (100, 200, 255)), 230)
    blit_center(fonts['small'].render(
        f'Рекорд: {profile["highscore"]}', True, (255, 255, 255)), 270)
    blit_center(fonts['small'].render(
        f'Монеты: {profile["coins"]}', True, (255, 215, 0)), 310)
    draw_button("[ Играть ]",  370)
    draw_button("[ Магазин ]", 415, base_color=(
        255, 215, 0), hover_color=(255, 255, 255))
    draw_button("[ Выход ]",   460, base_color=(
        180, 180, 180), hover_color=(255, 80, 80))


def draw_nickname():
    draw_bg_with_overlay()
    blit_center(fonts['mid'].render(
        'Введите никнейм:', True, (255, 255, 255)), 40)
    blit_center(fonts['mid'].render(
        nickname_input + '|', True, (0, 255, 0)), 100)

    if all_players:
        blit_center(fonts['mid'].render(
            '[ Таблица лидеров ]', True, (255, 215, 0)), 165)
        sorted_players = sorted(all_players.keys(), key=lambda n: all_players[n].get(
            'highscore', 0), reverse=True)
        medals = ['1.', '2.', '3.', '4.', '5.']
        medal_colors = [(255, 215, 0), (192, 192, 192),
                        (205, 127, 50), (200, 200, 200), (200, 200, 200)]
        for i, name in enumerate(sorted_players[:5]):
            color = (
                100, 200, 255) if name == nickname_input else medal_colors[i]
            hs = all_players[name].get('highscore', 0)
            line = f"{medals[i]}  {name}  —  {hs}"
            t = fonts['mid'].render(line, True, color)
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 215 + i * 48))

    draw_button("ENTER — подтвердить", 510, base_color=(180, 180, 180))


def draw_game_over():
    draw_bg_with_overlay()
    blit_center(fonts['big'].render('Игра окончена', True, (255, 0, 0)), 80)
    blit_center(fonts['small'].render(
        f'Игрок: {current_nick}', True, (100, 200, 255)), 200)
    blit_center(fonts['small'].render(
        f'Счет: {gs.score}', True, (255, 255, 255)), 250)
    blit_center(fonts['small'].render(
        f'Рекорд: {profile["highscore"]}', True, (255, 255, 255)), 300)
    draw_button("[ Играть снова ]", 390)
    draw_button("[ В меню ]", 440, base_color=(
        200, 200, 200), hover_color=(255, 215, 0))


def draw_pause():
    draw_bg_with_overlay()
    blit_center(fonts['big'].render("ПАУЗА", True, (255, 255, 0)), 150)
    draw_button("[ Продолжить ]",  270)
    draw_button("[ В меню ]",      330, base_color=(
        200, 200, 200), hover_color=(255, 215, 0))
    draw_button("[ Выйти из игры ]", 390, base_color=(
        180, 180, 180), hover_color=(255, 80, 80))


def draw_shop():
    draw_bg_with_overlay()
    blit_center(fonts['big'].render("МАГАЗИН", True, (255, 215, 0)), 20)
    blit_center(fonts['small'].render(
        f'Монеты: {profile["coins"]}', True, (255, 215, 0)), 95)

    for i, car_name in enumerate(SHOP_CAR_LIST):
        stats = CAR_STATS[car_name]
        y = 145 + i * 85

        if car_name == gs.selected_car:
            color, status = (0, 255, 0), '[ ВЫБРАНА ]'
        elif car_name in profile['owned_cars']:
            color, status = (
                100, 200, 100), f'[ нажми {i+1} или кликни — выбрать ]'
        elif profile['coins'] >= stats['price']:
            color, status = (
                255, 255, 255), f'[ нажми {i+1} или кликни — купить ]'
        else:
            color, status = (100, 100, 100), '[ недостаточно монет ]'

        mx, my = pygame.mouse.get_pos()
        row_rect = pygame.Rect(10, y - 5, WIDTH - 20, 70)
        if row_rect.collidepoint(mx, my) and car_name != gs.selected_car:
            color = tuple(min(255, c + 60) for c in color)

        line1 = f"{i+1}. {stats['label']}   скорость: {stats['speed']}   цена: {stats['price']}"
        screen.blit(fonts['small'].render(line1, True, color), (20, y))
        screen.blit(fonts['small'].render(status, True, color), (40, y + 30))

    draw_button("[ Назад ]", 510, base_color=(
        180, 180, 180), hover_color=(255, 215, 0))


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
                    play(snd_click)
                    game_state = 'menu'
                elif event.key == pygame.K_BACKSPACE:
                    nickname_input = nickname_input[:-1]
                elif len(nickname_input) < 10:
                    nickname_input += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # клик по строке игрока в таблице — подставляет ник
                sorted_players = sorted(all_players.keys(), key=lambda n: all_players[n].get(
                    'highscore', 0), reverse=True)
                for i, name in enumerate(sorted_players[:5]):
                    row_rect = pygame.Rect(0, 210 + i * 48, WIDTH, 44)
                    if row_rect.collidepoint(event.pos):
                        nickname_input = name
                        play(snd_click)

        elif game_state == 'game':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and gs.current_lane > 0:
                    gs.current_lane -= 1
                    play(snd_click)
                elif event.key == pygame.K_RIGHT and gs.current_lane < 2:
                    gs.current_lane += 1
                    play(snd_click)
                elif event.key == pygame.K_p:
                    play(snd_click)
                    game_state = 'pause'
            if event.type == spawn_event:
                gs.enemies.append(spawn_enemy())

        elif game_state == 'game_over':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'game'
                elif event.key == pygame.K_m:
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'menu'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # "Играть снова" ~y=390, "В меню" ~y=440
                btn_play = fonts['small'].render(
                    "[ Играть снова ]", True, (255, 255, 255))
                btn_menu = fonts['small'].render(
                    "[ В меню ]", True, (255, 255, 255))
                r_play = btn_play.get_rect(
                    center=(WIDTH//2, 390 + btn_play.get_height()//2))
                r_menu = btn_menu.get_rect(
                    center=(WIDTH//2, 440 + btn_menu.get_height()//2))
                if r_play.collidepoint(mx, my):
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'game'
                elif r_menu.collidepoint(mx, my):
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'menu'

        elif game_state == 'menu':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'game'
                elif event.key == pygame.K_s:
                    play(snd_click)
                    game_state = 'shop'
                elif event.key == pygame.K_ESCAPE:
                    all_players[current_nick] = profile
                    save_all_players(all_players)
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                btn_play = fonts['small'].render(
                    "[ Играть ]", True, (255, 255, 255))
                btn_shop = fonts['small'].render(
                    "[ Магазин ]", True, (255, 215, 0))
                btn_quit = fonts['small'].render(
                    "[ Выход ]", True, (180, 180, 180))
                r_play = btn_play.get_rect(
                    center=(WIDTH//2, 370 + btn_play.get_height()//2))
                r_shop = btn_shop.get_rect(
                    center=(WIDTH//2, 415 + btn_shop.get_height()//2))
                r_quit = btn_quit.get_rect(
                    center=(WIDTH//2, 460 + btn_quit.get_height()//2))
                if r_play.collidepoint(mx, my):
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'game'
                elif r_shop.collidepoint(mx, my):
                    play(snd_click)
                    game_state = 'shop'
                elif r_quit.collidepoint(mx, my):
                    all_players[current_nick] = profile
                    save_all_players(all_players)
                    return False

        elif game_state == 'pause':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    play(snd_click)
                    game_state = 'game'
                elif event.key == pygame.K_m:
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'menu'
                elif event.key == pygame.K_ESCAPE:
                    all_players[current_nick] = profile
                    save_all_players(all_players)
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                btn_cont = fonts['small'].render(
                    "[ Продолжить ]", True, (255, 255, 255))
                btn_menu = fonts['small'].render(
                    "[ В меню ]", True, (255, 255, 255))
                btn_quit = fonts['small'].render(
                    "[ Выйти из игры ]", True, (255, 255, 255))
                r_cont = btn_cont.get_rect(
                    center=(WIDTH//2, 270 + btn_cont.get_height()//2))
                r_menu = btn_menu.get_rect(
                    center=(WIDTH//2, 330 + btn_menu.get_height()//2))
                r_quit = btn_quit.get_rect(
                    center=(WIDTH//2, 390 + btn_quit.get_height()//2))
                if r_cont.collidepoint(mx, my):
                    play(snd_click)
                    game_state = 'game'
                elif r_menu.collidepoint(mx, my):
                    play(snd_click)
                    gs.reset()
                    pygame.time.set_timer(spawn_event, SPAWN_INTERVAL_MS)
                    game_state = 'menu'
                elif r_quit.collidepoint(mx, my):
                    all_players[current_nick] = profile
                    save_all_players(all_players)
                    return False

        elif game_state == 'shop':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play(snd_click)
                    game_state = 'menu'
                for i, car_name in enumerate(SHOP_CAR_LIST):
                    if event.key == getattr(pygame, f'K_{i+1}'):
                        if car_name in profile['owned_cars']:
                            play(snd_click)
                            gs.selected_car = car_name
                            gs.enemy_speed = CAR_STATS[car_name]['speed']
                        elif profile['coins'] >= CAR_STATS[car_name]['price']:
                            play(snd_coin)
                            profile['coins'] -= CAR_STATS[car_name]['price']
                            profile['owned_cars'].append(car_name)
                            all_players[current_nick] = profile
                            save_all_players(all_players)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # клик по строке машины
                for i, car_name in enumerate(SHOP_CAR_LIST):
                    y = 145 + i * 85
                    row_rect = pygame.Rect(10, y - 5, WIDTH - 20, 70)
                    if row_rect.collidepoint(mx, my):
                        if car_name in profile['owned_cars']:
                            play(snd_click)
                            gs.selected_car = car_name
                            gs.enemy_speed = CAR_STATS[car_name]['speed']
                        elif profile['coins'] >= CAR_STATS[car_name]['price']:
                            play(snd_coin)
                            profile['coins'] -= CAR_STATS[car_name]['price']
                            profile['owned_cars'].append(car_name)
                            all_players[current_nick] = profile
                            save_all_players(all_players)
                # кнопка "Назад"
                btn = fonts['small'].render("[ Назад ]", True, (180, 180, 180))
                r = btn.get_rect(center=(WIDTH//2, 510 + btn.get_height()//2))
                if r.collidepoint(mx, my):
                    play(snd_click)
                    game_state = 'menu'

    return True


# ========== ГЛАВНЫЙ ЦИКЛ ==========
running = True

while running:
    clock.tick(FPS)

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
