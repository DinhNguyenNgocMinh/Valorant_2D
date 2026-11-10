"""Static Arena geometry, cached rendering, and reusable collision helpers."""

import math

import pygame as pg


GRID_SIZE = 40
WALL_COLOR = (126, 117, 128)
GRID_COLOR = (205, 205, 205)
FLOOR_COLOR = (220, 220, 220)
EDGE_STEER_RATIO = 0.7


class Arena:
    """The practice map's walls and collision queries.

    Map artwork is cached once. Dynamic gameplay objects live in ``gameplay``
    and can be passed in as extra solid rectangles when needed.
    """

    def __init__(self, size):
        self.width, self.height = size
        scale = self.width / 825
        # Measurements follow the supplied arena reference image.
        self.walls = [
            pg.Rect(0, round(144 * scale), round(473 * scale), round(17 * scale)),
            pg.Rect(round(671 * scale), round(59 * scale), round(18 * scale), round(130 * scale)),
            pg.Rect(round(228 * scale), round(265 * scale), round(18 * scale), round(130 * scale)),
            pg.Rect(round(351 * scale), round(321 * scale), round(474 * scale), round(18 * scale)),
        ]
        self.spawn_point = pg.Vector2(round(389 * scale), round(508 * scale))
        self.background = self._build_background()

    def _build_background(self):
        background = pg.Surface((self.width, self.height))
        background.fill(FLOOR_COLOR)
        for x in range(0, self.width + 1, GRID_SIZE):
            pg.draw.line(background, GRID_COLOR, (x, 0), (x, self.height), 1)
        for y in range(0, self.height + 1, GRID_SIZE):
            pg.draw.line(background, GRID_COLOR, (0, y), (self.width, y), 1)
        for wall in self.walls:
            pg.draw.rect(background, WALL_COLOR, wall)
        return background

    def draw(self, surface):
        surface.blit(self.background, (0, 0))

    def solid_walls(self, extra_walls=()):
        return (*self.walls, *extra_walls)

    def circle_hits_wall(self, center, radius, extra_walls=()):
        return any(self._circle_hits_rect(center, radius, wall) for wall in self.solid_walls(extra_walls))

    def point_hits_wall(self, point, extra_walls=()):
        return any(wall.collidepoint(point) for wall in self.solid_walls(extra_walls))

    def segment_hits_wall(self, start, end, extra_walls=()):
        return any(wall.clipline(start, end) for wall in self.solid_walls(extra_walls))

    def move_circle(self, position, movement, radius, extra_walls=()):
        """Move a circle with wall sliding plus a gentle edge-steering assist."""
        position = pg.Vector2(position)
        # Split large impulse moves (such as Jett's dash) so they cannot jump
        # across a thin wall between collision checks.
        steps = max(1, math.ceil(movement.length() / max(8, radius / 2)))
        step = movement / steps
        for _ in range(steps):
            hit_x = self._move_axis(position, "x", step.x, radius, extra_walls)
            hit_y = self._move_axis(position, "y", step.y, radius, extra_walls)
            movement_speed = step.length()
            if hit_x and movement_speed:
                self._steer_around_edge(position, hit_x, "y", radius, movement_speed, extra_walls)
            if hit_y and movement_speed:
                self._steer_around_edge(position, hit_y, "x", radius, movement_speed, extra_walls)
        return position

    def _move_axis(self, position, axis, amount, radius, extra_walls):
        if not amount:
            return None
        candidate = position.copy()
        setattr(candidate, axis, getattr(candidate, axis) + amount)
        candidate.x = max(radius, min(self.width - radius, candidate.x))
        candidate.y = max(radius, min(self.height - radius, candidate.y))
        hit_wall = next(
            (wall for wall in self.solid_walls(extra_walls) if self._circle_hits_rect(candidate, radius, wall)),
            None,
        )
        if hit_wall is None:
            position.update(candidate)
        return hit_wall

    def _steer_around_edge(self, position, wall, slide_axis, radius, movement_speed, extra_walls):
        """Slip around a barely touched wall end; deep collisions stay solid."""
        edges = ((wall.left, -1), (wall.right, 1)) if slide_axis == "x" else ((wall.top, -1), (wall.bottom, 1))
        current = getattr(position, slide_axis)
        edge, direction = min(edges, key=lambda item: abs(current - item[0]))
        overlap = radius - abs(current - edge)
        half_radius = radius / 2
        if not 0 < overlap < half_radius:
            return
        openness = 1 - overlap / half_radius
        self._move_axis(position, slide_axis, direction * movement_speed * EDGE_STEER_RATIO * openness, radius, extra_walls)

    @staticmethod
    def _circle_hits_rect(center, radius, rect):
        closest_x = max(rect.left, min(center.x, rect.right))
        closest_y = max(rect.top, min(center.y, rect.bottom))
        return (center.x - closest_x) ** 2 + (center.y - closest_y) ** 2 < radius ** 2
