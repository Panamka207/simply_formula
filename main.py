import pygame
import random
import sys
import json
import os

pygame.init()

# Размеры окна
WIDTH = 600
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Минималистичная гонка")

clock = pygame.time.Clock()

# Линии
lanes = [150, 300, 450]
# lane_width = WIDTH // 3
# lanes = [
#     lane_width // 2,
#     lane_width + lane_width // 2,
#     lane_width * 2 + lane_width // 2
# ]

# Игрок
player_width = 60
player_height = 100
current_lane = 1
player_x = lanes[current_lane] - player_width // 2
player_y = HEIGHT - 150
player_rect = pygame.Rect(player_x, player_y, player_width, player_height)

# Враги
enemies = []
enemy_width = 60
enemy_height = 100
enemy_speed = 5

speed_incrase_timer = 0

# Таймер спавна
spawn_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_event, 1000)

running = True
game_over = False


def load_data():
    if os.path.exists('save.json'):
        with open('save.json', 'r') as f:
            data = json.load(f)
            return data.get('highscore', 0)
    return None


def save_data(data):
    data = {'highscore': data}
    with open('save.json', 'w') as f:
        json.dump(data, f)


score = 0
highscore = load_data()

# Загрузка профиля
data = load_data()
if data is not None:
    nickname = input("Введите ваш никнейм: ")
    data = {'nickname': nickname, 'highscore': 0}
    save_data(data)
else:
    nickname = data['nickname']
highscore = data['highscore']

# Основной игровой цикл
while running:
    clock.tick(60)
    screen.fill((0, 0, 0))

    # События
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT and current_lane > 0:
                current_lane -= 1
            if event.key == pygame.K_RIGHT and current_lane < 2:
                current_lane += 1
            if game_over and event.key == pygame.K_r:
                game_over = False
                score = 0
                enemy_speed = 5
                enemies.clear()

        if event.type == spawn_event:
            lane = random.choice(lanes)
            enemy_rect = pygame.Rect(0, -100, enemy_width, enemy_height)
            enemy_rect.centerx = lane

            enemy = {
                'rect': enemy_rect,
                'counted': False
            }

            enemies.append(enemy)

    if not game_over:
        speed_incrase_timer += 1

        if speed_incrase_timer > 300:
            enemy_speed = 5 + score * 0.1
            speed_incrase_timer = 0

        # Обновление позиции игрока
        player_rect.x = lanes[current_lane] - player_width // 2 + 1

        # Обновление врагов
        for enemy in enemies:
            enemy['rect'].y += enemy_speed

            # Подсчет очков
            if enemy['rect'].y > player_y and not enemy['counted']:
                score += 1
                enemy['counted'] = True

        # Проверка столкновения
        for enemy in enemies:
            if player_rect.colliderect(enemy['rect']):
                print("Игра окончена")
                game_over = True
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)

        # Удаление врагов за экраном
        enemies = [e for e in enemies if e['rect'].y < HEIGHT]

        # Отрисовка линий
        for lane in lanes:
            pygame.draw.line(screen, (50, 50, 50), (lane, 0),
                             (lane, HEIGHT), 2)

        # Отрисовка игрока
        pygame.draw.rect(screen, (255, 0, 0), player_rect)

        # Отрисовка врагов
        for enemy in enemies:
            pygame.draw.rect(screen, (255, 255, 255), enemy['rect'])

        font = pygame.font.SysFont(None, 40)
        score_text = font.render(f'Счет: {score}', True, (255, 255, 255))
        screen.blit(score_text, (20, 20))

        font_big = pygame.font.SysFont(None, 80)
        font_small = pygame.font.SysFont(None, 40)

    if game_over:
        game_over_text = font_big.render('Игра окончена', True, (255, 0, 0))
        restart_text = font_small.render(
            'Нажмите R чтобы начать заново', True, (255, 255, 255))
        score_text = font_small.render(
            f'Счет: {score}', True, (255, 255, 255))
        highscore_text = font_small.render(
            f'Рекорд: {highscore}', True, (255, 255, 255))

        screen.blit(game_over_text, (WIDTH // 2 -
                    game_over_text.get_width() // 2, 50))
        screen.blit(score_text, (WIDTH // 2 -
                    score_text.get_width() // 2, 300))
        screen.blit(highscore_text, (WIDTH // 2 -
                    highscore_text.get_width() // 2, 350))
        screen.blit(restart_text, (WIDTH // 2 -
                    restart_text.get_width() // 2, 550))

    pygame.display.flip()

pygame.quit()
sys.exit()
