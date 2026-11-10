"""Valorant-inspired 2D practice game entry point."""

from pathlib import Path

import pygame as pg

from gameplay import ABILITY_SPECS, AGENT_COLORS, GameSession


WIDTH, HEIGHT = 1000, 700
ROOT = Path(__file__).parent

INK = (15, 25, 31)
PAPER = (235, 232, 224)
MUTED = (129, 139, 141)
PANEL = (29, 42, 47)
PANEL_LIGHT = (43, 57, 61)
RED = (255, 70, 85)
CYAN = (75, 204, 193)
WHITE = (248, 247, 241)
GRID = (221, 219, 211)
AGENT_DATA = (
    ("Phoenix", "DUELIST", "images.jpg"),
    ("Sage", "SENTINEL", "images.jpg"),
    ("Sova", "INITIATOR", "images.jpg"),
    ("Jett", "DUELIST", "image.jpg"),
    ("Brimstone", "CONTROLLER", "images.jpg"),
)


class Agent:
    def __init__(self, name, role, portrait_file):
        self.name = name
        self.role = role
        image_path = ROOT / "agents" / name / portrait_file
        portrait = pg.image.load(str(image_path)).convert()
        self.portrait = pg.transform.smoothscale(portrait, (142, 142))


def font(size, bold=False):
    return pg.font.SysFont("arial", size, bold=bold)


def draw_text(surface, text, text_font, color, position, anchor="topleft"):
    rendered = text_font.render(text, True, color)
    rect = rendered.get_rect(**{anchor: position})
    surface.blit(rendered, rect)
    return rect


def build_menu_background():
    """Cache the shared tactical-grid background used by the selection screens."""
    background = pg.Surface((WIDTH, HEIGHT))
    background.fill(PAPER)
    for x in range(0, WIDTH, 40):
        pg.draw.line(background, GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 40):
        pg.draw.line(background, GRID, (0, y), (WIDTH, y), 1)
    pg.draw.rect(background, INK, (0, 0, WIDTH, 92))
    pg.draw.polygon(background, RED, [(0, 92), (230, 92), (195, 105), (0, 105)])
    return background


def draw_header(surface, title, eyebrow, right_text):
    draw_text(surface, eyebrow, SMALL, (187, 203, 200), (32, 23))
    draw_text(surface, title, TITLE, WHITE, (32, 43))
    draw_text(surface, right_text, SMALL, WHITE, (WIDTH - 32, 34), "topright")


def draw_button(surface, rect, label, color, hovered=False):
    fill = color if not hovered else tuple(min(255, component + 18) for component in color)
    pg.draw.rect(surface, fill, rect, border_radius=2)
    text_color = WHITE if color == PANEL_LIGHT else INK
    draw_text(surface, label, SMALL, text_color, rect.center, "center")


def draw_agent_card(surface, agent, rect, selected, hovered):
    if selected:
        pg.draw.rect(surface, (177, 45, 56), rect.move(0, 6), border_radius=4)
        pg.draw.rect(surface, RED, rect, border_radius=4)
    else:
        pg.draw.rect(surface, PANEL, rect, border_radius=4)
        pg.draw.rect(surface, CYAN if hovered else PANEL_LIGHT, rect, 2, border_radius=4)
    portrait_area = pg.Rect(rect.x + 8, rect.y + 8, 142, 142)
    surface.blit(agent.portrait, portrait_area)
    surface.blit(SELECTED_OVERLAY if selected else DIM_OVERLAY, portrait_area)
    pg.draw.line(surface, RED if selected else CYAN, (rect.x + 10, rect.y + 152), (rect.right - 10, rect.y + 152), 3)
    draw_text(surface, agent.name.upper(), NAME, WHITE, (rect.centerx, rect.y + 169), "midtop")
    draw_text(surface, agent.role, SMALL, (211, 219, 215), (rect.centerx, rect.y + 198), "midtop")


def draw_agent_details(surface, agent, mouse_position):
    box = pg.Rect(94, 446, WIDTH - 188, 180)
    pg.draw.rect(surface, PANEL, box, border_radius=5)
    pg.draw.rect(surface, PANEL_LIGHT, box, 1, border_radius=5)
    draw_text(surface, agent.role, SMALL, CYAN, (box.x + 28, box.y + 25))
    draw_text(surface, agent.name.upper(), AGENT_TITLE, WHITE, (box.x + 27, box.y + 43))
    draw_text(surface, "ABILITY LOADOUT", SMALL, MUTED, (box.x + 285, box.y + 27))
    for index, (key, ability, cooldown) in enumerate(ABILITY_SPECS[agent.name]):
        x = box.x + 285 + (index % 2) * 190
        y = box.y + 57 + (index // 2) * 42
        pg.draw.rect(surface, AGENT_COLORS[agent.name], (x, y + 3, 7, 18))
        draw_text(surface, f"{key}  {ability.upper()}", SMALL, WHITE, (x + 16, y + 1))
        draw_text(surface, f"{cooldown}s", TINY, MUTED, (x + 16, y + 20))
    draw_button(surface, LOCK_BUTTON, "LOCK IN  [ENTER]", RED, LOCK_BUTTON.collidepoint(mouse_position))


def draw_agent_select(surface, selected_index, mouse_position):
    surface.blit(MENU_BACKGROUND, (0, 0))
    draw_header(surface, "SELECT AGENT", "2D // PRACTICE RANGE", "5 AGENTS AVAILABLE")
    draw_text(surface, "CLICK A CARD OR USE  A / D  TO CHANGE AGENT", SMALL, MUTED, (WIDTH // 2, 126), "center")
    for index, (agent, rect) in enumerate(zip(AGENTS, AGENT_CARDS)):
        draw_agent_card(surface, agent, rect, index == selected_index, rect.collidepoint(mouse_position))
    draw_agent_details(surface, AGENTS[selected_index], mouse_position)
    draw_text(surface, "ESC  EXIT", SMALL, MUTED, (32, HEIGHT - 27))


def draw_map_select(surface, selected_agent, mouse_position):
    surface.blit(MENU_BACKGROUND, (0, 0))
    draw_header(surface, "SELECT MAP", "2D // PRACTICE RANGE", f"AGENT: {selected_agent.name.upper()}")
    draw_button(surface, CHANGE_AGENT_BUTTON, "CHANGE AGENT", PANEL_LIGHT, CHANGE_AGENT_BUTTON.collidepoint(mouse_position))
    hovered = MAP_CARD.collidepoint(mouse_position) or MAP_LAUNCH_BUTTON.collidepoint(mouse_position)
    pg.draw.rect(surface, (177, 45, 56), MAP_CARD.move(0, 7), border_radius=5)
    pg.draw.rect(surface, PANEL, MAP_CARD, border_radius=5)
    pg.draw.rect(surface, RED if hovered else PANEL_LIGHT, MAP_CARD, 3, border_radius=5)
    surface.blit(MAP_THUMBNAIL, MAP_THUMBNAIL_RECT)
    draw_text(surface, "ARENA", AGENT_TITLE, WHITE, (MAP_CARD.x + 22, MAP_CARD.bottom - 70))
    draw_text(surface, "PRACTICE MAP  //  WEAPONS + ABILITIES", SMALL, (207, 216, 212), (MAP_CARD.x + 22, MAP_CARD.bottom - 38))
    draw_button(surface, MAP_LAUNCH_BUTTON, "DEPLOY  [ENTER]", RED, hovered)
    draw_text(surface, "ONE MAP AVAILABLE", SMALL, MUTED, (WIDTH // 2, 132), "center")


def draw_game(surface, session, mouse_position):
    session.draw(surface)
    draw_button(surface, ARENA_EXIT_BUTTON, "MAP SELECT  [ESC]", RED, ARENA_EXIT_BUTTON.collidepoint(mouse_position))


pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("Valorant 2D Practice Range")
clock = pg.time.Clock()

TITLE = font(40, True)
NAME = font(22, True)
AGENT_TITLE = font(32, True)
SMALL = font(14, True)
TINY = font(12, True)
MENU_BACKGROUND = build_menu_background()
DIM_OVERLAY = pg.Surface((142, 142), pg.SRCALPHA)
DIM_OVERLAY.fill((7, 12, 16, 80))
SELECTED_OVERLAY = pg.Surface((142, 142), pg.SRCALPHA)
SELECTED_OVERLAY.fill((7, 12, 16, 35))

AGENTS = [Agent(*data) for data in AGENT_DATA]
CARD_SIZE = (158, 224)
CARD_GAP = 14
cards_width = len(AGENTS) * CARD_SIZE[0] + (len(AGENTS) - 1) * CARD_GAP
card_left = (WIDTH - cards_width) // 2
AGENT_CARDS = [
    pg.Rect(card_left + index * (CARD_SIZE[0] + CARD_GAP), 165, *CARD_SIZE)
    for index in range(len(AGENTS))
]
LOCK_BUTTON = pg.Rect(722, 579, 156, 30)
CHANGE_AGENT_BUTTON = pg.Rect(790, 24, 178, 34)
MAP_CARD = pg.Rect(238, 160, 524, 430)
MAP_THUMBNAIL_RECT = pg.Rect(258, 180, 484, 342)
MAP_LAUNCH_BUTTON = pg.Rect(548, 536, 184, 32)
ARENA_EXIT_BUTTON = pg.Rect(790, 20, 178, 34)
thumbnail = pg.image.load(str(ROOT / "maps" / "arena" / "thumbnail.png")).convert()
MAP_THUMBNAIL = pg.transform.smoothscale(thumbnail, MAP_THUMBNAIL_RECT.size)

state = "agent_select"
selected_index = 0
session = None
running = True

while running:
    delta_time = min(clock.tick(60) / 1000, 0.05)
    mouse_position = pg.mouse.get_pos()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif state == "agent_select":
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for index, card in enumerate(AGENT_CARDS):
                    if card.collidepoint(event.pos):
                        selected_index = index
                        break
                if LOCK_BUTTON.collidepoint(event.pos):
                    state = "map_select"
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_LEFT, pg.K_a):
                    selected_index = (selected_index - 1) % len(AGENTS)
                elif event.key in (pg.K_RIGHT, pg.K_d):
                    selected_index = (selected_index + 1) % len(AGENTS)
                elif event.key in (pg.K_RETURN, pg.K_SPACE):
                    state = "map_select"
                elif event.key == pg.K_ESCAPE:
                    running = False
        elif state == "map_select":
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if CHANGE_AGENT_BUTTON.collidepoint(event.pos):
                    state = "agent_select"
                elif MAP_CARD.collidepoint(event.pos) or MAP_LAUNCH_BUTTON.collidepoint(event.pos):
                    session = GameSession((WIDTH, HEIGHT), AGENTS[selected_index].name)
                    state = "arena"
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_RETURN, pg.K_SPACE):
                    session = GameSession((WIDTH, HEIGHT), AGENTS[selected_index].name)
                    state = "arena"
                elif event.key == pg.K_ESCAPE:
                    state = "agent_select"
        else:
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                if session.shop_open:
                    session.handle_event(event)
                elif session.target_mode:
                    session.cancel_target()
                else:
                    state = "map_select"
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and ARENA_EXIT_BUTTON.collidepoint(event.pos):
                state = "map_select"
            else:
                session.handle_event(event)

    if state == "agent_select":
        draw_agent_select(screen, selected_index, mouse_position)
    elif state == "map_select":
        draw_map_select(screen, AGENTS[selected_index], mouse_position)
    else:
        session.update(delta_time)
        draw_game(screen, session, mouse_position)
    pg.display.flip()

pg.quit()
