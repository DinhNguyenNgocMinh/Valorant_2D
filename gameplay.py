"""Playable practice-mode systems: movement, weapons, abilities, and HUD."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

import pygame as pg

from maps.arena.arena import Arena


PLAYER_RADIUS = 29
RUN_SPEED = 220
WALK_SPEED = 105
MAX_HEALTH = 100
INK = (15, 25, 31)
PANEL = (29, 42, 47)
PANEL_LIGHT = (50, 65, 69)
WHITE = (245, 246, 240)
MUTED = (169, 182, 179)
RED = (255, 75, 88)
CYAN = (75, 204, 193)
GOLD = (255, 204, 82)
AGENT_COLORS = {
    "Brimstone": (238, 137, 65),
    "Sage": (104, 199, 132),
    "Jett": (242, 245, 244),
    "Sova": (69, 150, 230),
    "Phoenix": (240, 78, 69),
}


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    category: str
    price: int
    damage: int
    magazine: int
    rate: int
    reload_time: float
    spread: float
    pellets: int = 1
    automatic: bool = False
    speed: int = 1400
    range: int = 1050
    melee: bool = False


# Prices, magazine sizes, fire-rates, and weapon roles follow Valorant's
# familiar loadout structure; projectile handling is tailored to this 2D game.
WEAPONS = (
    WeaponSpec("Classic", "SIDEARM", 0, 26, 12, 400, 1.75, 1.5),
    WeaponSpec("Shorty", "SIDEARM", 300, 12, 2, 225, 2.2, 11, 12, False, 1050, 220),
    WeaponSpec("Frenzy", "SIDEARM", 450, 26, 13, 600, 1.5, 2.3, 1, True),
    WeaponSpec("Ghost", "SIDEARM", 500, 30, 15, 400, 1.5, 0.8),
    WeaponSpec("Sheriff", "SIDEARM", 800, 55, 6, 240, 2.25, 0.45),
    WeaponSpec("Stinger", "SMG", 1100, 27, 20, 900, 2.25, 3.8, 1, True),
    WeaponSpec("Spectre", "SMG", 1600, 26, 30, 780, 2.25, 2.4, 1, True),
    WeaponSpec("Bucky", "SHOTGUN", 850, 20, 5, 70, 2.5, 8, 15, False, 1050, 260),
    WeaponSpec("Judge", "SHOTGUN", 1850, 17, 7, 280, 2.2, 7, 12, True, 1050, 260),
    WeaponSpec("Bulldog", "RIFLE", 2050, 35, 24, 600, 2.5, 1.8, 1, True),
    WeaponSpec("Guardian", "RIFLE", 2250, 65, 12, 240, 2.5, 0.35),
    WeaponSpec("Phantom", "RIFLE", 2900, 39, 30, 660, 2.5, 1.25, 1, True),
    WeaponSpec("Vandal", "RIFLE", 2900, 40, 25, 600, 2.5, 0.25, 1, True),
    WeaponSpec("Marshal", "SNIPER", 950, 101, 5, 160, 2.5, 0.15),
    WeaponSpec("Outlaw", "SNIPER", 2400, 140, 2, 140, 2.3, 0.12),
    WeaponSpec("Operator", "SNIPER", 4700, 150, 5, 39, 3.7, 0.08),
    WeaponSpec("Ares", "MACHINE GUN", 1600, 30, 50, 600, 3.4, 3.1, 1, True),
    WeaponSpec("Odin", "MACHINE GUN", 3200, 38, 100, 720, 3.25, 3.6, 1, True),
    WeaponSpec("Tactical Knife", "MELEE", 0, 50, 1, 90, 0, 0, 1, False, 0, 52, True),
)
WEAPON_BY_NAME = {weapon.name: weapon for weapon in WEAPONS}

ABILITY_SPECS = {
    "Phoenix": (("C", "Blaze", 18), ("Q", "Curveball", 7), ("E", "Hot Hands", 8), ("X", "Run It Back", 35)),
    "Sage": (("C", "Barrier Orb", 25), ("Q", "Slow Orb", 10), ("E", "Healing Orb", 16), ("X", "Resurrection", 35)),
    "Sova": (("C", "Owl Drone", 24), ("Q", "Shock Bolt", 9), ("E", "Recon Bolt", 18), ("X", "Hunter's Fury", 35)),
    "Jett": (("C", "Cloudburst", 8), ("Q", "Updraft", 8), ("E", "Tailwind", 10), ("X", "Blade Storm", 30)),
    "Brimstone": (("C", "Incendiary", 10), ("Q", "Stim Beacon", 15), ("E", "Sky Smoke", 18), ("X", "Orbital Strike", 40)),
}


@dataclass
class Bullet:
    position: pg.Vector2
    velocity: pg.Vector2
    damage: float
    color: tuple[int, int, int]
    lifetime: float
    radius: int = 3


@dataclass
class AbilityProjectile:
    kind: str
    position: pg.Vector2
    velocity: pg.Vector2
    color: tuple[int, int, int]
    lifetime: float
    radius: int = 9
    turn_speed: float = 0


@dataclass
class Zone:
    kind: str
    position: pg.Vector2
    radius: float
    color: tuple[int, int, int]
    remaining: float
    damage_per_second: float = 0
    delay: float = 0


@dataclass
class Barrier:
    rect: pg.Rect
    remaining: float


@dataclass
class WallLine:
    start: pg.Vector2
    end: pg.Vector2
    remaining: float
    damage_per_second: float


@dataclass
class Beam:
    start: pg.Vector2
    end: pg.Vector2
    remaining: float
    damage: float


@dataclass
class Drone:
    position: pg.Vector2
    direction: pg.Vector2
    remaining: float
    pulse_remaining: float = 0


@dataclass
class DroppedWeapon:
    weapon: WeaponSpec
    position: pg.Vector2


@dataclass
class Dummy:
    position: pg.Vector2
    spawn: pg.Vector2
    health: float = 100
    respawn: float = 0

    @property
    def alive(self):
        return self.respawn <= 0

    def take_damage(self, damage):
        if not self.alive:
            return False
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.respawn = 4
        return True

    def update(self, delta_time):
        if self.respawn > 0:
            self.respawn -= delta_time
            if self.respawn <= 0:
                self.health = 100
                self.position.update(self.spawn)


@dataclass
class Player:
    agent_name: str
    color: tuple[int, int, int]
    position: pg.Vector2
    health: float = MAX_HEALTH
    cash: int = 9000
    weapon: WeaponSpec = field(default_factory=lambda: WEAPON_BY_NAME["Classic"])
    ammo: int = 12
    reserve: int = 48
    reload_remaining: float = 0
    next_shot: float = 0
    stim_remaining: float = 0
    slow_remaining: float = 0
    run_it_back_origin: pg.Vector2 | None = None
    run_it_back_remaining: float = 0
    blade_count: int = 0

    def equip(self, weapon):
        self.weapon = weapon
        self.ammo = weapon.magazine
        self.reserve = weapon.magazine * 3
        self.reload_remaining = 0


def _font(size, bold=False):
    return pg.font.SysFont("arial", size, bold=bold)


def _draw_text(surface, text, text_font, color, position, anchor="topleft"):
    image = text_font.render(text, True, color)
    rect = image.get_rect(**{anchor: position})
    surface.blit(image, rect)
    return rect


def _lighten(color, amount=0.27):
    return tuple(min(255, round(channel + (255 - channel) * amount)) for channel in color)


def _darken(color, amount=0.45):
    return tuple(round(channel * (1 - amount)) for channel in color)


def _point_segment_distance(point, start, end):
    segment = end - start
    length_squared = segment.length_squared()
    if not length_squared:
        return point.distance_to(start)
    t = max(0, min(1, (point - start).dot(segment) / length_squared))
    return point.distance_to(start + segment * t)


class GameSession:
    """Owns one resettable, single-player practice session."""

    def __init__(self, size, agent_name):
        self.width, self.height = size
        self.arena = Arena(size)
        self.player = Player(agent_name, AGENT_COLORS[agent_name], self.arena.spawn_point.copy())
        self.bullets: list[Bullet] = []
        self.projectiles: list[AbilityProjectile] = []
        self.zones: list[Zone] = []
        self.barriers: list[Barrier] = []
        self.wall_lines: list[WallLine] = []
        self.beams: list[Beam] = []
        self.drones: list[Drone] = []
        self.dropped_weapons: list[DroppedWeapon] = []
        self.dummies = [
            Dummy(pg.Vector2(140, 505), pg.Vector2(140, 505)),
            Dummy(pg.Vector2(690, 250), pg.Vector2(690, 250)),
            Dummy(pg.Vector2(890, 525), pg.Vector2(890, 525)),
            Dummy(pg.Vector2(560, 610), pg.Vector2(560, 610)),
        ]
        self.cooldowns = {key: 0.0 for key, _, _ in ABILITY_SPECS[agent_name]}
        self.target_mode: str | None = None
        self.message = "PRACTICE RANGE READY"
        self.message_remaining = 2.5
        self.shop_open = False
        self.shop_buttons: list[tuple[pg.Rect, WeaponSpec]] = []
        self.aim_direction = pg.Vector2(1, 0)
        self.time = 0.0
        self.font_small = _font(14, True)
        self.font_tiny = _font(12, True)
        self.font_medium = _font(20, True)
        self.font_large = _font(30, True)

    @property
    def solid_barriers(self):
        return tuple(barrier.rect for barrier in self.barriers if barrier.remaining > 0)

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_b:
                self.shop_open = not self.shop_open
                self.target_mode = None
                return
            if self.shop_open:
                if event.key == pg.K_ESCAPE:
                    self.shop_open = False
                return
            if event.key == pg.K_r:
                self._start_reload()
            elif event.key == pg.K_g:
                self._drop_weapon()
            elif event.key == pg.K_f:
                self._pickup_nearest_weapon()
            elif event.key in (pg.K_c, pg.K_q, pg.K_e, pg.K_x):
                self._cast_ability(pg.key.name(event.key).upper())
        elif event.type == pg.MOUSEBUTTONDOWN:
            if self.shop_open:
                self._buy_at(event.pos)
            elif self.target_mode:
                self._confirm_target(event.button, event.pos)
            elif event.button == 1:
                self._shoot()

    def cancel_target(self):
        """Cancel an ability awaiting a mouse target without leaving the map."""
        if self.target_mode:
            self.target_mode = None
            self._message("ABILITY CANCELLED")

    def update(self, delta_time):
        self.time += delta_time
        self.message_remaining = max(0, self.message_remaining - delta_time)
        self._update_aim()
        if self.shop_open:
            return
        self._update_player(delta_time)
        self._update_timers(delta_time)
        if pg.mouse.get_pressed()[0] and self.player.weapon.automatic and not self.target_mode:
            self._shoot()
        self._update_bullets(delta_time)
        self._update_projectiles(delta_time)
        self._update_zones(delta_time)
        self._update_lines(delta_time)
        self._update_beams(delta_time)
        self._update_drones(delta_time)
        self._update_dummies(delta_time)

    def _update_aim(self):
        direction = pg.Vector2(pg.mouse.get_pos()) - self.player.position
        if direction.length_squared() > 4:
            self.aim_direction = direction.normalize()

    def _update_player(self, delta_time):
        keys = pg.key.get_pressed()
        direction = pg.Vector2(
            int(keys[pg.K_d]) - int(keys[pg.K_a]),
            int(keys[pg.K_s]) - int(keys[pg.K_w]),
        )
        if not direction:
            return
        direction = direction.normalize()
        speed = WALK_SPEED if keys[pg.K_LSHIFT] or keys[pg.K_RSHIFT] else RUN_SPEED
        if self.player.stim_remaining > 0:
            speed *= 1.18
        if self.player.slow_remaining > 0:
            speed *= 0.55
        self.player.position = self.arena.move_circle(
            self.player.position,
            direction * speed * delta_time,
            PLAYER_RADIUS,
            self.solid_barriers,
        )

    def _update_timers(self, delta_time):
        for key in self.cooldowns:
            self.cooldowns[key] = max(0, self.cooldowns[key] - delta_time)
        self.player.stim_remaining = max(0, self.player.stim_remaining - delta_time)
        self.player.slow_remaining = max(0, self.player.slow_remaining - delta_time)
        if self.player.reload_remaining > 0:
            self.player.reload_remaining -= delta_time
            if self.player.reload_remaining <= 0:
                needed = self.player.weapon.magazine - self.player.ammo
                loaded = min(needed, self.player.reserve)
                self.player.ammo += loaded
                self.player.reserve -= loaded
        if self.player.run_it_back_remaining > 0:
            self.player.run_it_back_remaining -= delta_time
            if self.player.run_it_back_remaining <= 0:
                self.player.position.update(self.player.run_it_back_origin)
                self.player.health = MAX_HEALTH
                self._message("RUN IT BACK RETURNED")

    def _shoot(self):
        player = self.player
        if player.reload_remaining > 0 or self.time < player.next_shot:
            return
        if player.blade_count > 0:
            self._throw_blade()
            return
        weapon = player.weapon
        if weapon.melee:
            self._melee_attack()
            player.next_shot = self.time + 60 / weapon.rate
            return
        if player.ammo <= 0:
            self._start_reload()
            return
        player.ammo -= 1
        rate_multiplier = 1.25 if player.stim_remaining > 0 else 1
        player.next_shot = self.time + 60 / (weapon.rate * rate_multiplier)
        for _ in range(weapon.pellets):
            direction = self.aim_direction.rotate(random.uniform(-weapon.spread, weapon.spread))
            self.bullets.append(
                Bullet(
                    player.position + direction * (PLAYER_RADIUS + 5),
                    direction * weapon.speed,
                    weapon.damage,
                    GOLD if weapon.category == "SNIPER" else WHITE,
                    weapon.range / weapon.speed,
                )
            )

    def _throw_blade(self):
        self.player.blade_count -= 1
        self.player.next_shot = self.time + 0.2
        self.bullets.append(
            Bullet(
                self.player.position + self.aim_direction * (PLAYER_RADIUS + 6),
                self.aim_direction * 1800,
                50,
                (190, 245, 250),
                0.75,
                5,
            )
        )
        if not self.player.blade_count:
            self._message("BLADE STORM EMPTY")

    def _melee_attack(self):
        for dummy in self.dummies:
            if dummy.alive and dummy.position.distance_to(self.player.position) < self.player.weapon.range:
                if (dummy.position - self.player.position).normalize().dot(self.aim_direction) > 0.35:
                    dummy.take_damage(self.player.weapon.damage)
                    self._message("KNIFE HIT")
                    break

    def _start_reload(self):
        player = self.player
        if player.weapon.melee or player.reload_remaining > 0 or player.ammo >= player.weapon.magazine or not player.reserve:
            return
        player.reload_remaining = player.weapon.reload_time
        self._message("RELOADING")

    def _drop_weapon(self):
        if self.player.weapon.name == "Classic":
            self._message("CLASSIC CANNOT BE DROPPED")
            return
        self.dropped_weapons.append(DroppedWeapon(self.player.weapon, self.player.position.copy()))
        self.player.equip(WEAPON_BY_NAME["Classic"])
        self._message("WEAPON DROPPED — PRESS F TO PICK UP")

    def _pickup_nearest_weapon(self):
        nearby = [item for item in self.dropped_weapons if item.position.distance_to(self.player.position) < 58]
        if not nearby:
            self._message("NO WEAPON NEARBY")
            return
        item = min(nearby, key=lambda dropped: dropped.position.distance_to(self.player.position))
        if self.player.weapon.name != "Classic":
            self.dropped_weapons.append(DroppedWeapon(self.player.weapon, self.player.position.copy()))
        self.player.equip(item.weapon)
        self.dropped_weapons.remove(item)
        self._message(f"EQUIPPED {item.weapon.name.upper()}")

    def _update_bullets(self, delta_time):
        active = []
        for bullet in self.bullets:
            start = bullet.position.copy()
            bullet.position += bullet.velocity * delta_time
            bullet.lifetime -= delta_time
            hit = self.arena.segment_hits_wall(start, bullet.position, self.solid_barriers)
            if not hit:
                for dummy in self.dummies:
                    if dummy.alive and _point_segment_distance(dummy.position, start, bullet.position) <= 22 + bullet.radius:
                        dummy.take_damage(bullet.damage)
                        self._message(f"HIT {round(bullet.damage)}")
                        hit = True
                        break
            if bullet.lifetime > 0 and not hit:
                active.append(bullet)
        self.bullets = active

    def _update_projectiles(self, delta_time):
        active = []
        for projectile in self.projectiles:
            start = projectile.position.copy()
            projectile.velocity.rotate_ip(projectile.turn_speed * delta_time)
            projectile.position += projectile.velocity * delta_time
            projectile.lifetime -= delta_time
            hit = self.arena.segment_hits_wall(start, projectile.position, self.solid_barriers)
            if hit or projectile.lifetime <= 0:
                self._detonate(projectile)
            else:
                active.append(projectile)
        self.projectiles = active

    def _detonate(self, projectile):
        position = projectile.position
        kind = projectile.kind
        if kind == "hot_hands":
            self.zones.append(Zone("fire", position, 70, RED, 4, 36))
        elif kind == "curveball":
            self.zones.append(Zone("flash", position, 105, WHITE, 0.55))
            self._message("CURVEBALL FLASH")
        elif kind == "slow_orb":
            self.zones.append(Zone("slow", position, 85, (123, 174, 255), 5))
        elif kind == "shock_bolt":
            self.zones.append(Zone("shock", position, 80, (84, 156, 255), 0.35, 135))
        elif kind == "recon_bolt":
            self.zones.append(Zone("recon", position, 145, (74, 185, 255), 4))
        elif kind == "cloudburst":
            self.zones.append(Zone("smoke", position, 82, (210, 224, 226), 4))
        elif kind == "incendiary":
            self.zones.append(Zone("fire", position, 75, (255, 132, 51), 5, 42))

    def _update_zones(self, delta_time):
        active = []
        for zone in self.zones:
            zone.remaining -= delta_time
            if zone.delay > 0:
                zone.delay -= delta_time
                active.append(zone)
                continue
            if zone.kind in ("fire", "shock", "orbital"):
                for dummy in self.dummies:
                    if dummy.alive and dummy.position.distance_to(zone.position) <= zone.radius + 22:
                        dummy.take_damage(zone.damage_per_second * delta_time)
            if zone.kind == "slow" and self.player.position.distance_to(zone.position) < zone.radius:
                self.player.slow_remaining = max(self.player.slow_remaining, 0.12)
            if zone.kind == "stim" and self.player.position.distance_to(zone.position) < zone.radius:
                self.player.stim_remaining = max(self.player.stim_remaining, 0.12)
            if zone.remaining > 0:
                active.append(zone)
        self.zones = active

    def _update_lines(self, delta_time):
        active = []
        for line in self.wall_lines:
            line.remaining -= delta_time
            for dummy in self.dummies:
                if dummy.alive and _point_segment_distance(dummy.position, line.start, line.end) < 30:
                    dummy.take_damage(line.damage_per_second * delta_time)
            if line.remaining > 0:
                active.append(line)
        self.wall_lines = active

    def _update_beams(self, delta_time):
        active = []
        for beam in self.beams:
            beam.remaining -= delta_time
            if beam.damage:
                for dummy in self.dummies:
                    if dummy.alive and _point_segment_distance(dummy.position, beam.start, beam.end) < 28:
                        dummy.take_damage(beam.damage)
                beam.damage = 0
            if beam.remaining > 0:
                active.append(beam)
        self.beams = active

    def _update_drones(self, delta_time):
        active = []
        for drone in self.drones:
            drone.remaining -= delta_time
            drone.pulse_remaining -= delta_time
            drone.position += drone.direction * 180 * delta_time
            if drone.remaining > 0 and not self.arena.point_hits_wall(drone.position, self.solid_barriers):
                if drone.pulse_remaining <= 0:
                    for dummy in self.dummies:
                        if dummy.alive and dummy.position.distance_to(drone.position) < 125:
                            self.zones.append(Zone("recon", dummy.position.copy(), 72, (74, 185, 255), 0.35))
                    drone.pulse_remaining = 0.65
                active.append(drone)
        self.drones = active

    def _update_dummies(self, delta_time):
        for dummy in self.dummies:
            dummy.update(delta_time)

    def _cast_ability(self, key):
        if self.target_mode:
            self._message("CONFIRM OR CANCEL THE CURRENT ABILITY")
            return
        if self.cooldowns.get(key, 0) > 0:
            self._message(f"{key} COOLDOWN {self.cooldowns[key]:.1f}S")
            return
        ability = next((item for item in ABILITY_SPECS[self.player.agent_name] if item[0] == key), None)
        if ability is None:
            return
        _, name, cooldown = ability
        agent = self.player.agent_name
        if agent == "Phoenix":
            self._cast_phoenix(key, cooldown)
        elif agent == "Sage":
            self._cast_sage(key, cooldown)
        elif agent == "Sova":
            self._cast_sova(key, cooldown)
        elif agent == "Jett":
            self._cast_jett(key, cooldown)
        else:
            self._cast_brimstone(key, cooldown)
        if not self.target_mode or not self.target_mode.startswith(f"{agent}:{key}"):
            self.cooldowns[key] = cooldown
            self._message(name.upper())

    def _cast_phoenix(self, key, cooldown):
        if key == "C":
            side = self.aim_direction.rotate(90) * 75
            start = self.player.position + self.aim_direction * 36 - side
            end = self.player.position + self.aim_direction * 36 + side
            self.wall_lines.append(WallLine(start, end, 7, 24))
        elif key == "Q":
            self.target_mode = "Phoenix:Q"
            self._message("CURVEBALL: LMB LEFT  |  RMB RIGHT")
        elif key == "E":
            self._launch("hot_hands", RED, 360, 0.8)
        elif key == "X":
            self.player.run_it_back_origin = self.player.position.copy()
            self.player.run_it_back_remaining = 8

    def _cast_sage(self, key, cooldown):
        if key == "C":
            center = self.player.position + self.aim_direction * 80
            horizontal = abs(self.aim_direction.x) > abs(self.aim_direction.y)
            rect = pg.Rect(0, 0, 28 if horizontal else 150, 150 if horizontal else 28)
            rect.center = (round(center.x), round(center.y))
            self.barriers.append(Barrier(rect, 10))
        elif key == "Q":
            self._launch("slow_orb", (123, 174, 255), 400, 1.0)
        elif key == "E":
            self.player.health = min(MAX_HEALTH, self.player.health + 45)
            self.zones.append(Zone("heal", self.player.position.copy(), 46, (111, 230, 165), 1.1))
        elif key == "X":
            self.target_mode = "Sage:X"
            self._message("RESURRECTION: CLICK A DOWNED TRAINING BOT")

    def _cast_sova(self, key, cooldown):
        if key == "C":
            self.drones.append(Drone(self.player.position + self.aim_direction * 38, self.aim_direction.copy(), 5))
        elif key == "Q":
            self._launch("shock_bolt", (84, 156, 255), 540, 1.1)
        elif key == "E":
            self._launch("recon_bolt", (74, 185, 255), 430, 1.3)
        elif key == "X":
            self.target_mode = "Sova:X:3"
            self._message("HUNTER'S FURY: CLICK TO FIRE 3 BEAMS")

    def _cast_jett(self, key, cooldown):
        if key == "C":
            self._launch("cloudburst", (210, 224, 226), 420, 0.7)
        elif key == "Q":
            self._dash(120)
        elif key == "E":
            self._dash(235)
        elif key == "X":
            self.player.blade_count = 5

    def _cast_brimstone(self, key, cooldown):
        if key == "C":
            self._launch("incendiary", (255, 132, 51), 430, 0.95)
        elif key == "Q":
            self.zones.append(Zone("stim", self.player.position.copy(), 85, CYAN, 8))
        elif key == "E":
            self.target_mode = "Brimstone:E"
            self._message("SKY SMOKE: CLICK A TARGET")
        elif key == "X":
            self.target_mode = "Brimstone:X"
            self._message("ORBITAL STRIKE: CLICK A TARGET")

    def _launch(self, kind, color, speed, lifetime):
        self.projectiles.append(
            AbilityProjectile(kind, self.player.position + self.aim_direction * 34, self.aim_direction * speed, color, lifetime)
        )

    def _dash(self, distance):
        self.player.position = self.arena.move_circle(
            self.player.position,
            self.aim_direction * distance,
            PLAYER_RADIUS,
            self.solid_barriers,
        )

    def _confirm_target(self, button, position):
        target = pg.Vector2(position)
        mode = self.target_mode
        if mode == "Phoenix:Q":
            side = -1 if button == 1 else 1
            direction = self.aim_direction.rotate(75 * side)
            self.projectiles.append(
                AbilityProjectile("curveball", self.player.position + direction * 34, direction * 370, GOLD, 0.78, turn_speed=-side * 155)
            )
            self.cooldowns["Q"] = 7
        elif mode == "Sage:X":
            downed = [dummy for dummy in self.dummies if not dummy.alive and dummy.position.distance_to(target) < 65]
            if downed:
                dummy = min(downed, key=lambda item: item.position.distance_to(target))
                dummy.respawn = 0
                dummy.health = 100
                self.cooldowns["X"] = 35
                self._message("TRAINING BOT RESURRECTED")
            else:
                self._message("NO DOWNED BOT AT TARGET")
                return
        elif mode.startswith("Sova:X:"):
            direction = target - self.player.position
            if not direction.length_squared():
                return
            direction.normalize_ip()
            self.beams.append(Beam(self.player.position.copy(), self.player.position + direction * 1100, 0.18, 120))
            shots = int(mode.rsplit(":", 1)[1]) - 1
            if shots:
                self.target_mode = f"Sova:X:{shots}"
                self._message(f"HUNTER'S FURY: {shots} BEAMS LEFT")
                return
            self.cooldowns["X"] = 35
        elif mode == "Brimstone:E":
            self.zones.append(Zone("smoke", target, 95, (154, 166, 178), 6))
            self.cooldowns["E"] = 18
        elif mode == "Brimstone:X":
            self.zones.append(Zone("orbital", target, 105, (255, 91, 64), 3.6, 95, delay=1.2))
            self.cooldowns["X"] = 40
        else:
            return
        self.target_mode = None

    def _buy_at(self, position):
        for rect, weapon in self.shop_buttons:
            if rect.collidepoint(position):
                if self.player.cash < weapon.price:
                    self._message("NOT ENOUGH CREDITS")
                else:
                    self.player.cash -= weapon.price
                    self.player.equip(weapon)
                    self._message(f"EQUIPPED {weapon.name.upper()}")
                return

    def _message(self, text):
        self.message = text
        self.message_remaining = 1.6

    def draw(self, surface):
        self.arena.draw(surface)
        self._draw_world(surface)
        self._draw_player(surface)
        self._draw_hud(surface)
        if self.shop_open:
            self._draw_shop(surface)

    def _draw_world(self, surface):
        for zone in self.zones:
            if zone.delay > 0:
                color = GOLD
            elif zone.kind == "smoke":
                color = zone.color
            else:
                color = zone.color
            width = 3 if zone.kind not in ("smoke", "flash") else 0
            pg.draw.circle(surface, color, (round(zone.position.x), round(zone.position.y)), round(zone.radius), width)
            if zone.kind == "recon":
                pg.draw.circle(surface, WHITE, (round(zone.position.x), round(zone.position.y)), 8)
        for barrier in self.barriers:
            pg.draw.rect(surface, (155, 221, 239), barrier.rect, border_radius=4)
            pg.draw.rect(surface, WHITE, barrier.rect, 2, border_radius=4)
        for line in self.wall_lines:
            pg.draw.line(surface, (112, 25, 28), line.start, line.end, 14)
            pg.draw.line(surface, RED, line.start, line.end, 7)
            pg.draw.line(surface, GOLD, line.start, line.end, 2)
        for beam in self.beams:
            pg.draw.line(surface, (43, 92, 162), beam.start, beam.end, 18)
            pg.draw.line(surface, (90, 193, 255), beam.start, beam.end, 8)
            pg.draw.line(surface, WHITE, beam.start, beam.end, 2)
        for drone in self.drones:
            center = (round(drone.position.x), round(drone.position.y))
            pg.draw.circle(surface, (80, 160, 220), center, 14)
            pg.draw.circle(surface, WHITE, center, 5)
        for dropped in self.dropped_weapons:
            point = (round(dropped.position.x), round(dropped.position.y))
            pg.draw.rect(surface, GOLD, (point[0] - 13, point[1] - 5, 26, 10), border_radius=2)
            _draw_text(surface, dropped.weapon.name.upper(), self.font_tiny, INK, (point[0], point[1] + 12), "midtop")
        for bullet in self.bullets:
            pg.draw.circle(surface, bullet.color, (round(bullet.position.x), round(bullet.position.y)), bullet.radius)
        for dummy in self.dummies:
            self._draw_dummy(surface, dummy)

    def _draw_dummy(self, surface, dummy):
        center = (round(dummy.position.x), round(dummy.position.y))
        if not dummy.alive:
            pg.draw.circle(surface, (82, 82, 82), center, 18, 2)
            _draw_text(surface, f"RESPAWN {max(0, dummy.respawn):.1f}", self.font_tiny, WHITE, (center[0], center[1] - 34), "midbottom")
            return
        pg.draw.circle(surface, (80, 80, 88), center, 24)
        pg.draw.circle(surface, (237, 105, 80), center, 17)
        pg.draw.circle(surface, INK, center, 7)
        health_rect = pg.Rect(center[0] - 26, center[1] - 38, 52, 6)
        pg.draw.rect(surface, INK, health_rect)
        pg.draw.rect(surface, (100, 225, 125), (health_rect.x + 1, health_rect.y + 1, round(50 * dummy.health / 100), 4))

    def _draw_player(self, surface):
        center = (round(self.player.position.x), round(self.player.position.y))
        shadow = (center[0] + 3, center[1] + 7)
        pg.draw.ellipse(surface, (55, 55, 55), (shadow[0] - 25, shadow[1] - 11, 50, 20))
        pg.draw.circle(surface, _darken(self.player.color), center, PLAYER_RADIUS)
        front = self.player.position + self.aim_direction * 6
        pg.draw.circle(surface, _lighten(self.player.color), (round(front.x), round(front.y)), PLAYER_RADIUS - 5)
        pg.draw.circle(surface, WHITE, center, PLAYER_RADIUS, 2)
        aim_end = self.player.position + self.aim_direction * 42
        pg.draw.line(surface, INK, center, aim_end, 5)
        pg.draw.line(surface, WHITE, center, aim_end, 2)
        if self.player.run_it_back_remaining > 0:
            pg.draw.circle(surface, RED, center, PLAYER_RADIUS + 6, 2)

    def _draw_hud(self, surface):
        left = pg.Rect(18, 18, 302, 61)
        pg.draw.rect(surface, INK, left, border_radius=4)
        _draw_text(surface, self.player.agent_name.upper(), self.font_medium, WHITE, (left.x + 13, left.y + 9))
        _draw_text(surface, f"HP {round(self.player.health)}", self.font_small, (111, 230, 165), (left.x + 13, left.y + 37))
        _draw_text(surface, f"¢ {self.player.cash}", self.font_small, GOLD, (left.right - 13, left.y + 37), "topright")
        _draw_text(surface, "B  BUY    G  DROP    F  PICK UP    R  RELOAD", self.font_tiny, WHITE, (18, 88))
        weapon_panel = pg.Rect(self.width - 238, self.height - 82, 220, 64)
        pg.draw.rect(surface, INK, weapon_panel, border_radius=4)
        _draw_text(surface, self.player.weapon.name.upper(), self.font_medium, WHITE, (weapon_panel.x + 13, weapon_panel.y + 9))
        ammo = "—" if self.player.weapon.melee else f"{self.player.ammo} / {self.player.reserve}"
        _draw_text(surface, ammo, self.font_medium, GOLD, (weapon_panel.right - 13, weapon_panel.y + 31), "topright")
        if self.player.reload_remaining > 0:
            _draw_text(surface, f"RELOAD {self.player.reload_remaining:.1f}", self.font_tiny, RED, (weapon_panel.x + 13, weapon_panel.y + 39))
        self._draw_ability_bar(surface)
        if self.target_mode:
            pg.draw.rect(surface, INK, (205, 112, 590, 34), border_radius=3)
            _draw_text(surface, self.message, self.font_small, GOLD, (500, 129), "center")
        elif self.message_remaining > 0:
            _draw_text(surface, self.message, self.font_small, INK, (self.width // 2, 22), "midtop")

    def _draw_ability_bar(self, surface):
        specs = ABILITY_SPECS[self.player.agent_name]
        start_x = 18
        y = self.height - 78
        for index, (key, name, _) in enumerate(specs):
            rect = pg.Rect(start_x + index * 142, y, 132, 56)
            cooldown = self.cooldowns[key]
            pg.draw.rect(surface, INK if cooldown <= 0 else PANEL_LIGHT, rect, border_radius=3)
            pg.draw.rect(surface, self.player.color if cooldown <= 0 else (90, 99, 100), rect, 2, border_radius=3)
            label = f"{key}  {name.upper()}"
            _draw_text(surface, label, self.font_tiny, WHITE, (rect.x + 8, rect.y + 9))
            value = "READY" if cooldown <= 0 else f"{cooldown:.1f}s"
            _draw_text(surface, value, self.font_small, CYAN if cooldown <= 0 else MUTED, (rect.x + 8, rect.y + 29))
        if self.player.blade_count:
            _draw_text(surface, f"KNIVES: {self.player.blade_count}", self.font_small, GOLD, (590, self.height - 100))

    def _draw_shop(self, surface):
        overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
        overlay.fill((5, 10, 14, 220))
        surface.blit(overlay, (0, 0))
        _draw_text(surface, "BUY MENU", self.font_large, WHITE, (32, 26))
        _draw_text(surface, f"CREDITS  {self.player.cash}", self.font_medium, GOLD, (self.width - 32, 33), "topright")
        _draw_text(surface, "CLICK A WEAPON TO EQUIP  •  B OR ESC TO CLOSE", self.font_small, MUTED, (32, 64))
        categories = ("SIDEARM", "SMG", "SHOTGUN", "RIFLE", "SNIPER", "MACHINE GUN", "MELEE")
        grouped = {category: [weapon for weapon in WEAPONS if weapon.category == category] for category in categories}
        self.shop_buttons = []
        card_width, card_height = 218, 58
        for column, category in enumerate(categories):
            x = 25 + (column % 4) * 243
            y = 112 if column < 4 else 465
            _draw_text(surface, category, self.font_small, CYAN, (x, y))
            for index, weapon in enumerate(grouped[category]):
                rect = pg.Rect(x, y + 26 + index * (card_height + 5), card_width, card_height)
                affordable = self.player.cash >= weapon.price
                pg.draw.rect(surface, PANEL if affordable else (45, 47, 49), rect, border_radius=3)
                pg.draw.rect(surface, self.player.color if weapon.name == self.player.weapon.name else PANEL_LIGHT, rect, 2, border_radius=3)
                _draw_text(surface, weapon.name.upper(), self.font_small, WHITE if affordable else MUTED, (rect.x + 9, rect.y + 8))
                _draw_text(surface, f"{weapon.damage} DMG  •  {weapon.rate} RPM", self.font_tiny, MUTED, (rect.x + 9, rect.y + 29))
                price = "OWNED" if weapon.name == self.player.weapon.name else f"¢ {weapon.price}"
                _draw_text(surface, price, self.font_small, GOLD if affordable else RED, (rect.right - 9, rect.y + 9), "topright")
                self.shop_buttons.append((rect, weapon))
