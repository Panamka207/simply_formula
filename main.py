import pygame
import random
import sys
import json
import os

pygame.init()

WIDTH = 600
HEIGHT = 600
SAVE_FILE = 'save.json'
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Минималистичная гонка")
clock = pygame.time.Clock()

game_state = 'nickname'

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
font = pygame.font.SysFont(None, 50)
font_big = pygame.font.SysFont(None, 80)
font_small = pygame.font.SysFont(None, 40)

running = True

while running:
    clock.tick(60)
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

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

        elif game_state == 'game':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and current_lane > 0:
                    current_lane -= 1
                if event.key == pygame.K_RIGHT and current_lane < 2:
                    current_lane += 1

            if event.type == spawn_event:
                lane = random.choice(lanes)
                enemy_rect = pygame.Rect(0, -100, enemy_width, enemy_height)
                enemy_rect.centerx = lane
                enemies.append({'rect': enemy_rect, 'counted': False})

        elif game_state == 'game_over':
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game_state = 'game'
                score = 0
                enemy_speed = 5
                enemies.clear()
                current_lane = 1

    if game_state == 'game':
        speed_increase_timer += 1
        if speed_increase_timer > 300:
            enemy_speed = 5 + score * 0.1
            speed_increase_timer = 0

        player_rect.x = lanes[current_lane] - player_width // 2

        for enemy in enemies:
            enemy['rect'].y += enemy_speed
            if enemy['rect'].y > player_y and not enemy['counted']:
                score += 1
                enemy['counted'] = True

        for enemy in enemies:
            if player_rect.colliderect(enemy['rect']):
                game_state = 'game_over'
                if score > highscore:
                    highscore = score
                    data['highscore'] = highscore
                    save_data(data)

        enemies = [e for e in enemies if e['rect'].y < HEIGHT]

        for lane in lanes:
            pygame.draw.line(screen, (50, 50, 50),
                             (lane, 0), (lane, HEIGHT), 2)

        pygame.draw.rect(screen, (255, 0, 0), player_rect)

        for enemy in enemies:
            pygame.draw.rect(screen, (255, 255, 255), enemy['rect'])

        score_text = font_small.render(f'Счет: {score}', True, (255, 255, 255))
        screen.blit(score_text, (20, 20))

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

    pygame.display.flip()

pygame.quit()
sys.exit()
