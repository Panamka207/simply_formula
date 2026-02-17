import pygame
import random
import sys

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

# Таймер спавна
spawn_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_event, 1000)

running = True

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

        if event.type == spawn_event:
            lane = random.choice(lanes)
            enemy_rect = pygame.Rect(
                lane - enemy_width // 2 + 1, -100, enemy_width, enemy_height)
            enemies.append(enemy_rect)

    # Обновление позиции игрока
    player_rect.x = lanes[current_lane] - player_width // 2 + 1

    # Обновление врагов
    for enemy in enemies:
        enemy.y += enemy_speed

    # Проверка столкновения
    for enemy in enemies:
        if player_rect.colliderect(enemy):
            print("Игра окончена")
            running = False

    # Удаление врагов за экраном
    enemies = [e for e in enemies if e.y < HEIGHT]

    # Отрисовка линий
    for lane in lanes:
        pygame.draw.line(screen, (50, 50, 50), (lane, 0),
                         (lane, HEIGHT), 2)

    # Отрисовка игрока
    pygame.draw.rect(screen, (255, 0, 0), player_rect)

    # Отрисовка врагов
    for enemy in enemies:
        pygame.draw.rect(screen, (255, 255, 255), enemy)

    pygame.display.flip()

pygame.quit()
sys.exit()
