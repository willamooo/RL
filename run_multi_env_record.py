import os
import sys
import torch
import numpy as np
import imageio
import pygame
from PIL import Image
from collections import deque
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'space_ship_game_RL'))

# 載入自訂模組
script_dir = os.path.join(os.getcwd(), 'space_ship_game_RL')
if script_dir not in sys.path:
    sys.path.append(script_dir)
from setting import *
from game import Game



# --- 定義 SpaceShipEnv ---
class SpaceShipEnv():
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = None
        self.clock = pygame.time.Clock()
        self.fps = FPS
        self.game = Game()
        self.action_space = [0, 1, 2, 3]
        self.observation = self.game.state
        self.prev_score = 0
    def step(self, action):
        self.game.update(action)
        if self.screen is None:
            self.game.draw()
        else:
            self.game.draw(self.screen)
            self.clock.tick(self.fps)
        state = self.game.state
        reward  = 0.0
        reward += self.game.is_hit_rock * 80
        reward += self.game.is_power * 50
        reward -= self.game.is_collided * 100
        reward += 0.01
        reward += (self.game.score - self.prev_score) * 0.1
        self.prev_score = self.game.score
        done = not self.game.running or self.game.score >= 10000
        info = {
            "score": self.game.score,
            "health": self.game.player.sprite.health
        }
        return state, reward, done, info
    def reset(self):
        self.game = Game()
        return self.game.state
    def render(self):
        if self.screen is None:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            pygame.display.set_caption("SpaceShip RL Environment")
    def close(self):
        pygame.quit()

# --- DQN Model ---
import torch.nn as nn
class DQN(nn.Module):
    def __init__(self, in_channels, num_actions):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, num_actions)
        )
    def forward(self, x):
        x = self.conv(x / 255.0)
        return self.fc(x)

# --- 預處理 ---
import cv2
def preprocess_state(state, stacked_state=None, is_new=False):
    gray = cv2.cvtColor(state, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, (84, 84), interpolation=cv2.INTER_AREA)
    gray = torch.tensor(gray, dtype=torch.uint8).unsqueeze(0)
    if is_new or stacked_state is None:
        stacked_state = gray.repeat(4, 1, 1)
    else:
        stacked_state = torch.cat((gray, stacked_state[:-1]), dim=0)
    return stacked_state.float().unsqueeze(0), stacked_state

# --- 多進程驗收錄影 ---
import multiprocessing

def run_env(idx, device, checkpoint_path):
    import pygame
    import os
    # 視窗排列參數
    WINDOW_W, WINDOW_H = 250, 350
    WINDOWS_PER_ROW = 6
    row = idx // WINDOWS_PER_ROW
    col = idx % WINDOWS_PER_ROW
    x = col * WINDOW_W
    y = row * WINDOW_H
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"
    env = SpaceShipEnv()
    env.render()
    state_raw = env.reset()
    state_b, state = preprocess_state(state_raw, None, True)
    done = False
    frames = []
    score = 0
    # 每個 process 都要自己 load model
    num_actions = 4
    i_channels = 4
    model = DQN(i_channels, num_actions).to(device)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['policy_net'])
    model.eval()
    while not done:
        state_tensor = state_b.to(device)
        q_values = model(state_tensor)
        action = torch.argmax(q_values, dim=1).item()
        next_state_raw, reward, done, info = env.step(action)
        next_state_b, next_state = preprocess_state(next_state_raw, state, False)
        state_b, state = next_state_b, next_state
        score = info['score']
        # 錄影
        surface = pygame.display.get_surface()
        frame = pygame.surfarray.array3d(surface)
        frame = np.transpose(frame, (1, 0, 2))
        frames.append(frame)
        pygame.event.pump()
    env.close()
    # 儲存影片
    if score > 4000:
        video_dir = 'video'
        os.makedirs(video_dir, exist_ok=True)
        video_path = os.path.join(video_dir, f"run_{idx}_score_{score}.mp4")
        imageio.mimsave(video_path, frames, fps=60, quality=9)
        print(f"Process {idx} finished, score={score}, video saved to {video_path}")
    else:
        print(f"Process {idx} finished, score={score}, video not saved (score < 4000)")

if __name__ == '__main__':
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint_path = 'checkpoint_V2.pth'
    checkpoint = torch.load(checkpoint_path, map_location=device)
    num_envs = 12  # 5x3
    procs = []
    for i in range(num_envs):
        p = multiprocessing.Process(target=run_env, args=(i, device, checkpoint_path))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
