import pygame
import sys
import random
import math
import numpy as np
import tensorflow as tf

# Initialize Pygame
pygame.init()
pygame.mixer.init()
# Get actual screen size
info = pygame.display.Info()
# We use your 800x600 logic, but scale it to the phone's actual pixels
screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
WIDTH, HEIGHT = info.current_w, info.current_h

# Load the files from your folder
# Initialize mixer first
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
except:
    print("Mixer failed to start")

def safe_load_sound(filename):
    try:
        # This will look for the file in the same folder as main.py
        import os
        path = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
        else:
            print(f"File {filename} not found!")
            return None
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None

# Load the sounds
sfx_explosion = safe_load_sound("explosion.wav")
sfx_spawn = safe_load_sound("spawn.wav")
sfx_tank = safe_load_sound("tank_fire.flac")

# ----- Constants -----
WIDTH, HEIGHT = 800, 600
FPS = 60

# Colors
MAP_PLAYER = (180, 255, 180)
MAP_AI = (255, 180, 180)
MAP_RIVER = (173, 216, 230)
SELECTED_COLOR = (0, 255, 255)

# Unit/Object Colors
DARK_GREEN = (0, 100, 0)
DARK_BLUE = (0, 0, 139)
DARK_RED = (139, 0, 0)
DARK_CRIMSON = (80, 0, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
RED = (200, 0, 0)
BLACK = (0, 0, 0)
GREY = (100, 100, 100)
WHITE = (255, 255, 255)
LIGHT_GREY = (200, 200, 200)
GOLD = (255, 215, 0)

# Fonts
FONT_LARGE = pygame.font.SysFont("Arial", 40, bold=True)
FONT_MEDIUM = pygame.font.SysFont("Arial", 28)
FONT_SMALL = pygame.font.SysFont("Arial", 16)
FONT_TINY = pygame.font.SysFont("Arial", 12, bold=True)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dots of War - Fixed V7.1")
clock = pygame.time.Clock()

# ----- Game States -----
STATE_HOME = "home"
STATE_MAP_SELECT = "map_select"
STATE_TUTORIAL = "tutorial"
STATE_GAME = "game"
STATE_END = "end"

# Multiplayer States
STATE_MP_SETUP_P1 = "mp_setup_p1"
STATE_MP_SETUP_P2 = "mp_setup_p2"
STATE_MP_ORDER_P1 = "mp_order_p1"
STATE_MP_ORDER_P2 = "mp_order_p2"
STATE_MP_RESOLVE = "mp_resolve"

state = STATE_HOME

# ----- Global Game Variables -----
game_mode = "single"
treasury_p1 = 0
treasury_p2 = 0
game_result = ""
unit_id_counter = 0
current_map_name = ""
player_spawn_zone = pygame.Rect(0, 0, 0, 0)
enemy_spawn_zone = pygame.Rect(0, 0, 0, 0)

# Stats Tracking
stats = {
    "kills": 0,
    "losses": 0,
    "money_earned": 0,
    "start_time": 0,
    "end_time": 0
}

# Turn Logic
TURN_DURATION = 300
turn_timer = 0

# Territory Map
TERRITORY_SCALE = 10
TERRITORY_W = WIDTH // TERRITORY_SCALE
TERRITORY_H = HEIGHT // TERRITORY_SCALE
territory_surface = pygame.Surface((TERRITORY_W, TERRITORY_H))

# Unit lists
player_units = []
enemy_units = []
cities = []
mountains = []
rivers = []
floating_texts = []
particles = []
screen_shake = 0

MAX_UNITS = 20
placing_phase = True
selected_units = set()

# Speeds
TROOP_SPEED = 2.5
TANK_SPEED = 4.0

# AI Logic Timers
AI_THINK_INTERVAL = 20
AI_BUY_INTERVAL = 45
ai_think_timer = 0
ai_buy_timer = 0

# TENSORFLOW CONSTANTS
GRID_SIZE = 20
GRID_W = WIDTH // GRID_SIZE
GRID_H = HEIGHT // GRID_SIZE
KERNEL = tf.reshape(tf.constant(
    [[0.05, 0.1, 0.1, 0.1, 0.05], [0.1, 0.2, 0.2, 0.2, 0.1], [0.1, 0.2, 1.0, 0.2, 0.1], [0.1, 0.2, 0.2, 0.2, 0.1],
     [0.05, 0.1, 0.1, 0.1, 0.05]], dtype=tf.float32), [5, 5, 1, 1])


class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = 255  # Alpha transparency
        self.color = color
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 8  # Fades out over time
        return self.life > 0

    def draw(self, surf):
        p_surf = pygame.Surface((self.size, self.size))
        p_surf.set_alpha(self.life)
        p_surf.fill(self.color)
        surf.blit(p_surf, (self.x, self.y))


# ----- CLASS: Floating Text -----
class FloatingText:
    def __init__(self, x, y, text, color, duration=60):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.duration = duration
        self.timer = 0
        self.alpha = 255

    def update(self):
        self.y -= 0.5
        self.timer += 1
        if self.timer > self.duration * 0.7:
            self.alpha = max(0, 255 - int(255 * (self.timer - self.duration * 0.7) / (self.duration * 0.3)))

    def draw(self, surf):
        txt_surf = FONT_TINY.render(self.text, True, self.color)
        txt_surf.set_alpha(self.alpha)
        surf.blit(txt_surf, (self.x - txt_surf.get_width() // 2, self.y))


def spawn_floating_text(x, y, text, color):
    floating_texts.append(FloatingText(x, y, text, color))


# ----- Helper Functions -----
def in_mountain(x, y):
    for m in mountains:
        if m[0] <= x <= m[2] and m[1] <= y <= m[3]: return True
    return False


def in_river(x, y):
    for r in rivers:
        if r[0] <= x <= r[2] and r[1] <= y <= r[3]: return True
    return False


def draw_text(surface, text, font, color, pos):
    textobj = font.render(text, True, color)
    surface.blit(textobj, pos)


def draw_rounded_rect(surface, rect, color, radius=10, border=0, border_color=None):
    x, y, w, h = rect
    shape_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(shape_surf, color, (0, 0, w, h), border_radius=radius)
    if border and border_color:
        pygame.draw.rect(shape_surf, border_color, (0, 0, w, h), border, border_radius=radius)
    surface.blit(shape_surf, (x, y))


# ----- Menus -----
def draw_home():
    screen.fill(LIGHT_GREY)
    title_text = FONT_LARGE.render("Dots of War", True, BLACK)
    subtitle_text = FONT_MEDIUM.render("V6.0: Tensorflow AI!!!", True, DARK_BLUE)
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 80))
    screen.blit(subtitle_text, (WIDTH // 2 - subtitle_text.get_width() // 2, 130))

    btn_w, btn_h = 240, 50
    cx = WIDTH // 2

    sp_rect = pygame.Rect(cx - btn_w // 2, 220, btn_w, btn_h)
    draw_rounded_rect(screen, sp_rect, DARK_GREEN, radius=15, border=3, border_color=BLACK)
    draw_text(screen, "Singleplayer", FONT_MEDIUM, WHITE, (sp_rect.x + 45, sp_rect.y + 10))

    mp_rect = pygame.Rect(cx - btn_w // 2, 300, btn_w, btn_h)
    draw_rounded_rect(screen, mp_rect, DARK_BLUE, radius=15, border=3, border_color=BLACK)
    draw_text(screen, "Local Multiplayer (!!!WARNING!!! !!!CURRENTLY NOT WORKING!!!)", FONT_MEDIUM, WHITE, (mp_rect.x + 20, mp_rect.y + 10))

    tut_rect = pygame.Rect(cx - btn_w // 2, 380, btn_w, btn_h)
    draw_rounded_rect(screen, tut_rect, GREY, radius=15, border=3, border_color=BLACK)
    draw_text(screen, "Tutorial", FONT_MEDIUM, WHITE, (tut_rect.x + 75, tut_rect.y + 10))

    return {'single': sp_rect, 'multi': mp_rect, 'tutorial': tut_rect}


def draw_map_select():
    screen.fill(LIGHT_GREY)
    title_text = FONT_LARGE.render("Choose Battle Map", True, BLACK)
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 40))
    btn_w, btn_h = 250, 60
    cx = WIDTH // 2
    maps = [("Classic Bridge", DARK_GREEN, 120, 'map1'), ("Twin Islands", DARK_BLUE, 200, 'map2'),
            ("Mountain Pass", GREY, 280, 'map3'), ("Crossroads", ORANGE, 360, 'map4')]
    rects = {}
    for name, color, y, key in maps:
        r = pygame.Rect(cx - btn_w // 2, y, btn_w, btn_h)
        draw_rounded_rect(screen, r, color, radius=10, border=2, border_color=BLACK)
        txt = FONT_MEDIUM.render(name, True, WHITE)
        screen.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
        rects[key] = r

    back = pygame.Rect(cx - 100, 440, 200, 50)
    draw_rounded_rect(screen, back, GREY, radius=15, border=2, border_color=BLACK)
    draw_text(screen, "Back", FONT_MEDIUM, WHITE, (back.centerx - 30, back.centery - 15))
    rects['back'] = back
    return rects


def draw_tutorial():
    screen.fill(LIGHT_GREY)
    draw_text(screen, "TUTORIAL", FONT_LARGE, BLACK, (50, 50))
    lines = [
        "Singleplayer",
        "  - Place 20 troops/tanks and conquer the AI's cities.",
        "  - AI is very hard, but beatable",
        "Multiplayer (!!!CURRENTLY NOT WORKING!!!)",
        "  - Place 20 troops/tanks and conquer the other player's cities.",
        "",
        "Controls:",
        "  - Left Click: Select / Buy Troop ($350)",
        "  - Right Click: Move / Buy Tank ($500)",
        "  - Spacebar: Start Game",
        "",
        "Press 'B' to return."
    ]
    y = 100
    for l in lines:
        draw_text(screen, l, FONT_SMALL, BLACK, (50, y))
        y += 30


# ----- Territory & Logic -----

# 1. Initialize Territory Grid
def init_territory(map_name):
    if map_name in ["classic_bridge", "mountain_pass"]:
        territory_surface.fill(MAP_AI, (0, 0, TERRITORY_W, TERRITORY_H // 2))
        territory_surface.fill(MAP_PLAYER, (0, TERRITORY_H // 2, TERRITORY_W, TERRITORY_H // 2))
    elif map_name in ["twin_islands", "crossroads"]:
        territory_surface.fill(MAP_PLAYER, (0, 0, TERRITORY_W // 2, TERRITORY_H))
        territory_surface.fill(MAP_AI, (TERRITORY_W // 2, 0, TERRITORY_W // 2, TERRITORY_H))
    if map_name == "crossroads":
        territory_surface.fill(MAP_PLAYER, (0, TERRITORY_H // 2, TERRITORY_W // 2, TERRITORY_H // 2))
        territory_surface.fill(MAP_AI, (TERRITORY_W // 2, 0, TERRITORY_W // 2, TERRITORY_H // 2))


# 2. Update Territory Grid (THE FIXED FUNCTION)
def update_territory():
    for unit in player_units:
        pygame.draw.circle(territory_surface, MAP_PLAYER,
                           (int(unit["x"] / TERRITORY_SCALE), int(unit["y"] / TERRITORY_SCALE)), 2)
    for unit in enemy_units:
        pygame.draw.circle(territory_surface, MAP_AI,
                           (int(unit["x"] / TERRITORY_SCALE), int(unit["y"] / TERRITORY_SCALE)), 2)


# 3. Check Captures
def check_city_capture():
    for city in cities:
        tx, ty = int(city['pos'][0] / TERRITORY_SCALE), int(city['pos'][1] / TERRITORY_SCALE)
        tx = max(0, min(TERRITORY_W - 1, tx))
        ty = max(0, min(TERRITORY_H - 1, ty))
        try:
            color = territory_surface.get_at((tx, ty))[:3]
            if city['owner'] == 'ai' and color == MAP_PLAYER:
                city['owner'] = 'player'
                city['color'] = YELLOW
            elif city['owner'] == 'player' and color == MAP_AI:
                city['owner'] = 'ai'
                city['color'] = ORANGE
            elif city['owner'] == 'neutral':
                if color == MAP_PLAYER:
                    city['owner'], city['color'] = 'player', YELLOW
                elif color == MAP_AI:
                    city['owner'], city['color'] = 'ai', ORANGE
        except:
            continue


def create_unit(x, y, u_type):
    global unit_id_counter
    unit_id_counter += 1
    max_hp = 150 if u_type == "tank" else 80
    return {"id": unit_id_counter, "x": x, "y": y, "tx": x, "ty": y, "type": u_type, "hp": max_hp, "max_hp": max_hp}


def init_game(map_name, mode):
    global treasury_p1, treasury_p2, player_units, enemy_units, placing_phase, selected_units, cities
    global ai_think_timer, ai_buy_timer, game_result, unit_id_counter, mountains, rivers, current_map_name
    global player_spawn_zone, enemy_spawn_zone, game_mode, state, turn_timer, floating_texts, stats

    game_mode = mode
    treasury_p1 = 10000
    treasury_p2 = 1200
    selected_units.clear()
    player_units.clear()
    enemy_units.clear()
    cities.clear()
    mountains.clear()
    rivers.clear()
    floating_texts.clear()
    ai_think_timer = 0
    ai_buy_timer = 0
    game_result = ""
    unit_id_counter = 0
    current_map_name = map_name
    turn_timer = 0

    # Reset Stats
    stats = {"kills": 0, "losses": 0, "money_earned": 500, "start_time": pygame.time.get_ticks(), "end_time": 0}

    init_territory(map_name)

    # --- Map Data ---
    if map_name == "classic_bridge":
        rivers = [[0, 280, 280, 320], [320, 280, WIDTH, 320]]
        mountains = [[100, 100, 200, 200], [WIDTH - 200, 100, WIDTH - 100, 200],
                     [100, HEIGHT - 200, 200, HEIGHT - 100], [WIDTH - 200, HEIGHT - 200, WIDTH - 100, HEIGHT - 100]]
        cities = [
            {'pos': (150, HEIGHT - 50), 'owner': 'player', 'color': YELLOW},
            {'pos': (WIDTH // 2, HEIGHT - 50), 'owner': 'player', 'color': YELLOW},
            {'pos': (WIDTH - 150, HEIGHT - 50), 'owner': 'player', 'color': YELLOW},
            {'pos': (150, 50), 'owner': 'ai', 'color': ORANGE},
            {'pos': (WIDTH // 2, 50), 'owner': 'ai', 'color': ORANGE},
            {'pos': (WIDTH - 150, 50), 'owner': 'ai', 'color': ORANGE}
        ]
        player_spawn_zone = pygame.Rect(0, HEIGHT // 2, WIDTH, HEIGHT // 2)
        enemy_spawn_zone = pygame.Rect(0, 0, WIDTH, HEIGHT // 2)
    elif map_name == "twin_islands":
        rivers = [[WIDTH // 2 - 20, 0, WIDTH // 2 + 20, HEIGHT // 2 - 30],
                  [WIDTH // 2 - 20, HEIGHT // 2 + 30, WIDTH // 2 + 20, HEIGHT]]
        mountains = [[50, 50, 150, 150], [WIDTH - 150, HEIGHT - 150, WIDTH - 50, HEIGHT - 50]]
        cities = [
            {'pos': (150, 150), 'owner': 'player', 'color': YELLOW},
            {'pos': (100, HEIGHT - 150), 'owner': 'player', 'color': YELLOW},
            {'pos': (WIDTH - 150, 150), 'owner': 'ai', 'color': ORANGE},
            {'pos': (WIDTH - 100, HEIGHT - 150), 'owner': 'ai', 'color': ORANGE},
        ]
        player_spawn_zone = pygame.Rect(0, 0, WIDTH // 2, HEIGHT)
        enemy_spawn_zone = pygame.Rect(WIDTH // 2, 0, WIDTH // 2, HEIGHT)
    elif map_name == "mountain_pass":
        mountains = [[150, 200, WIDTH - 150, HEIGHT - 200]]
        rivers = [[0, 180, WIDTH, 200], [0, HEIGHT - 200, WIDTH, HEIGHT - 180]]
        cities = [
            {'pos': (150, HEIGHT - 50), 'owner': 'player', 'color': YELLOW},
            {'pos': (WIDTH - 150, HEIGHT - 50), 'owner': 'player', 'color': YELLOW},
            {'pos': (150, 50), 'owner': 'ai', 'color': ORANGE},
            {'pos': (WIDTH - 150, 50), 'owner': 'ai', 'color': ORANGE}
        ]
        player_spawn_zone = pygame.Rect(0, HEIGHT // 2, WIDTH, HEIGHT // 2)
        enemy_spawn_zone = pygame.Rect(0, 0, WIDTH, HEIGHT // 2)
    elif map_name == "crossroads":
        rivers = [[WIDTH // 2 - 20, 0, WIDTH // 2 + 20, HEIGHT], [0, HEIGHT // 2 - 20, WIDTH, HEIGHT // 2 + 20]]
        cities = [
            {'pos': (100, HEIGHT - 100), 'owner': 'player', 'color': YELLOW},
            {'pos': (WIDTH - 100, 100), 'owner': 'ai', 'color': ORANGE},
            {'pos': (100, 100), 'owner': 'neutral', 'color': GREY},
            {'pos': (WIDTH - 100, HEIGHT - 100), 'owner': 'neutral', 'color': GREY}
        ]
        player_spawn_zone = pygame.Rect(0, HEIGHT // 2, WIDTH // 2, HEIGHT // 2)
        enemy_spawn_zone = pygame.Rect(WIDTH // 2, 0, WIDTH // 2, HEIGHT // 2)

    if game_mode == "single":
        placing_phase = True
        state = STATE_GAME
        for _ in range(20):
            spawn_unit('ai', (enemy_spawn_zone.centerx, enemy_spawn_zone.centery), "troop")
    else:
        placing_phase = True
        state = STATE_MP_SETUP_P1


def draw_game():
    global screen_shake

    # 1. Setup Shake
    render_offset = [0, 0]
    if screen_shake > 0:
        render_offset[0] = random.randint(-screen_shake, screen_shake)
        render_offset[1] = random.randint(-screen_shake, screen_shake)
        screen_shake -= 1

        # 2. Create and Fill the Canvas
    display_surf = pygame.Surface((WIDTH, HEIGHT))
    display_surf.fill(LIGHT_GREY)

    # 3. Territory Map
    scaled_map = pygame.transform.scale(territory_surface, (WIDTH, HEIGHT))
    display_surf.blit(scaled_map, (0, 0))  # FIXED: was screen.blit

    # 4. Rivers
    for r in rivers:
        # FIXED: was pygame.draw.rect(screen, ...)
        pygame.draw.rect(display_surf, MAP_RIVER, pygame.Rect(r[0], r[1], r[2] - r[0], r[3] - r[1]))

    # 5. Mountains
    for m in mountains:
        # FIXED: was pygame.draw.polygon(screen, ...)
        pygame.draw.polygon(display_surf, GREY, [(m[0], m[3]), (m[2], m[3]), ((m[0] + m[2]) // 2, m[1])])

    # 6. Cities
    for city in cities:
        # Pulse effect: grows and shrinks slightly over time
        pulse = math.sin(pygame.time.get_ticks() * 0.005) * 3

        pygame.draw.circle(display_surf, city['color'], city['pos'], 12)

        ring_color = WHITE
        if city['owner'] == 'player':
            ring_color = DARK_GREEN
        elif city['owner'] == 'ai':
            ring_color = RED

        # The radius now uses (14 + pulse)
        pygame.draw.circle(display_surf, ring_color, city['pos'], int(14 + pulse), 2)

        mx, my = pygame.mouse.get_pos()
        for c in cities:
            if math.hypot(mx - c['pos'][0], my - c['pos'][1]) < 15:
                # Draw a small tooltip box
                pygame.draw.rect(display_surf, BLACK, (mx + 10, my + 10, 80, 25))
                income_text = FONT_TINY.render(f"+$10/sec", True, GOLD)
                display_surf.blit(income_text, (mx + 15, my + 15))

    # 7. Units (Updated helper function inside draw_game)
    def draw_unit_to_surf(u, is_player):
        base_c = (DARK_GREEN if u["type"] == "troop" else DARK_BLUE) if is_player else (
            DARK_RED if u["type"] == "troop" else DARK_CRIMSON)
        if game_mode == "single" and not is_player: base_c = RED
        c = SELECTED_COLOR if u["id"] in selected_units else base_c

        # 1. Calculate the bobbing offset
        # Only bob if the unit is actually moving (velocity is not 0)
        is_moving = abs(u.get('vx', 0)) > 0.1 or abs(u.get('vy', 0)) > 0.1
        bob = math.sin(pygame.time.get_ticks() * 0.01) * 3 if is_moving else 0

        # 2. Draw the circle using the bob offset on the Y axis
        pygame.draw.circle(display_surf, c, (int(u['x']), int(u['y'] + bob)), 6)
        if u["id"] in selected_units:
            pygame.draw.circle(display_surf, WHITE, (int(u['x']), int(u['y'])), 8, 1)

    for u in player_units: draw_unit_to_surf(u, True)
    for u in enemy_units: draw_unit_to_surf(u, False)

    # 8. Particles
    for p in particles:
        p.draw(display_surf)

    # 9. UI and Text
    # Make sure your draw_text function uses display_surf inside its logic,
    # or just blit the text surfaces to display_surf here.
    if game_mode == "single":
        money_txt = FONT_MEDIUM.render(f"Treasury: ${int(treasury_p1)}", True, BLACK)
        display_surf.blit(money_txt, (10, 10))

    # 10. FINAL BLIT: Only here do we use 'screen'
    screen.blit(display_surf, (render_offset[0], render_offset[1]))

    def draw_unit(u, is_player):
        base_c = (DARK_GREEN if u["type"] == "troop" else DARK_BLUE) if is_player else (
            DARK_RED if u["type"] == "troop" else DARK_CRIMSON)
        if game_mode == "single" and not is_player: base_c = RED
        c = SELECTED_COLOR if u["id"] in selected_units else base_c
        pygame.draw.circle(screen, c, (int(u['x']), int(u['y'])), 6)
        if u["id"] in selected_units: pygame.draw.circle(screen, WHITE, (int(u['x']), int(u['y'])), 8, 1)
        if u['hp'] < u['max_hp']:
            bar_w = 14
            hp_pct = u['hp'] / u['max_hp']
            pygame.draw.rect(screen, BLACK, (u['x'] - 7, u['y'] - 10, bar_w, 3))
            col = (0, 255, 0) if hp_pct > 0.5 else (255, 0, 0)
            pygame.draw.rect(screen, col, (u['x'] - 7, u['y'] - 10, bar_w * hp_pct, 3))

    for u in player_units: draw_unit(u, True)
    for u in enemy_units: draw_unit(u, False)

    # Draw Floating Texts
    for ft in floating_texts:
        ft.draw(screen)

    if state == STATE_MP_ORDER_P1:
        for u in player_units:
            if u["id"] in selected_units: pygame.draw.line(screen, WHITE, (u['x'], u['y']), (u['tx'], u['ty']), 1)
    if state == STATE_MP_ORDER_P2:
        for u in enemy_units:
            if u["id"] in selected_units: pygame.draw.line(screen, WHITE, (u['x'], u['y']), (u['tx'], u['ty']), 1)

    if game_mode == "single":
        draw_text(screen, f"Treasury: ${int(treasury_p1)}", FONT_MEDIUM, BLACK, (10, 10))
    else:
        draw_text(screen, f"P1: ${int(treasury_p1)}", FONT_MEDIUM, DARK_GREEN, (10, 10))
        draw_text(screen, f"P2: ${int(treasury_p2)}", FONT_MEDIUM, RED, (WIDTH - 150, 10))

    msg, color = "", BLACK
    if state == STATE_GAME and placing_phase:
        msg, color = "Place Units (Space to Start)", DARK_GREEN
    elif state == STATE_MP_SETUP_P1:
        msg, color = f"P1 Setup ({MAX_UNITS - len(player_units)} left) - Space", DARK_GREEN
    elif state == STATE_MP_SETUP_P2:
        msg, color = f"P2 Setup ({MAX_UNITS - len(enemy_units)} left) - Space", RED
    elif state == STATE_MP_ORDER_P1:
        msg, color = "P1 Turn: Order Troops - Space", DARK_GREEN
    elif state == STATE_MP_ORDER_P2:
        msg, color = "P2 Turn: Order Troops - Space", RED
    elif state == STATE_MP_RESOLVE:
        msg, color = f"RESOLVING... {int(turn_timer / 60)}s", BLACK

    if msg:
        t = FONT_SMALL.render(msg, True, color)
        bg = pygame.Surface((t.get_width() + 10, t.get_height() + 10))
        bg.fill(WHITE)
        bg.set_alpha(200)
        screen.blit(bg, (WIDTH // 2 - t.get_width() // 2 - 5, HEIGHT - 45))
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT - 40))

        # Unit Counters
        draw_rounded_rect(screen, (10, 50, 120, 60), (0, 0, 0, 150))
        draw_text(screen, f"Units: {len(player_units)}/{MAX_UNITS}", FONT_TINY, WHITE, (20, 60))
        draw_text(screen, f"Enemy: {len(enemy_units)}", FONT_TINY, RED, (20, 80))


def ai_buy_units():
    global treasury_p2
    ai_cities = [c for c in cities if c['owner'] == 'ai']
    if not ai_cities: return
    if len(enemy_units) < MAX_UNITS:
        if treasury_p2 >= 350:
            target_city = random.choice(ai_cities)
            u_type = "tank" if treasury_p2 >= 600 else "troop"
            cost = 500 if u_type == "tank" else 350
            if treasury_p2 >= cost:
                treasury_p2 -= cost
                spawn_unit('ai', target_city['pos'], u_type)


def run_tensorflow_movement():
    # ... (keep your existing grid and influence map setup) ...

    for u in enemy_units:
        gx, gy = int(u['x'] // GRID_SIZE), int(u['y'] // GRID_SIZE)
        best_x, best_y, max_val = u['x'], u['y'], -999.0

        # 1. Search for best target on Influence Map (Units/Territory)
        target_found = False
        # ... (keep your existing loop for result_map) ...

        # 2. STRATEGY BUG FIX: If no immediate threat, target the nearest Player City
        if not target_found or max_val < 0.5:
            # Filter for cities the AI doesn't own
            targets = [c for c in cities if c['owner'] != 'ai']
            if targets:
                # Find the closest city and move toward it
                closest_city = min(targets, key=lambda c: math.hypot(c['pos'][0] - u['x'], c['pos'][1] - u['y']))
                u['tx'], u['ty'] = closest_city['pos'][0], closest_city['pos'][1]
            elif player_units:
                # Fallback to nearest player unit if cities are all taken
                closest = min(player_units, key=lambda p: math.hypot(p['x'] - u['x'], p['y'] - u['y']))
                u['tx'], u['ty'] = closest['x'], closest['y']
        else:
            # Use influence map result
            u['tx'], u['ty'] = best_x + random.randint(-15, 15), best_y + random.randint(-15, 15)

def spawn_unit(owner, pos, u_type):
    global treasury_p1, treasury_p2
    attempts = 50
    for _ in range(attempts):
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(30, 60)
        sx = pos[0] + math.cos(angle) * radius
        sy = pos[1] + math.sin(angle) * radius
        sx = max(10, min(WIDTH - 10, sx))
        sy = max(10, min(HEIGHT - 10, sy))
        if not in_mountain(sx, sy):
            collision = False
            for u in player_units + enemy_units:
                if math.hypot(u['x'] - sx, u['y'] - sy) < 12:
                    collision = True
                    break
            if not collision:
                u_obj = create_unit(sx, sy, u_type)
                if owner == 'player':
                    player_units.append(u_obj)
                else:
                    enemy_units.append(u_obj)
                return True
    return False


def purchase_menu(city, btn):  # Added btn parameter
    current_owner = 'player' if state == STATE_MP_ORDER_P1 or (game_mode == "single" and not placing_phase) else 'ai'
    if state == STATE_MP_ORDER_P2: current_owner = 'ai'
    if city['owner'] != current_owner: return

    global treasury_p1
    # Check button: 1 is Left Click (Troop), 3 is Right Click (Tank)
    u_type = "tank" if btn == 3 else "troop"
    cost = 500 if u_type == "tank" else 350

    if treasury_p1 >= cost:
        if spawn_unit('player', city['pos'], u_type):
            treasury_p1 -= cost
            if sfx_spawn: sfx_spawn.play()


def update_units(dt):
    global player_losses, ai_losses, ai_think_timer, ai_buy_timer, state, player_units, enemy_units, selected_units, turn_timer, stats, d

    # Update Floating Text
    for ft in floating_texts[:]:
        ft.update()
        if ft.timer > ft.duration: floating_texts.remove(ft)

    moving = False
    if game_mode == "single" and not placing_phase:
        moving = True
    elif state == STATE_MP_RESOLVE:
        moving = True

    if moving:
        if game_mode == "single":
            ai_buy_timer += 1
            if ai_buy_timer >= AI_BUY_INTERVAL:
                ai_buy_units()
                ai_buy_timer = 0
            ai_think_timer += 1
            if ai_think_timer >= AI_THINK_INTERVAL:
                run_tensorflow_movement()
                ai_think_timer = 0

        if state == STATE_MP_RESOLVE:
            turn_timer -= 1
            if turn_timer <= 0:
                state = STATE_MP_ORDER_P1
                selected_units.clear()
                for u in player_units + enemy_units: u['tx'], u['ty'] = u['x'], u['y']

        all_units = player_units + enemy_units
        for i, unit in enumerate(all_units):
            dx, dy = unit["tx"] - unit["x"], unit["ty"] - unit["y"]
            dist = math.hypot(dx, dy)
            sep_x, sep_y = 0, 0
            for other in all_units:
                if unit != other:
                    d_x, d_y = unit['x'] - other['x'], unit['y'] - other['y']
                    d = math.hypot(d_x, d_y)
                    if d < 12 and d > 0:
                        force = (12 - d) / 2
                        sep_x += (d_x / d) * force
                        sep_y += (d_y / d) * force
            if dist > 2:
                speed = TANK_SPEED if unit["type"] == "tank" else TROOP_SPEED
                if in_river(unit["x"], unit["y"]): speed *= 0.5
                move_dist = min(dist, speed)
                vx = (dx / dist) * move_dist + sep_x
                vy = (dy / dist) * move_dist + sep_y
                nx, ny = unit["x"] + vx, unit["y"] + vy
                if in_mountain(nx, ny):
                    if not in_mountain(nx, unit["y"]):
                        unit["x"] = nx
                    elif not in_mountain(unit["x"], ny):
                        unit["y"] = ny
                else:
                    unit["x"], unit["y"] = nx, ny
            else:
                unit["x"] += sep_x
                unit["y"] += sep_y

        damage_pairs = []
        for p in player_units:
            for e in enemy_units:
                if math.hypot(p['x'] - e['x'], p['y'] - e['y']) < 18:
                    damage_pairs.append((p, e))

        for p, e in damage_pairs:
            if random.random() < 0.1:
                p_dmg = 5 if e['type'] == "troop" else 8
                e_dmg = 5 if p['type'] == "troop" else 8
                p['hp'] -= p_dmg
                e['hp'] -= e_dmg
                spawn_floating_text(p['x'], p['y'], f"-{p_dmg}", RED)
                spawn_floating_text(e['x'], e['y'], f"-{e_dmg}", RED)

                # Count losses
                dead_p = [u for u in player_units if u['hp'] <= 0]
                dead_e = [u for u in enemy_units if u['hp'] <= 0]

                # Trigger VFX and Sound for dead units
                for d in (dead_p + dead_e):
                    global screen_shake
                    # This was the error line - we ensure d is the unit dictionary
                    screen_shake = 8 if d['type'] == "tank" else 4

                    # Trigger Explosion Sound
                    if sfx_explosion:
                        sfx_explosion.play()

                    # Particle effects (optional polish)
                    p_color = DARK_GREEN if d in dead_p else RED
                    if d['type'] == "tank": p_color = GREY
                    for _ in range(10):
                        particles.append(Particle(d['x'], d['y'], p_color))

                # Update stats
                stats['losses'] += len(dead_p)
                stats['kills'] += len(dead_e)

                # Remove dead units from the game lists
                player_units = [u for u in player_units if u['hp'] > 0]
                enemy_units = [u for u in enemy_units if u['hp'] > 0]

                # --- NEW LOSS & WIN LOGIC ---
                # 1. Count how many cities each side owns
                p_cities = sum(1 for c in cities if c['owner'] == 'player')
                ai_cities = sum(1 for c in cities if c['owner'] == 'ai')

                # 2. Check for Loss: You have 0 cities AND 0 units
                if p_cities == 0 and not player_units:
                    game_result = "loss"
                    state = STATE_END
                    stats['end_time'] = pygame.time.get_ticks()

                # 3. Check for Win: AI has 0 cities AND 0 units
                elif ai_cities == 0 and not enemy_units:
                    game_result = "win"
                    state = STATE_END
                    stats['end_time'] = pygame.time.get_ticks()

def game_events(event):
    global placing_phase, selected_units, state, turn_timer, treasury_p1

    # --- HANDLE MOUSE CLICKS ---
    if event.type == pygame.MOUSEBUTTONDOWN:
        mx, my = pygame.mouse.get_pos()
        for c in cities:
            if math.hypot(mx - c['pos'][0], my - c['pos'][1]) < 15:
                purchase_menu(c, event.button)  # Pass event.button here!
                return

        # 2. Setup Phases (Placement)
        # Fix: Removed the treasury cost check here so placement is free
        if state == STATE_GAME and placing_phase and player_spawn_zone.collidepoint(mx, my):
            u = "tank" if event.button == 3 else "troop"
            if len(player_units) < MAX_UNITS:
                spawn_unit("player", (mx, my), u)
                if sfx_spawn:
                    sfx_spawn.play()
            return

        if state == STATE_MP_SETUP_P1 and player_spawn_zone.collidepoint(mx, my):
            u = "tank" if event.button == 3 else "troop"
            if len(player_units) < MAX_UNITS: player_units.append(create_unit(mx, my, u))
            if sfx_spawn: sfx_spawn.play()
            return

        if state == STATE_MP_SETUP_P2 and enemy_spawn_zone.collidepoint(mx, my):
            u = "tank" if event.button == 3 else "troop"
            if len(enemy_units) < MAX_UNITS: enemy_units.append(create_unit(mx, my, u))
            if sfx_spawn: sfx_spawn.play()
            return

        # 3. Unit Selection and Movement Orders
        # We only do this if NOT in a setup phase
        if not placing_phase and state != STATE_MP_RESOLVE:
            active_units = player_units if (state == STATE_GAME or state == STATE_MP_ORDER_P1) else enemy_units

            clicked = None
            for u in active_units:
                if math.hypot(mx - u['x'], my - u['y']) < 15:
                    clicked = u
                    break

            if clicked:
                if clicked['id'] in selected_units:
                    selected_units.remove(clicked['id'])
                else:
                    selected_units.add(clicked['id'])
            elif event.button == 3 and selected_units:
                # Right click to move
                for uid in selected_units:
                    u = next((unit for unit in active_units if unit["id"] == uid), None)
                    if u:
                        u['tx'] = mx + random.randint(-15, 15)
                        u['ty'] = my + random.randint(-15, 15)
                if game_mode == "single": selected_units.clear()

    # --- HANDLE KEYPRESSES (SPACEBAR) ---
    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
        if state == STATE_GAME and placing_phase:
            placing_phase = False
            # Ensure treasury starts at a normal level when game begins
            treasury_p1 = 500
        elif state == STATE_MP_SETUP_P1:
            state = STATE_MP_SETUP_P2;
            selected_units.clear()
        elif state == STATE_MP_SETUP_P2:
            state = STATE_MP_ORDER_P1;
            selected_units.clear()
        elif state == STATE_MP_ORDER_P1:
            state = STATE_MP_ORDER_P2;
            selected_units.clear()
        elif state == STATE_MP_ORDER_P2:
            state = STATE_MP_RESOLVE;
            selected_units.clear();
            turn_timer = TURN_DURATION


def update_treasury(delta):
    global treasury_p1, treasury_p2
    p_inc_count = sum(1 for c in cities if c['owner'] == 'player')
    a_inc_count = sum(1 for c in cities if c['owner'] == 'ai')

    old_p1 = int(treasury_p1)
    treasury_p1 += (10 + p_inc_count * 20) * delta
    treasury_p2 += (15 + a_inc_count * 20) * delta

    if int(treasury_p1) > old_p1 and int(treasury_p1) % 10 == 0:
        my_cities = [c for c in cities if c['owner'] == 'player']
        if my_cities:
            c = random.choice(my_cities)
            spawn_floating_text(c['pos'][0], c['pos'][1] - 20, "+$$$", GOLD)
            stats['money_earned'] += (int(treasury_p1) - old_p1)


def draw_end_screen():
    screen.fill(BLACK)
    msg, color = "GAME OVER", WHITE

    # Check the game_result set in update_units
    if game_result == "win":
        msg, color = "VICTORY", YELLOW
    elif game_result == "loss":
        msg, color = "DEFEAT", RED  # This will show the Red Defeat text
    elif game_result == "p1_win":
        msg, color = "PLAYER 1 WINS", DARK_GREEN
    elif game_result == "p2_win":
        msg, color = "PLAYER 2 WINS", RED

    title = FONT_LARGE.render(msg, True, color)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

    # Display Stats (Same as Victory Screen)
    duration = (stats['end_time'] - stats['start_time']) // 1000
    stat_lines = [
        f"Time Played: {duration}s",
        f"Total Kills: {stats['kills']}",
        f"Units Lost: {stats['losses']}",
        f"Money Earned: ${int(stats['money_earned'])}"
    ]

    y = 180
    for line in stat_lines:
        txt = FONT_MEDIUM.render(line, True, WHITE)
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, y))
        y += 50

    # Back to Menu Button
    r = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 100, 200, 50)
    draw_rounded_rect(screen, r, GREY, radius=10, border=2, border_color=WHITE)
    draw_text(screen, "Return to Menu", FONT_MEDIUM, WHITE, (r.x + 15, r.y + 10))
    return r

# ----- Main Loop -----
def main():
    global state
    running = True
    last_time = pygame.time.get_ticks()

    while running:
        current_time = pygame.time.get_ticks()
        dt = (current_time - last_time) / 1000.0
        last_time = current_time

        if state == STATE_HOME:
            btns = draw_home()
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
                if e.type == pygame.MOUSEBUTTONDOWN:
                    mp = pygame.mouse.get_pos()
                    if btns['single'].collidepoint(mp):
                        init_game("", "single")
                        state = STATE_MAP_SELECT
                    elif btns['multi'].collidepoint(mp):
                        init_game("", "multi")
                        state = STATE_MAP_SELECT
                    elif btns['tutorial'].collidepoint(mp):
                        state = STATE_TUTORIAL
        elif state == STATE_MAP_SELECT:
            btns = draw_map_select()
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
                if e.type == pygame.MOUSEBUTTONDOWN:
                    mp = pygame.mouse.get_pos()
                    if btns['map1'].collidepoint(mp):
                        init_game("classic_bridge", game_mode)
                    elif btns['map2'].collidepoint(mp):
                        init_game("twin_islands", game_mode)
                    elif btns['map3'].collidepoint(mp):
                        init_game("mountain_pass", game_mode)
                    elif btns['map4'].collidepoint(mp):
                        init_game("crossroads", game_mode)
                    elif btns['back'].collidepoint(mp):
                        state = STATE_HOME
        elif state == STATE_TUTORIAL:
            draw_tutorial()
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
                if e.type == pygame.KEYDOWN and e.key == pygame.K_b: state = STATE_HOME
        elif state == STATE_END:
            res_btn = draw_end_screen()
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
                if e.type == pygame.MOUSEBUTTONDOWN and res_btn.collidepoint(pygame.mouse.get_pos()): state = STATE_HOME
        else:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                game_events(event)
            update_treasury(dt)
            update_territory()
            check_city_capture()
            update_units(dt)
            draw_game()
            pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
