import pygame
from sys import exit
import itertools
import random

pygame.init()
pygame.font.init()
pygame.mixer.init()

# Window Setup
WIDTH, HEIGHT = 900, 500
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Invaders by David Labitzke")
SCREEN_MARGIN = 40

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (88, 255, 0)

# Clock
clock = pygame.time.Clock()
FPS = 60

# Other Constants
SPACESHIP_SPAWN_ODDS = 400
enemy_start_y = 75


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.width, self.height = 50, 40
        self.image = pygame.transform.scale(
            pygame.image.load("Sprites/player/player.png"),
            (self.width, self.height)).convert_alpha()

        self.death_image = pygame.transform.scale(
            pygame.image.load("Sprites/player-death/player-death_img.png"),
            (self.width, self.height)).convert_alpha()

        self.x, self.y = center_label(self.image), HEIGHT - self.image.get_height()
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.image)

        self.vel = 5

        self.bullets = pygame.sprite.GroupSingle()
        self.bullet_image_str = "Sprites/bullets/player_bullet.png"

        self.score = 0

        self.lives = 3
        self.is_dying = False
        self.death_animation_cooldown = 0
        self.death_sound = pygame.mixer.Sound("Audio/player_dead.wav")
        self.death_sound.set_volume(0.4)
        self.death_sound_played = False

        self.laser_sound = pygame.mixer.Sound("Audio/player_laser.wav")
        self.laser_sound.set_volume(0.25)

    def get_player_inputs(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.x > SCREEN_MARGIN:
            self.x -= self.vel
        if keys[pygame.K_RIGHT] and self.x < WIDTH - SCREEN_MARGIN - self.image.get_width():
            self.x += self.vel
        if keys[pygame.K_SPACE]:
            self.shoot()

    def shoot(self):
        if not self.bullets:
            bullet = Bullet(self.x + self.image.get_width() / 2, self.y - self.image.get_height() / 2,
                            self.bullet_image_str)
            self.bullets.add(bullet)
            self.laser_sound.play()

    def animate_death(self, spaceship_enemy, enemy_manager):
        if not self.death_sound_played:
            self.death_sound.play()
            self.death_sound_played = True
        if self.death_animation_cooldown >= 120:
            self.death_animation_cooldown = 0
            self.lives -= 1
            if spaceship_enemy:
                spaceship_enemy.sprite.kill()
            self.bullets.empty()
            self.is_dying = False
            self.death_sound_played = False
            self.x, self.y = center_label(self.image), HEIGHT - self.image.get_height()
            for enemy in enemy_manager:
                enemy.bullets.empty()
        else:
            window.fill(GREEN)
            window.blit(self.death_image, (self.x, self.y))
            self.death_animation_cooldown += 1

    def update(self, enemy_list, spaceship_enemy, walls) -> None:
        if not self.is_dying:
            self.get_player_inputs()
            self.rect.topleft = (self.x, self.y)
            if self.bullets:
                for bullet in self.bullets:
                    bullet.move(True)
                    for enemy in enemy_list:
                        if bullet.collide(enemy) and not enemy.hit:
                            self.score += enemy.points
                            bullet.kill()
                            enemy.hit = True
                    for ship in spaceship_enemy:
                        if bullet.collide(ship):
                            self.score += ship.points
                            bullet.kill()
                            ship.hit = True
                    for wall in walls:
                        if bullet.collide(wall):
                            wall.health -= 1
                            bullet.kill()
                    if bullet.is_off_screen():
                        self.bullets.empty()
                self.bullets.update()
                self.bullets.draw(window)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, image_str, x, y, points):
        super().__init__()
        self.width, self.height = 32, 32
        self.image_num = itertools.cycle([1, 0])
        self.image_str = image_str
        self.image = pygame.transform.scale(
            pygame.image.load(self.image_str),
            (self.width, self.height)).convert_alpha()

        self.x, self.y = x, y
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.image)

        self.vel = 10

        self.should_move_right_options = itertools.cycle([False, True])
        self.should_move_right = True

        self.bullets = pygame.sprite.GroupSingle()
        self.bullet_image_str = "Sprites/bullets/enemy_bullet.png"

        self.points = points

        self.hit = False
        self.death_image_num_cycler = itertools.cycle([0, 1, 2, 3, 4, 5])
        self.death_image_num = next(self.death_image_num_cycler)
        self.death_image_str = f"Sprites/enemy-death/enemy-death_{self.death_image_num}.png"
        self.death_audio = pygame.mixer.Sound("Audio/enemy_dead.wav")
        self.death_audio.set_volume(0.15)
        self.death_audio_played = False

    def animate(self):
        if not self.hit:
            self.image_str = f"{self.image_str.split('_')[0]}_{next(self.image_num)}.png"
            self.image = pygame.transform.scale(
                pygame.image.load(self.image_str),
                (self.width, self.height))

    def animate_death(self):
        if not self.death_audio_played:
            self.death_audio.play()
            self.death_audio_played = True
        if self.death_image_num >= 5:
            if not self.bullets:
                self.kill()
            else:
                self.image = None
        else:
            self.image_str = f"{self.death_image_str.split('_')[0]}_{self.death_image_num}.png"
            self.image = pygame.transform.scale(
                pygame.image.load(self.image_str), (self.width, self.height))
            self.death_image_num = next(self.death_image_num_cycler)

    def shoot(self):
        if not self.bullets:
            rng_shoot = random.randint(0, 10)
            if rng_shoot == 1:
                bullet = Bullet(self.x + self.image.get_width() / 2, self.y - self.image.get_height() / 2,
                                self.bullet_image_str)
                self.bullets.add(bullet)

    def collide(self, obj):
        offset_x = obj.x - self.x
        offset_y = obj.y - self.y
        return self.mask.overlap(obj.mask, (offset_x, offset_y)) is not None

    def collision(self, obj):
        return self.collide(obj)

    def is_too_low(self):
        return self.y >= 450

    def draw(self, screen):
        if self.image is not None:
            screen.blit(self.image, self.rect)

    def update(self, player, walls):
        self.rect.topleft = (self.x, self.y)
        if self.hit:
            self.animate_death()
        for bullet in self.bullets:
            bullet.move(False)
            for wall in walls:
                if bullet.collide(wall):
                    wall.health -= 1
                    bullet.kill()
            if bullet.collide(player):
                player.is_dying = True
            if bullet.is_off_screen():
                self.bullets.empty()
            self.bullets.update()
            self.bullets.draw(window)

        for wall in walls:
            if self.collide(wall):
                wall.health -= 5
                self.kill()


class SpaceShip(pygame.sprite.Sprite):
    def __init__(self, should_move_right):
        super().__init__()
        self.points_options = [10, 25, 50, 100, 250]
        self.points = random.choice(self.points_options)
        self.width, self.height = 50, 32
        self.image_num = itertools.cycle([0, 1])
        self.image_str = f"Sprites/spaceship/spaceship_{next(self.image_num)}.png"
        self.image = pygame.transform.scale(
            pygame.image.load(self.image_str),
            (self.width, self.height)).convert_alpha()

        self.should_move_right = should_move_right
        if self.should_move_right:
            self.x = -(self.image.get_width())
        else:
            self.x = WIDTH + self.image.get_width()
        self.y = 50

        self.audio = pygame.mixer.Sound("Audio/spaceship_animation.wav")
        self.audio.set_volume(0.1)

        self.vel = 2 if self.should_move_right else -2

        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.image)
        self.hit = False
        self.death_animation_counter = 0
        self.death_audio = pygame.mixer.Sound("Audio/spaceship_dead.wav")
        self.death_audio.set_volume(0.4)
        self.death_audio_played = False

    def animate(self, player):
        if not self.hit:
            self.image_str = f"Sprites/spaceship/spaceship_{next(self.image_num)}.png"
            self.image = pygame.transform.scale(
                pygame.image.load(self.image_str),
                (self.width, self.height)).convert_alpha()
            if not player.is_dying:
                self.audio.play()

    def is_off_screen(self):
        return self.x <= -(self.image.get_width()) or self.x >= WIDTH + self.image.get_width()

    def update(self, main_font):
        if not self.hit:
            self.x += self.vel
            self.rect.topleft = (self.x, self.y)
            if self.is_off_screen():
                self.kill()
        else:
            if not self.death_audio_played:
                self.death_audio.play()
                self.death_audio_played = True
            if self.death_animation_counter < 60:
                if not 15 < self.death_animation_counter < 25:
                    death_label = main_font.render(f"{self.points}", True, WHITE)
                    window.blit(death_label, (self.x, self.y))
                self.death_animation_counter += 1
            else:
                self.kill()


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width, self.height = 100, 100
        self.image = pygame.transform.scale(
            pygame.image.load("Sprites/wall/wall.png"),
            (self.width, self.height)).convert_alpha()
        self.x, self.y = x, y
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.health = 30

    def update(self, small_font):
        health_label = small_font.render(f"{self.health}", True, WHITE)
        self.rect.topleft = (self.x, self.y)
        window.blit(health_label,
                    (self.x + self.image.get_width() / 2, self.y + self.image.get_height()))
        if self.health <= 0:
            self.kill()


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, image_str):
        super().__init__()
        self.width, self.height = 32, 30
        self.image = pygame.transform.scale(
            pygame.image.load(image_str),
            (self.width, self.height))
        self.x, self.y = x - self.image.get_width() / 2, y + self.image.get_height() / 2
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.vel = 5
        self.mask = pygame.mask.from_surface(self.image)

    def move(self, move_up: bool):
        self.y += -(self.vel * 2) if move_up else self.vel
        self.rect.topleft = (self.x, self.y)

    def is_off_screen(self):
        return not HEIGHT >= self.y >= -(self.image.get_height())

    def collide(self, obj):
        offset_x = obj.x - self.x
        offset_y = obj.y - self.y
        return self.mask.overlap(obj.mask, (offset_x, offset_y)) is not None

    def collision(self, obj):
        return self.collide(obj)


def create_new_enemies(group, y):
    enemy3_image_str = "Sprites/enemy3/enemy3_0.png"
    enemy2_image_str = "Sprites/enemy2/enemy2_0.png"
    enemy1_image_str = "Sprites/enemy1/enemy1_0.png"
    image_str_to_use = enemy3_image_str
    points = 50
    x_pos = 200
    for i in range(50):
        new_enemy = Enemy(image_str_to_use, x_pos, y, points)
        group.add(new_enemy)
        x_pos += 50
        if x_pos >= 700:
            x_pos = 200
            y += 25
        if i == 9:
            image_str_to_use = enemy2_image_str
            points = 25
        elif i == 29:
            image_str_to_use = enemy1_image_str
            points = 10


def lower_enemies(enemy_manager):
    for enemy in enemy_manager:
        enemy.y += 20
        enemy.rect.topleft = (enemy.x, enemy.y)
        enemy.vel *= -1
        enemy.should_move_right = next(enemy.should_move_right_options)
        enemy.animate()
    return 85


def manage_enemy_movement(enemy_manager):
    right_limit = WIDTH - SCREEN_MARGIN - 32
    left_limit = SCREEN_MARGIN
    right_limit_reached = any(enemy.x >= right_limit for enemy in enemy_manager) and all(enemy.should_move_right
                                                                                         for enemy in enemy_manager)
    left_limit_reached = any(enemy.x <= left_limit for enemy in enemy_manager) and all(not enemy.should_move_right
                                                                                       for enemy in enemy_manager)
    decrement_amount = 0
    if left_limit_reached or right_limit_reached:
        decrement_amount = lower_enemies(enemy_manager)
    else:
        for enemy in enemy_manager:
            enemy.x += enemy.vel
            enemy.rect.topleft = (enemy.x, enemy.y)
            enemy.animate()
    return decrement_amount


def create_new_walls(group):
    x_pos, y_pos = 100, 350
    for i in range(4):
        group.add(Wall(x_pos, y_pos))
        x_pos += 200


def game_over_screen(game_over_font, main_font, player_score):
    window.fill(GREEN)
    game_over_label = game_over_font.render("Game Over!!!", True, BLACK)
    high_score_label = main_font.render(f"New High Score!!! {player_score}", True, BLACK)
    window.blit(game_over_label, (center_label(game_over_label), HEIGHT / 2 - game_over_label.get_height()))
    if is_new_high_score(player_score):
        window.blit(high_score_label, (center_label(high_score_label), HEIGHT / 2 + high_score_label.get_height()))


def get_current_high_score():
    with open("high_score.csv", "r") as high_score:
        return high_score.read()


def is_new_high_score(player_score):
    current_high_score = int(get_current_high_score())
    return player_score > current_high_score


def update_high_score(player_score):
    with open("high_score.csv", "w") as high_score:
        high_score.write(str(player_score))


def center_label(label):
    return WIDTH / 2 - label.get_width() / 2


def main_menu():
    main_menu_counter = 0
    space_font = pygame.font.SysFont("bahnschrift", 72)
    invaders_font = pygame.font.SysFont("bahnschrift", 48)
    main_font = pygame.font.SysFont("bahnschrift", 32)

    enemy1_image = pygame.transform.scale(
        pygame.image.load("Sprites/enemy1/enemy1_0.png"),
        (32, 32)).convert_alpha()
    enemy2_image = pygame.transform.scale(
        pygame.image.load("Sprites/enemy2/enemy2_0.png"),
        (32, 32)).convert_alpha()
    enemy3_image = pygame.transform.scale(
        pygame.image.load("Sprites/enemy3/enemy3_0.png"),
        (32, 32)).convert_alpha()
    spaceship_image = pygame.transform.scale(
        pygame.image.load("Sprites/spaceship/spaceship_0.png"),
        (50, 32)).convert_alpha()

    run = True
    while run:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        if main_menu_counter >= 6000:
            if keys[pygame.K_RETURN]:
                main()
            if keys[pygame.K_c]:
                credits_page()
            if keys[pygame.K_r]:
                rules_page()

        window.fill(BLACK)

        space_label = space_font.render("Space", True, WHITE)
        invaders_label = invaders_font.render("Invaders", True, GREEN)
        points_label = main_font.render("Points", True, WHITE)
        enemy1_equals_label = main_font.render(" = 10", True, WHITE)
        enemy2_equals_label = main_font.render(" = 25", True, WHITE)
        enemy3_equals_label = main_font.render(" = 50", True, WHITE)
        spaceship_equals_label = main_font.render(" = ???", True, WHITE)
        begin_label = main_font.render("Click Enter to Start", True, WHITE)
        rules_label = main_font.render("Click R to Read the Rules", True, WHITE)
        credits_label = main_font.render("Click C for Credits", True, WHITE)

        window.blit(space_label, (center_label(space_label), 20))
        window.blit(invaders_label, (center_label(invaders_label), 85))
        window.blit(points_label, (center_label(points_label), 150))
        pygame.draw.line(window, WHITE, (center_label(points_label), 180),
                         (center_label(points_label) + points_label.get_width(), 180), 2)

        if main_menu_counter >= 1200:
            window.blit(enemy1_image, (400, 190))
            window.blit(enemy1_equals_label, (440, 190))
        if main_menu_counter >= 2400:
            window.blit(enemy2_image, (400, 225))
            window.blit(enemy2_equals_label, (440, 225))
        if main_menu_counter >= 3600:
            window.blit(enemy3_image, (400, 250))
            window.blit(enemy3_equals_label, (440, 255))
        if main_menu_counter >= 4800:
            window.blit(spaceship_image, (390, 285))
            window.blit(spaceship_equals_label, (440, 285))
        if main_menu_counter >= 6000:
            window.blit(begin_label, (center_label(begin_label), 350))
            window.blit(rules_label, (center_label(rules_label), 410))
            window.blit(credits_label, (center_label(credits_label), HEIGHT - credits_label.get_height()))

        pygame.display.update()
        if main_menu_counter <= 7000:
            main_menu_counter += 1

    pygame.quit()
    exit()


def credits_page():
    credits_font = pygame.font.SysFont("bahnschrift", 72)
    main_font = pygame.font.SysFont("bahnschrift", 32)
    subscript_font = pygame.font.SysFont("bahnschrift", 24)

    run = True
    while run:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        if keys[pygame.K_RETURN]:
            main_menu()

        credits_label = credits_font.render("Credits", True, WHITE)

        created_by_label = main_font.render("Created By", True, GREEN)
        created_by_x, created_by_y = center_label(created_by_label), 80
        my_name_label = subscript_font.render("David Labitzke", True, WHITE)

        sprite_resources_label = main_font.render("Sprites Created Using", True, GREEN)
        sprites_x, sprites_y = center_label(sprite_resources_label), 160
        sprites_website_label = subscript_font.render("www.piskelapp.com", True, WHITE)

        audio_resources_label = main_font.render("Audio Created Using/Courtesy Of", True, GREEN)
        audio_x, audio_y = center_label(audio_resources_label), 250
        audio_website1_label = subscript_font.render("www.sfxr.me", True, WHITE)
        audio_website2_label = subscript_font.render("www.classicgaming.cc/classics/space-invaders/sounds", True, WHITE)

        based_on_label = main_font.render("Modeled After", True, GREEN)
        based_on_x, based_on_y = center_label(based_on_label), HEIGHT - based_on_label.get_height() * 4
        website_model_label = subscript_font.render("freeinvaders.org", True, WHITE)

        return_label = main_font.render("Click Enter to Return to Main Menu", True, WHITE)

        window.fill(BLACK)

        window.blit(credits_label, (center_label(credits_label), 10))
        window.blit(created_by_label, (created_by_x, created_by_y))
        pygame.draw.line(window, GREEN,
                         (created_by_x, created_by_y + created_by_label.get_height()),
                         (created_by_x + created_by_label.get_width(), created_by_y + created_by_label.get_height()), 2)
        window.blit(my_name_label,
                    (created_by_x, created_by_y + my_name_label.get_height() + created_by_label.get_height() / 2))

        window.blit(sprite_resources_label, (sprites_x, sprites_y))
        pygame.draw.line(window, GREEN,
                         (sprites_x, sprites_y + sprite_resources_label.get_height()),
                         (sprites_x + sprite_resources_label.get_width(),
                          sprites_y + sprite_resources_label.get_height()), 2)
        window.blit(sprites_website_label,
                    (center_label(sprites_website_label),
                     sprites_y + sprites_website_label.get_height() + sprite_resources_label.get_height() / 2))

        window.blit(audio_resources_label, (audio_x, audio_y))
        pygame.draw.line(window, GREEN,
                         (audio_x, audio_y + audio_resources_label.get_height()),
                         (audio_x + audio_resources_label.get_width(),
                          audio_y + audio_resources_label.get_height()), 2)
        window.blit(audio_website1_label, (center_label(audio_website1_label),
                                           audio_y + audio_website1_label.get_height()
                                           + audio_website1_label.get_height()))
        window.blit(audio_website2_label, (center_label(audio_website2_label),
                                           audio_y + audio_website1_label.get_height()
                                           + audio_website1_label.get_height() + audio_website2_label.get_height()))

        window.blit(based_on_label, (based_on_x, based_on_y))
        pygame.draw.line(window, GREEN,
                         (based_on_x, based_on_y + based_on_label.get_height()),
                         (based_on_x + based_on_label.get_width(),
                          based_on_y + based_on_label.get_height()), 2)
        window.blit(website_model_label,
                    (center_label(website_model_label),
                     based_on_y + website_model_label.get_height() + based_on_label.get_height() / 2))
        window.blit(return_label, (center_label(return_label), HEIGHT - return_label.get_height()))

        pygame.display.update()

    main_menu()


def rules_page():
    rules_font = pygame.font.SysFont("bahnschrift", 72)
    main_font = pygame.font.SysFont("bahnschrift", 32)
    subscript_font = pygame.font.SysFont("bahnschrift", 18)

    run = True
    while run:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        if keys[pygame.K_RETURN]:
            main_menu()

        rules_label = rules_font.render("Rules", True, WHITE)
        objective_label = main_font.render("Objective", True, GREEN)
        objective1 = subscript_font.render(
            "The main objective is to survive as long as possible against the swarm of enemies.", True, WHITE)
        objective2 = subscript_font.render("The white enemies on screen will be shooting at you, "
                                           "progressively moving closer to you, and gaining speed.", True, WHITE)
        objective3 = subscript_font.render("On the bottom of the screen are 4 walls, each with 30 hit points.",
                                           True, WHITE)
        objective4 = subscript_font.render("They can absorb enemy and player bullets, "
                                           "and will lose 1 hit point each time.", True, WHITE)
        objective5 = subscript_font.render("If an enemy crashes into the wall, "
                                           "it will be killed and the wall will lose 5 hit points.", True, WHITE)
        objective6 = subscript_font.render("If a wall loses all its hit points, "
                                           "it will be removed for the remainder of the game.", True, WHITE)
        objective7 = subscript_font.render("If you are hit by an enemy bullet, you will lose a life.", True, WHITE)
        objective8 = subscript_font.render("If you survive a swarm, the swarm will be reset, "
                                           "and you will gain a life.", True, WHITE)
        objective9 = subscript_font.render("The game ends when either the player loses all their lives, "
                                           "or the enemies reach the bottom of the screen.", True, WHITE)

        controls_label = main_font.render("Controls", True, GREEN)
        control1 = subscript_font.render("Left = move left", True, WHITE)
        control2 = subscript_font.render("Right = move right", True, WHITE)
        control3 = subscript_font.render("Space = shoot", True, WHITE)

        return_label = main_font.render("Click Enter to Return to Main Menu", True, WHITE)

        window.fill(BLACK)

        window.blit(rules_label, (center_label(rules_label), 10))
        window.blit(objective_label, (center_label(objective_label), 80))
        pygame.draw.line(window, GREEN, (center_label(objective_label), 110),
                         (center_label(objective_label) + objective_label.get_width(), 110), 2)

        window.blit(objective1, (center_label(objective1), 120))
        window.blit(objective2, (center_label(objective2), 140))
        window.blit(objective3, (center_label(objective3), 160))
        window.blit(objective4, (center_label(objective4), 180))
        window.blit(objective5, (center_label(objective5), 200))
        window.blit(objective6, (center_label(objective6), 220))
        window.blit(objective7, (center_label(objective7), 240))
        window.blit(objective8, (center_label(objective8), 260))
        window.blit(objective9, (center_label(objective9), 280))

        window.blit(controls_label, (center_label(controls_label), 310))
        pygame.draw.line(window, GREEN, (center_label(controls_label), 340),
                         (center_label(controls_label) + controls_label.get_width(), 340), 2)
        window.blit(control1, (center_label(control1), 350))
        window.blit(control2, (center_label(control2), 370))
        window.blit(control3, (center_label(control3), 390))

        window.blit(return_label, (center_label(return_label), HEIGHT - return_label.get_height() * 2))

        pygame.display.update()

    pygame.quit()
    exit()


def main():
    global enemy_start_y
    # Defined Events
    move_enemies = pygame.USEREVENT + 1
    base_movement_ratio = 1000
    movement_ratio = base_movement_ratio
    pygame.time.set_timer(move_enemies, movement_ratio)

    animate_spaceship_enemy = pygame.USEREVENT + 2
    pygame.time.set_timer(animate_spaceship_enemy, 800)

    random_enemy_shoot = pygame.USEREVENT + 3
    enemy_shoot_rate = 100
    pygame.time.set_timer(random_enemy_shoot, enemy_shoot_rate)

    main_font = pygame.font.SysFont("bahnschrift", 32)
    small_font = pygame.font.SysFont("bahnschrift", 24)
    game_over_font = pygame.font.SysFont("bahnschrift", 64)

    player = pygame.sprite.GroupSingle()
    player.add(Player())

    enemy_manager = pygame.sprite.Group()
    create_new_enemies(enemy_manager, enemy_start_y)

    spaceship_enemy = pygame.sprite.GroupSingle()
    spaceship_should_move_right_options = [True, False]

    walls = pygame.sprite.Group()
    create_new_walls(walls)

    current_level = 1

    game_over_counter = 0
    game_over_audio = pygame.mixer.Sound("Audio/game_over.wav")
    new_high_score_audio = pygame.mixer.Sound("Audio/new_high_score.wav")
    new_high_score_audio.set_volume(0.3)
    game_over_audio.set_volume(0.3)
    game_over_audio_played = False

    audio_num_cycler = itertools.cycle([0, 1, 2, 3])
    audio_num = next(audio_num_cycler)
    audio = pygame.mixer.Sound(f"Audio/Enemy_Animation/enemy_animation_{audio_num}.wav")
    audio.set_volume(0.2)

    while True:
        current_score_label = main_font.render(f"Score: {player.sprite.score}", True, WHITE)
        lives_label = small_font.render(f"Lives: {player.sprite.lives}", True, WHITE)
        level_label = small_font.render(f"Level: {current_level}", True, WHITE)
        high_score_label = main_font.render(f"High Score: {get_current_high_score()}", True, WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == move_enemies and not player.sprite.is_dying:
                movement_ratio -= manage_enemy_movement(enemy_manager)
                if movement_ratio < 50:
                    movement_ratio = 50
                pygame.time.set_timer(move_enemies, movement_ratio)
                if player.sprite.lives > 0:
                    audio.play()
                    audio_num = next(audio_num_cycler)
                    audio = pygame.mixer.Sound(f"Audio/Enemy_Animation/enemy_animation_{audio_num}.wav")
                    audio.set_volume(0.2)
            if event.type == animate_spaceship_enemy:
                if spaceship_enemy:
                    spaceship_enemy.sprite.animate(player.sprite)
            if event.type == random_enemy_shoot:
                if enemy_manager:
                    enemy_to_shoot = random.choice(enemy_manager.sprites())
                    enemy_to_shoot.shoot()

        if player.sprite.lives <= 0 or any(enemy.is_too_low() for enemy in enemy_manager):
            if not game_over_audio_played:
                if is_new_high_score(player.sprite.score):
                    new_high_score_audio.play()
                else:
                    game_over_audio.play()
                game_over_audio_played = True

            if game_over_counter >= 300:
                if is_new_high_score(player.sprite.score):
                    update_high_score(player.sprite.score)
                enemy_start_y = 75
                main_menu()
            else:
                game_over_screen(game_over_font, main_font, player.sprite.score)
                game_over_counter += 1
        else:
            if player.sprite.is_dying:
                player.sprite.animate_death(spaceship_enemy, enemy_manager)
            else:
                window.fill(BLACK)
                player.update(enemy_manager, spaceship_enemy, walls)
                player.draw(window)

                if random.randint(1, SPACESHIP_SPAWN_ODDS) == 1 and not spaceship_enemy:
                    spaceship_enemy.add(SpaceShip(random.choice(spaceship_should_move_right_options)))

                if not enemy_manager:
                    while audio_num != 0:
                        audio_num = next(audio_num_cycler)
                        audio = pygame.mixer.Sound(f"Audio/Enemy_Animation/enemy_animation_{audio_num}.wav")
                        audio.set_volume(0.2)

                    if spaceship_enemy:
                        spaceship_enemy.sprite.kill()

                    if current_level <= 6:
                        enemy_start_y += 25

                    create_new_enemies(enemy_manager, enemy_start_y)
                    player.sprite.lives += 1
                    current_level += 1

                    base_movement_ratio -= 85
                    if base_movement_ratio <= 50:
                        base_movement_ratio = 50
                    movement_ratio = base_movement_ratio
                    pygame.time.set_timer(move_enemies, movement_ratio)
                    enemy_shoot_rate *= 0.98
                    enemy_shoot_rate = round(enemy_shoot_rate)
                    pygame.time.set_timer(random_enemy_shoot, enemy_shoot_rate)

                for enemy in enemy_manager:
                    enemy.update(player.sprite, walls)
                    enemy.draw(window)

                spaceship_enemy.update(main_font)
                if spaceship_enemy and not spaceship_enemy.sprite.hit:
                    spaceship_enemy.draw(window)

                for wall in walls:
                    wall.update(small_font)
                walls.draw(window)

                window.blit(current_score_label, (center_label(current_score_label) - 50, 10))
                window.blit(lives_label, (SCREEN_MARGIN, 10))
                window.blit(level_label, (SCREEN_MARGIN, 10 + level_label.get_height()))
                window.blit(high_score_label, (WIDTH - high_score_label.get_width() - SCREEN_MARGIN, 10))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main_menu()
