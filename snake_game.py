import pygame
import random
import math
import os
import io
import wave
import struct
pygame.init()
pygame.font.init()
pygame.mixer.init()

# --- Configurations ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 25
COLS = WINDOW_WIDTH // CELL_SIZE
ROWS = WINDOW_HEIGHT // CELL_SIZE
FPS = 60

# Cyberpunk Neon Theme Colors
BG_COLOR = (12, 12, 20)
GRID_COLOR = (25, 25, 45)
SNAKE_HEAD = (0, 255, 255)
SNAKE_TAIL = (0, 80, 150)
FOOD_COLOR = (255, 0, 255)
POWERUP_COLOR = (255, 255, 0)
TEXT_COLOR = (200, 255, 255)

# --- Procedural Audio Generation ---
def create_sound(freq, duration, wave_type='square', volume=0.1):
    try:
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        buf = io.BytesIO()
        with wave.open(buf, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            for i in range(num_samples):
                t = float(i) / sample_rate
                if wave_type == 'square':
                    val = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
                elif wave_type == 'sine':
                    val = math.sin(2.0 * math.pi * freq * t)
                elif wave_type == 'noise':
                    val = random.uniform(-1.0, 1.0)
                else:
                    val = 0.0
                
                # Apply envelope (fade out)
                env = max(0.0, 1.0 - (i / num_samples))
                value = int(volume * 32767.0 * val * env)
                value = max(-32768, min(32767, value))
                frames.extend(struct.pack('<h', value))
            wav_file.writeframes(frames)
        buf.seek(0)
        return pygame.mixer.Sound(buf)
    except Exception as e:
        print(f"Audio init warning: {e}")
        return None

def create_bgm():
    try:
        sample_rate = 44100
        duration = 1.0 # 1 second repeating pulse loop
        num_samples = int(sample_rate * duration)
        buf = io.BytesIO()
        with wave.open(buf, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            for i in range(num_samples):
                t = float(i) / sample_rate
                
                # Envelope for a bass pulse rhythm
                env = 0.0
                if t < 0.25:
                    env = 1.0 - (t / 0.25)
                elif 0.5 <= t < 0.75:
                    env = 1.0 - ((t - 0.5) / 0.25)
                
                freq = 55.0 # A1 bass note
                val = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
                # FM Synthesis dirt
                val += 0.5 * math.sin(2.0 * math.pi * (freq * 2) * t)
                
                value = int(0.12 * 32767.0 * val * env)
                value = max(-32768, min(32767, value))
                frames.extend(struct.pack('<h', value))
            wav_file.writeframes(frames)
        buf.seek(0)
        return pygame.mixer.Sound(buf)
    except Exception as e:
        print(f"BGM init warning: {e}")
        return None

# --- Visual Effects & Utilities ---
def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )

glow_cache = {}
def get_glow_surface(color, radius):
    key = (color, radius)
    if key not in glow_cache:
        # Create surface for additive blending (black background)
        surf = pygame.Surface((radius * 2, radius * 2))
        surf.fill((0, 0, 0))
        for r in range(radius, 0, -1):
            intensity = (1.0 - (r/radius))**2
            c = (
                int(color[0] * intensity),
                int(color[1] * intensity),
                int(color[2] * intensity)
            )
            pygame.draw.circle(surf, c, (radius, radius), r)
        glow_cache[key] = surf
    return glow_cache[key]

def draw_text(surface, text, size, color, pos, font_name='impact', glow=False, align="center"):
    # Fallback to default font if impact isn't available
    font_match = pygame.font.match_font(font_name)
    if font_match:
        font = pygame.font.Font(font_match, size)
    else:
        font = pygame.font.SysFont('arial black', size)
        
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect()
    
    if align == "center":
        text_rect.center = pos
    elif align == "topleft":
        text_rect.topleft = pos
    elif align == "topright":
        text_rect.topright = pos
        
    if glow:
        glow_color = (
            int(color[0] * 0.4),
            int(color[1] * 0.4),
            int(color[2] * 0.4)
        )
        glow_surf = font.render(text, True, glow_color)
        offsets = [(-2,-2), (2,-2), (-2,2), (2,2)]
        for dx, dy in offsets:
            surface.blit(glow_surf, (text_rect.x + dx, text_rect.y + dy), special_flags=pygame.BLEND_RGB_ADD)
            
    surface.blit(text_surf, text_rect)

def draw_eyes(surface, head_rect, direction):
    x, y, w, h = head_rect
    eye_color = (255, 255, 255)
    pupil_color = (0, 0, 0)
    
    if direction == (1, 0): # Right
        e1, e2 = (x + w*0.7, y + h*0.25), (x + w*0.7, y + h*0.75)
    elif direction == (-1, 0): # Left
        e1, e2 = (x + w*0.3, y + h*0.25), (x + w*0.3, y + h*0.75)
    elif direction == (0, 1): # Down
        e1, e2 = (x + w*0.25, y + h*0.7), (x + w*0.75, y + h*0.7)
    elif direction == (0, -1): # Up
        e1, e2 = (x + w*0.25, y + h*0.3), (x + w*0.75, y + h*0.3)
    else:
        e1, e2 = (x + w*0.5, y + h*0.5), (x + w*0.5, y + h*0.5)

    eye_rad = max(2, int(w * 0.2))
    pupil_rad = max(1, int(w * 0.1))
    
    pygame.draw.circle(surface, eye_color, e1, eye_rad)
    pygame.draw.circle(surface, eye_color, e2, eye_rad)
    
    pupil_offset = (direction[0] * pupil_rad, direction[1] * pupil_rad)
    pygame.draw.circle(surface, pupil_color, (e1[0] + pupil_offset[0], e1[1] + pupil_offset[1]), pupil_rad)
    pygame.draw.circle(surface, pupil_color, (e2[0] + pupil_offset[0], e2[1] + pupil_offset[1]), pupil_rad)

# --- Classes ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(50, 250)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.color = color
        self.size = random.randint(4, 9)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt * 1.5

    def draw(self, surface):
        if self.life > 0:
            current_size = max(1, int(self.size * self.life))
            glow = get_glow_surface(self.color, current_size * 2)
            surface.blit(glow, (int(self.x) - glow.get_width()//2, int(self.y) - glow.get_height()//2), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), max(1, current_size - 1))

class Snake:
    def __init__(self):
        start_x, start_y = COLS // 4, ROWS // 2
        self.body = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.prev_body = self.body.copy()
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.pending_growth = 0

    def draw(self, surface, progress):
        for i in range(len(self.body)):
            # Fallback in case arrays mismatch during rapid state changes
            if i >= len(self.prev_body):
                px, py = self.body[i]
            else:
                px, py = self.prev_body[i]
            
            cx, cy = self.body[i]
            
            x = px + (cx - px) * progress
            y = py + (cy - py) * progress
            
            ratio = i / (len(self.body) - 1) if len(self.body) > 1 else 0
            color = lerp_color(SNAKE_HEAD, SNAKE_TAIL, ratio)
            
            # Segment bounding box
            pad = 2
            rect = pygame.Rect(int(x * CELL_SIZE) + pad, int(y * CELL_SIZE) + pad, CELL_SIZE - pad*2, CELL_SIZE - pad*2)
            
            if i == 0:
                # Additive glow on head
                glow_surf = get_glow_surface(SNAKE_HEAD, int(CELL_SIZE * 1.5))
                surface.blit(glow_surf, (rect.centerx - glow_surf.get_width()//2, rect.centery - glow_surf.get_height()//2), special_flags=pygame.BLEND_RGB_ADD)
                
                pygame.draw.rect(surface, color, rect, border_radius=6)
                draw_eyes(surface, rect, self.direction)
            else:
                pygame.draw.rect(surface, color, rect, border_radius=4)

class Game:
    def __init__(self):
        self.state = "START"
        self.particles = []
        self.sounds = self.init_audio()
        self.highscore = self.load_highscore()
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.reset_game()

    def init_audio(self):
        pygame.mixer.init()
        sounds = {
            'eat': create_sound(600, 0.1, 'sine'),
            'powerup': create_sound(880, 0.2, 'square'),
            'gameover': create_sound(100, 0.6, 'noise', volume=0.2),
            'bgm': create_bgm()
        }
        if sounds['bgm']:
            sounds['bgm'].play(loops=-1)
        return sounds

    def play_sound(self, name):
        if self.sounds.get(name):
            self.sounds[name].play()

    def load_highscore(self):
        if not os.path.exists("highscore.txt"):
            with open("highscore.txt", "w") as f:
                f.write("0")
            return 0
        try:
            with open("highscore.txt", "r") as f:
                return int(f.read())
        except:
            return 0

    def save_highscore(self):
        with open("highscore.txt", "w") as f:
            f.write(str(self.highscore))

    def reset_game(self):
        self.snake = Snake()
        self.powerup_pos = None
        self.powerup_timer = 0
        self.score = 0
        self.move_delay = 140
        self.time_since_move = 0
        self.input_queue = []
        self.food_pos = self.spawn_food()

    def spawn_food(self):
        occupied = set(self.snake.body)
        if hasattr(self, 'food_pos') and self.food_pos: occupied.add(self.food_pos)
        if hasattr(self, 'powerup_pos') and self.powerup_pos: occupied.add(self.powerup_pos)
        
        if len(occupied) >= COLS * ROWS:
            return None # Player filled the screen!
            
        while True:
            x, y = random.randint(0, COLS - 1), random.randint(0, ROWS - 1)
            if (x, y) not in occupied:
                return (x, y)

    def spawn_particles(self, x, y, color, count=15):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def trigger_gameover(self):
        self.state = "GAMEOVER"
        self.gameover_timer = 0
        self.play_sound('gameover')
        
        # Explode snake body into particles
        for i, pt in enumerate(self.snake.body):
            ratio = i / (len(self.snake.body) - 1) if len(self.snake.body) > 1 else 0
            color = lerp_color(SNAKE_HEAD, SNAKE_TAIL, ratio)
            px = pt[0] * CELL_SIZE + CELL_SIZE // 2
            py = pt[1] * CELL_SIZE + CELL_SIZE // 2
            self.spawn_particles(px, py, color, count=6)
            
        self.snake.body.clear() # Hide the snake since it exploded
        
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore()

    def logic_update(self):
        if self.input_queue:
            self.snake.next_direction = self.input_queue.pop(0)
            
        self.snake.prev_body = self.snake.body.copy()
        head_x, head_y = self.snake.body[0]
        self.snake.direction = self.snake.next_direction
        new_head = (head_x + self.snake.direction[0], head_y + self.snake.direction[1])
        
        # Wall Collision
        if new_head[0] < 0 or new_head[0] >= COLS or new_head[1] < 0 or new_head[1] >= ROWS:
            self.trigger_gameover()
            return
            
        self.snake.body.insert(0, new_head)
        ate_food = False
        
        # Food Collision
        if new_head == self.food_pos:
            self.snake.pending_growth += 1
            self.score += 10
            self.move_delay = max(50, self.move_delay - 3) # Speed up
            self.play_sound('eat')
            self.spawn_particles(new_head[0]*CELL_SIZE + CELL_SIZE//2, new_head[1]*CELL_SIZE + CELL_SIZE//2, FOOD_COLOR, 15)
            self.food_pos = self.spawn_food()
            ate_food = True
            
        elif self.powerup_pos and new_head == self.powerup_pos:
            self.snake.pending_growth += 3
            self.score += 50
            self.play_sound('powerup')
            self.spawn_particles(new_head[0]*CELL_SIZE + CELL_SIZE//2, new_head[1]*CELL_SIZE + CELL_SIZE//2, POWERUP_COLOR, 30)
            self.powerup_pos = None
            self.powerup_timer = 0
            ate_food = True
            
        # Handle Growth
        if self.snake.pending_growth > 0:
            self.snake.pending_growth -= 1
            self.snake.prev_body.append(self.snake.prev_body[-1])
        else:
            self.snake.body.pop()
            
        # Self Collision
        if new_head in self.snake.body[1:]:
            self.trigger_gameover()
            return
            
        # Powerup Logic
        if self.powerup_pos:
            self.powerup_timer -= 1
            if self.powerup_timer <= 0:
                self.powerup_pos = None
                
        # Powerup spawn (2% chance)
        if not self.powerup_pos and not ate_food and random.random() < 0.02:
            self.powerup_pos = self.spawn_food()
            self.powerup_timer = 50 # lasts 50 logic steps

    def handle_keydown(self, key):
        if key == pygame.K_F11:
            self.is_fullscreen = not self.is_fullscreen
            if self.is_fullscreen:
                self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            return

        if self.state == "START":
            if key == pygame.K_SPACE:
                self.state = "PLAYING"
                self.play_sound('eat')
                
        elif self.state == "GAMEOVER":
            if self.gameover_timer > 1.0 and key == pygame.K_SPACE:
                self.reset_game()
                self.state = "PLAYING"
                self.play_sound('eat')
                
        elif self.state == "PLAYING":
            if key == pygame.K_ESCAPE:
                self.state = "PAUSED"
            else:
                new_dir = None
                if key in (pygame.K_UP, pygame.K_w):
                    new_dir = (0, -1)
                elif key in (pygame.K_DOWN, pygame.K_s):
                    new_dir = (0, 1)
                elif key in (pygame.K_LEFT, pygame.K_a):
                    new_dir = (-1, 0)
                elif key in (pygame.K_RIGHT, pygame.K_d):
                    new_dir = (1, 0)
                    
                if new_dir:
                    last_dir = self.input_queue[-1] if self.input_queue else self.snake.next_direction
                    # Prevent reversing direction
                    if new_dir[0] != -last_dir[0] or new_dir[1] != -last_dir[1]:
                        if new_dir != last_dir and len(self.input_queue) < 2: # Queue size limit
                            self.input_queue.append(new_dir)
                            
        elif self.state == "PAUSED":
            if key in (pygame.K_ESCAPE, pygame.K_SPACE):
                self.state = "PLAYING"

    def update(self, dt):
        for p in self.particles[:]:
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)
                
        if self.state == "PLAYING":
            self.time_since_move += dt * 1000
            while self.time_since_move >= self.move_delay:
                self.time_since_move -= self.move_delay
                self.logic_update()
        elif self.state == "GAMEOVER":
            self.gameover_timer += dt

    def draw_bg(self, surface):
        surface.fill(BG_COLOR)
        # Slow diagonal scroll effect for cyberpunk grid
        time_sec = pygame.time.get_ticks() / 1000.0
        offset_x = int(time_sec * 15) % CELL_SIZE
        offset_y = int(time_sec * 15) % CELL_SIZE
        
        for x in range(offset_x - CELL_SIZE, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(offset_y - CELL_SIZE, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(surface, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))

    def draw(self, surface):
        self.draw_bg(surface)
        
        # Draw Food
        if self.food_pos:
            fx, fy = self.food_pos
            center = (int(fx * CELL_SIZE + CELL_SIZE/2), int(fy * CELL_SIZE + CELL_SIZE/2))
            
            time_sec = pygame.time.get_ticks() / 1000.0
            pulse = (math.sin(time_sec * 8) + 1) / 2
            glow_radius = int(CELL_SIZE * 0.7 + pulse * CELL_SIZE * 0.4)
            
            glow_surf = get_glow_surface(FOOD_COLOR, glow_radius)
            surface.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(surface, FOOD_COLOR, center, int(CELL_SIZE * 0.3))
            pygame.draw.circle(surface, (255, 255, 255), center, int(CELL_SIZE * 0.15))
            
        # Draw Powerup
        if self.powerup_pos:
            fx, fy = self.powerup_pos
            center = (int(fx * CELL_SIZE + CELL_SIZE/2), int(fy * CELL_SIZE + CELL_SIZE/2))
            
            time_sec = pygame.time.get_ticks() / 1000.0
            pulse = (math.sin(time_sec * 15) + 1) / 2
            glow_radius = int(CELL_SIZE * 0.8 + pulse * CELL_SIZE * 0.5)
            
            glow_surf = get_glow_surface(POWERUP_COLOR, glow_radius)
            surface.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(surface, POWERUP_COLOR, center, int(CELL_SIZE * 0.4))
            pygame.draw.circle(surface, (255, 255, 255), center, int(CELL_SIZE * 0.2))
            
            # Powerup Timer Bar
            bar_width = (self.powerup_timer / 50.0) * WINDOW_WIDTH
            pygame.draw.rect(surface, POWERUP_COLOR, (0, 0, bar_width, 4))
            pygame.draw.rect(surface, POWERUP_COLOR, (0, WINDOW_HEIGHT-4, bar_width, 4))

        # Draw Snake
        if self.state in ("PLAYING", "PAUSED", "START") and self.snake.body:
            progress = self.time_since_move / self.move_delay if self.state == "PLAYING" else 0
            self.snake.draw(surface, progress)
            
        # Draw Particles
        for p in self.particles:
            p.draw(surface)
            
        # Draw UI Overlays
        draw_text(surface, f"SCORE: {self.score}", 24, TEXT_COLOR, (20, 20), align="topleft")
        draw_text(surface, f"HIGH: {self.highscore}", 24, TEXT_COLOR, (WINDOW_WIDTH - 20, 20), align="topright")
        
        if self.state == "START":
            draw_text(surface, "NEON SNAKE", 64, SNAKE_HEAD, (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 50), glow=True)
            draw_text(surface, "Press SPACE to Start", 24, TEXT_COLOR, (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 20))
            
        elif self.state == "PAUSED":
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            draw_text(surface, "PAUSED", 64, POWERUP_COLOR, (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 30), glow=True)
            draw_text(surface, "Press ESC to Resume", 24, TEXT_COLOR, (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 30))
            
        elif self.state == "GAMEOVER":
            alpha = min(180, int(self.gameover_timer * 120))
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            surface.blit(overlay, (0, 0))
            
            if self.gameover_timer > 1.0:
                draw_text(surface, "SYSTEM FAILURE", 64, (255, 50, 50), (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 50), glow=True)
                draw_text(surface, f"Final Score: {self.score}", 32, TEXT_COLOR, (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 20))
                draw_text(surface, "Press SPACE to Restart", 24, TEXT_COLOR, (WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 70))

# --- Main Application ---
if __name__ == "__main__":
    pygame.display.set_caption("Neon Cyberpunk Snake")
    clock = pygame.time.Clock()
    game = Game()
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event.key)
                
        game.update(dt)
        game.draw(game.screen)
        pygame.display.flip()
        
    pygame.quit()
