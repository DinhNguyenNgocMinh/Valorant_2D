# Valorant 2D Practice Range

A local, Pygame-based 2D practice prototype with agent selection, a map-selection screen, tactical movement, abilities, a weapon shop, and target bots. It uses only the assets included in this repository and is not affiliated with Riot Games.

## Run

```powershell
pip install pygame
python main.py
```

Python 3.10 or newer is recommended.

## Game flow

1. Select an agent, then lock it in.
2. Choose the Arena map and deploy.
3. Practice movement, guns, and all four abilities against the training bots.

## Controls

| Action | Control |
| --- | --- |
| Move | `W` `A` `S` `D` |
| Walk | Hold `Shift` while moving |
| Aim / fire | Aim with mouse; left-click to fire |
| Reload | `R` |
| Buy menu | `B` (click a weapon to buy and equip it) |
| Drop / pick up weapon | `G` / `F` |
| Abilities | `C`, `Q`, `E`, `X` |
| Back / cancel targeting | `Esc` |

Phoenix's Curveball uses the canonical input: press `Q`, then left-click for a left curve or right-click for a right curve. Targeted abilities display their exact follow-up instruction in the HUD.

## Agents and abilities

| Agent | `C` | `Q` | `E` | `X` |
| --- | --- | --- | --- | --- |
| Phoenix | Blaze fire wall | Curveball flash | Hot Hands fire zone | Run It Back return point |
| Sage | Barrier Orb | Slow Orb | Healing Orb | Resurrection for a downed training bot |
| Sova | Owl Drone recon | Shock Bolt | Recon Bolt | Hunter's Fury (3 beams) |
| Jett | Cloudburst smoke | Updraft movement burst | Tailwind dash | Blade Storm (5 knives) |
| Brimstone | Incendiary | Stim Beacon | Sky Smoke target | Orbital Strike target |

Each ability has a visible cooldown. Walls, smoke, zones, dashes, beams, drones, flash effects, healing, slows, stim boosts, and bot damage are all simulated in the practice map.

## Weapons

Press `B` in the Arena to access all weapon categories:

- Sidearms: Classic, Shorty, Frenzy, Ghost, Sheriff
- SMGs: Stinger, Spectre
- Shotguns: Bucky, Judge
- Rifles: Bulldog, Guardian, Phantom, Vandal
- Snipers: Marshal, Outlaw, Operator
- Machine guns: Ares, Odin
- Melee: Tactical Knife

Weapons have individual price, magazine, reload duration, rate of fire, damage, spread, pellet count, projectile speed, and range. Automatic weapons can be held; semi-auto weapons require clicks. Shotguns fire multiple pellets, and bullets follow the mouse aim direction.

## Movement and collision

- The round player marker is always the same size; color identifies the selected agent.
- Directional shading makes the back of the character darker and the facing side lighter.
- Grey Arena walls and Sage barriers are solid for both movement and bullets.
- Movement is frame-rate independent. Run speed is 220 px/s; walking is 105 px/s.
- A light hit on a wall's edge (less than half the player's radius) provides a proportional steering assist toward the open side. A deeper impact remains blocked.

## Project layout

```text
main.py                  # Agent/map screens and application flow
gameplay.py              # Practice session, weapons, abilities, bots, HUD, shop
maps/arena/arena.py      # Cached map grid, static walls, and collision helpers
maps/arena/thumbnail.png # Map-selection image
agents/<agent>/          # Existing agent portrait assets
web view/                # Standalone browser implementation (open index.html)
```

## Notes

This is a single-player local prototype. Hosting source on GitHub does not by itself add shared multiplayer; that would require an authoritative networking server and client synchronization.
