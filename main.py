import pygame
import random
import sys
import json
import os

pygame.init()

# ========== НАСТРОЙКИ ЭКРАНА ==========
WIDTH = 600
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
# --- Загрузка фона ---
bg_image = pygame.image.load('./assets/images/background.png').convert()
bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
bg_y = 0
bg_speed = 5   # скорость движения фона
pygame.display.set_caption("Simply Formula")

clock = pygame.time.Clock()

# ========== ЗАГРУЗКА ДАННЫХ ==========
SAVE_FILE = 'save.json'


def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            return json.load(f)
    return None


def save_data(data):
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f)


data = load_data()
if data is None:
    data = {'nickname': '', 'highscore': 0}
    save_data(data)

nickname = data['nickname']
highscore = data['highscore']
nickname_input = ''

# ========== ЗАГРУЗКА СПРАЙТОВ МАШИН ==========


def load_cars(path, size):
    cars = {}
    for folder in os.listdir(path):
        folder_path = os.path.join(path, folder)
        if os.path.isdir(folder_path):
            frames = []
            for file in sorted(os.listdir(folder_path)):
                if file.endswith(".png"):
                    img = pygame.image.load(os.path.join(
                        folder_path, file)).convert_alpha()
                    img = pygame.transform.scale(img, size)
                    frames.append(img)
            cars[folder] = frames
    return cars


# путь к папке с машинами
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cars_path = os.path.join(BASE_DIR, "assets", "images", "cars")

CAR_SIZE = (60, 100)
cars = load_cars(cars_path, CAR_SIZE)

# выбираем скин для игрока
selected_car = "car1"  # можно менять
player_frames = cars[selected_car]
player_anim_index = 0

enemy_car_names = [name for name in cars.keys() if name != selected_car]

# ========== переменные ИГРЫ ==========
game_state = 'menu'

lanes = [150, 300, 450]
player_width = 60
player_height = 100
current_lane = 1
player_y = HEIGHT - 150
player_rect = pygame.Rect(0, player_y, player_width, player_height)

enemies = []
enemy_width = 60
enemy_height = 100
enemy_speed = 5
speed_increase_timer = 0

spawn_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_event, 1000)

score = 0

font = pygame.font.SysFont(None, 50)
font_big = pygame.font.SysFont(None, 80)
font_small = pygame.font.SysFont(None, 40)

running = True

# ========== ОСНОВНОЙ ЦИКЛ ==========
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ввод ника
        if game_state == 'nickname':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and nickname_input:
                    data['nickname'] = nickname_input
                    save_data(data)
                    nickname = nickname_input
                    game_state = 'game'
                elif event.key == pygame.K_BACKSPACE:
                    nickname_input = nickname_input[:-1]
                else:
                    if len(nickname_input) < 10:
                        nickname_input += event.unicode

        # управление в игре
        elif game_state == 'game':
            # --- движение фона ---
            bg_y += bg_speed
            if bg_y >= HEIGHT:
                bg_y = 0

            # --- рисуем два фона для бесконечного скролла ---
            screen.blit(bg_image, (0, bg_y))
            screen.blit(bg_image, (0, bg_y - HEIGHT))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and current_lane > 0:
                    current_lane -= 1
                if event.key == pygame.K_RIGHT and current_lane < 2:
                    current_lane += 1

                if event.key == pygame.K_p:
                    game_state = 'pause'

            if event.type == spawn_event:
                lane = random.choice(lanes)
                enemy_rect = pygame.Rect(0, -100, enemy_width, enemy_height)
                enemy_rect.centerx = lane

                # выбираем скин врага
                if enemy_car_names:
                    enemy_name = random.choice(enemy_car_names)
                else:
                    enemy_name = selected_car  # если список пуст
                enemy_frames = cars[enemy_name]

                enemies.append({
                    'rect': enemy_rect,
                    'frames': enemy_frames,
                    'anim': 0,
                    'counted': False
                })

        # рестарт после проигрыша
        elif game_state == 'game_over':
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game_state = 'game'
                score = 0
                enemy_speed = 5
                enemies.clear()
                current_lane = 1

        # меню
        elif game_state == 'menu':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_state = 'nickname'
                if event.key == pygame.K_ESCAPE:
                    running = False

        # пауза
        elif game_state == 'pause':
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                game_state = 'game'

    # ======= ЛОГИКА =======
    if game_state == 'game':
        speed_increase_timer += 1
        if speed_increase_timer > 300:
            enemy_speed = 5 + score * 0.1
            speed_increase_timer = 0

        player_rect.x = lanes[current_lane] - player_width // 2

        # движение врагов
        for enemy in enemies:
            enemy['rect'].y += enemy_speed

            if enemy['rect'].y > player_y and not enemy['counted']:
                score += 1
                enemy['counted'] = True

        # столкновение
        for enemy in enemies:
            if player_rect.colliderect(enemy['rect']):
                game_state = 'game_over'
                if score > highscore:
                    highscore = score
                    data['highscore'] = highscore
                    save_data(data)

        enemies = [e for e in enemies if e['rect'].y < HEIGHT]

    # ======= ОТРИСОВКА =======
    if game_state == 'game':
        # линии
        for lane in lanes:
            pygame.draw.line(screen, (50, 50, 50),
                             (lane, 0), (lane, HEIGHT), 2)

        # игрок (анимация)
        player_anim_index += 0.15
        if player_anim_index >= len(player_frames):
            player_anim_index = 0
        current_player_img = player_frames[int(player_anim_index)]
        screen.blit(current_player_img, player_rect)

        # враги (анимация)
        for enemy in enemies:
            enemy['anim'] += 0.15
            if enemy['anim'] >= len(enemy['frames']):
                enemy['anim'] = 0
            current_enemy_img = enemy['frames'][int(enemy['anim'])]
            screen.blit(current_enemy_img, enemy['rect'])

        # счёт
        score_text = font_small.render(f'Счет: {score}', True, (255, 255, 255))
        screen.blit(score_text, (20, 20))

    # ======= ЭКРАНЫ =======
    elif game_state == 'nickname':
        text = font.render('Введите никнейм:', True, (255, 255, 255))
        screen.blit(text, (150, 200))
        name_surface = font.render(nickname_input, True, (0, 255, 0))
        screen.blit(name_surface, (150, 260))

    elif game_state == 'game_over':
        game_over_text = font_big.render('Игра окончена', True, (255, 0, 0))
        restart_text = font_small.render(
            'Нажмите R чтобы начать заново', True, (255, 255, 255))
        score_text = font_small.render(f'Счет: {score}', True, (255, 255, 255))
        highscore_text = font_small.render(
            f'Рекорд: {highscore}', True, (255, 255, 255))

        screen.blit(game_over_text, (WIDTH//2 -
                    game_over_text.get_width()//2, 80))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 250))
        screen.blit(highscore_text, (WIDTH//2 -
                    highscore_text.get_width()//2, 300))
        screen.blit(restart_text, (WIDTH//2 -
                    restart_text.get_width()//2, 500))

    elif game_state == 'menu':
        title = font_big.render("Simply Formula", True, (255, 255, 255))
        play_text = font_small.render("ENTER - Играть", True, (255, 255, 255))
        quit_text = font_small.render("ESC - Выход", True, (255, 255, 255))

        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        screen.blit(play_text, (WIDTH//2 - play_text.get_width()//2, 300))
        screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, 350))

    elif game_state == 'pause':
        pause_text = font_big.render("ПАУЗА", True, (255, 255, 0))
        continue_text = font_small.render(
            "Нажмите P чтобы продолжить", True, (255, 255, 255))
        screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, 200))
        screen.blit(continue_text, (WIDTH//2 -
                    continue_text.get_width()//2, 300))

    pygame.display.flip()

pygame.quit()
sys.exit()
