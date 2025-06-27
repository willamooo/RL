# 太空生存戰
import pygame
import random 
import os
from setting import *

# 遊戲初始化 and 創建視窗
# pygame.init()
# pygame.mixer.init()
# screen = pygame.display.set_mode((WIDTH, HEIGHT))
# pygame.display.set_mode((WIDTH, HEIGHT))

from power import Power
from explosion import Explosion
from rock import Rock
from player import Player

import torch

BASE_PATH = os.path.dirname(__file__)
background_img = pygame.image.load(os.path.join(BASE_PATH, "img", "background.png"))

font_name = os.path.join(BASE_PATH, "font.ttf")

class Game:
    def __init__(self):
        self.running = True
        self.player = pygame.sprite.GroupSingle()
        self.player.add(Player())
        self.all_sprites = pygame.sprite.Group()
        self.rocks = pygame.sprite.Group()
        for i in range(8):
            self.new_rock()
        self.powers = pygame.sprite.Group()

        self.score = 0
        self.surface = pygame.Surface((WIDTH, HEIGHT))  # 用來 off-screen 畫畫的
        self.state = pygame.surfarray.array3d(self.surface) # shape (500, 600, 3)
        self.action = 0

        self.is_collided = False
        self.is_hit_rock = False
        self.is_power = False

        self.is_power_shield = 0
        self.is_power_gun = 0
        self.is_collided_radius = 0
        self.combo = 0
        self.no_hit_steps = 0
        self.last_hit_frame = 0
        self.frame_count = 0

             
    def draw_text(self, surf, text, size, x, y):
        font = pygame.font.Font(font_name, size)
        text_surface = font.render(text, True, WHITE)
        text_rect = text_surface.get_rect()
        text_rect.centerx = x
        text_rect.top = y
        surf.blit(text_surface, text_rect)

    def draw_health(self, surf, hp, x, y):
        if hp < 0:
            hp = 0
        BAR_LENGTH = 100
        BAR_HEIGHT = 10
        fill = (hp/100)*BAR_LENGTH
        outline_rect = pygame.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
        fill_rect = pygame.Rect(x, y, fill, BAR_HEIGHT)
        pygame.draw.rect(surf, GREEN, fill_rect)
        pygame.draw.rect(surf, WHITE, outline_rect, 2)

                
    def new_rock(self):
        r = Rock()
        self.all_sprites.add(r)
        self.rocks.add(r)

    def collide_bullet_rock(self):
        # 判斷子彈 石頭相撞
        hits = pygame.sprite.groupcollide(self.rocks, self.player.sprite.bullet_group, True, True)
        if hits:
            for hit in hits:
                # random.choice(expl_sounds).play()
                self.score += hit.radius * 2
                expl = Explosion(hit.rect.center, 'lg')
                self.all_sprites.add(expl)
                if random.random() > 0.8:
                    pow = Power(hit.rect.center)
                    self.all_sprites.add(pow)
                    self.powers.add(pow)
                self.new_rock()
            
            self.is_hit_rock = True

        else:
            self.is_hit_rock = False

    def collide_player_rock(self):
        # 判斷飛船 石頭相撞
        hits = pygame.sprite.spritecollide(self.player.sprite, self.rocks, True, pygame.sprite.collide_circle)
        if hits:
            self.is_collided_radius = hits[0].radius
            self.player.sprite.health -= hits[0].radius * 1
            expl = Explosion(hits[0].rect.center, 'sm')
            self.all_sprites.add(expl)
            self.new_rock()
            self.is_collided = True
        else:
            self.is_collided = False
            self.is_collided_radius = 0

    def collide_player_power(self):
        # 判斷飛船 寶物相撞
        hits = pygame.sprite.spritecollide(self.player.sprite, self.powers, True)
        if hits:
            for hit in hits:
                if hit.type == 'shield':
                    # 新增
                    self.is_power_shield = 1
                    #
                    self.player.sprite.health += 20
                    if self.player.sprite.health > 100:
                        self.player.sprite.health = 100
                elif hit.type == 'gun':
                    # 新增
                    self.is_power_gun = 1
                    #
                    self.player.sprite.gunup()
            self.is_power = True
        else:
            self.is_power = False

    def check_state(self):
        if self.player.sprite.health <= 0:
            death_expl = Explosion(self.player.sprite.rect.center, 'player')
            self.all_sprites.add(death_expl)
            
            self.player.sprite.lives -= 1
            # self.player.sprite.health = 100
            self.player.sprite.hide()

        if self.player.sprite.lives == 0:
            # die_sound.play()
            self.running = False

    def update(self, action):
        # 更新遊戲
        self.is_power_shield = 0
        self.is_power_gun = 0
        self.frame_count += 1
        self.all_sprites.update()
        self.player.update(action)
        self.collide_bullet_rock()
        self.collide_player_rock()
        self.collide_player_power()
        self.check_state()
        

    def draw(self, screen=None):
        surface = self.surface if screen is None else screen
        surface.fill(BLACK)
        surface.blit(background_img, (0, 0))
        self.all_sprites.draw(surface)
        self.player.draw(surface)
        self.player.sprite.bullet_group.draw(surface)
        self.draw_text(surface, str(self.score), 18, WIDTH/2, 10)
        self.draw_health(surface, self.player.sprite.health, 5, 15)

        # 更新 state
        self.state = pygame.surfarray.array3d(surface)

        # 只有 render 模式才更新視窗
        if screen is not None:
            pygame.display.update()



    # def get_closest_rock(game):
    #     player_x = game.player.sprite.rect.centerx
    #     return min(game.rocks, key=lambda r: abs(r.rect.centerx - player_x))

    # def get_closest_power(game):
    #     if not game.powers:
    #         dummy = pygame.sprite.Sprite()
    #         dummy.rect = pygame.Rect(WIDTH // 2, HEIGHT // 2, 0, 0)
    #         dummy.type = 'shield'
    #         return dummy
    #     return min(game.powers, key=lambda p: abs(p.rect.centerx - game.player.sprite.rect.centerx))

    # def get_state_vector(game):
    #     player = game.player.sprite
    #     rock = get_closest_rock(game)
    #     power = get_closest_power(game)
        
    #     return torch.tensor([
    #         player.rect.centerx / WIDTH,
    #         player.health / 100,
    #         float(player.gun > 1),
    #         rock.rect.centerx / WIDTH,
    #         rock.rect.centery / HEIGHT,
    #         rock.radius / 50,
    #         power.rect.centerx / WIDTH,
    #         power.rect.centery / HEIGHT,
    #         float(power.type == 'gun')
    #     ], dtype=torch.float32)


