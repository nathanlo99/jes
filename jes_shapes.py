import math
import copy
import time
import numpy as np
import pygame

from utils import lerp, species_to_color, species_to_name


def draw_text_rect(surface, transform, coor, color1, color2, text, font):
    tx, ty, s = transform
    x1, y1, x2, y2 = coor
    draw_rect(surface, transform, coor, color1)
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    text_x = center_x * s + tx
    text_y = center_y * s + ty
    center_text(surface, text, text_x, text_y, color2, font)


def draw_rect(surface, transform, coor, color):
    surface_width = surface.get_width()
    surface_height = surface.get_height()
    if coor is None:
        x1 = y1 = x2 = y2 = None
    else:
        x1, y1, x2, y2 = coor
    tx, ty, s = transform
    ax1 = 0 if x1 is None else tx + x1 * s
    ay1 = 0 if y1 is None else ty + y1 * s
    ax2 = surface_width if x2 is None else tx + x2 * s
    ay2 = surface_height if y2 is None else ty + y2 * s
    if ax1 < surface_width and ax2 > 0 and ay1 < surface_height and ay2 > 0:
        pygame.draw.rect(surface, color, (ax1, ay1, ax2 - ax1, ay2 - ay1))


def draw_ring_light(w, h, thickness):
    s = math.sin(time.monotonic() * (2 * math.pi) * 3) * 0.5 + 0.5
    bright = (255 * s, 255 * s, 0, 200)
    ring_light = pygame.Surface((w, h), pygame.SRCALPHA, 32)
    pygame.draw.rect(ring_light, bright, (0, 0, w, thickness))
    pygame.draw.rect(ring_light, bright, (0, h - thickness, w, thickness))
    pygame.draw.rect(ring_light, bright, (0, 0, thickness, h))
    pygame.draw.rect(ring_light, bright, (w - thickness, 0, thickness, h))
    return ring_light


def draw_x(icon_coor, I, color, screen):
    for part_num in range(2):
        i1 = I * 0.02
        i2 = I * 0.06 + 3
        points = [[i1, i2], [i2, i1], [I - i1, I - i2], [I - i2, I - i1]]
        for point in points:
            if part_num == 1:
                point[0] = I - point[0]
            point[0] += icon_coor[0]
            point[1] += icon_coor[1]
        pygame.draw.polygon(screen, color, points)


def center_text(screen, stri, x, y, color, font):
    align_text(screen, stri, x, y, color, font, 0.5, None)


def right_text(screen, stri, x, y, color, font):
    align_text(screen, stri, x, y, color, font, 1.0, None)


def expand(coor, amount):
    return [
        coor[0] - amount,
        coor[1] - amount,
        coor[2] + amount * 2,
        coor[3] + amount * 2,
    ]


def align_text(screen, stri, x, y, color, font, align, bg_color):
    text_surface = font.render(stri, False, color)
    coor = (x - text_surface.get_width() * align, y - text_surface.get_height() / 2)
    if bg_color is not None:
        coor = (
            coor[0] - 4,
            coor[1],
            text_surface.get_width() + 8,
            text_surface.get_height(),
        )
        if bg_color[1] is not None:
            pygame.draw.rect(screen, bg_color[1], expand(coor, 2))
        pygame.draw.rect(screen, bg_color[0], coor)
    screen.blit(text_surface, coor)


def draw_clock(surface, coor, ratio, text, font):
    white = (255, 255, 255)
    grayish = (115, 125, 160)
    black = (0, 0, 0)

    x, y, r = coor
    num_arcs = 30
    for p in range(num_arcs):
        ratio1 = p / num_arcs
        ratio2 = (p + 1) / num_arcs
        ang1 = (ratio1 - 0.25) * 2 * math.pi
        ang2 = (ratio2 - 0.25) * 2 * math.pi
        points = [
            [x, y],
            [x + r * math.cos(ang1), y + r * math.sin(ang1)],
            [x + r * math.cos(ang2), y + r * math.sin(ang2)],
        ]
        pygame.draw.polygon(surface, grayish, points)

        if ratio > ratio2:
            pygame.draw.polygon(surface, white, points)
        elif ratio > ratio1:
            points2 = copy.deepcopy(points)
            prog = (ratio - ratio1) / (ratio2 - ratio1)
            points2[2][0] = lerp(points[1][0], points[2][0], prog)
            points2[2][1] = lerp(points[1][1], points[2][1], prog)
            pygame.draw.polygon(surface, white, points2)

    center_text(surface, text, x, y, black, font)


def draw_arrow(screen, _start, _end, margin, head, color):
    start = np.array(_start)
    end = np.array(_end)
    total_dist = np.linalg.norm(start - end)
    prog = margin / total_dist

    near_start = start + (end - start) * prog
    near_end = start + (end - start) * (1 - prog)

    pygame.draw.line(screen, color, near_start, near_end, width=2)  # main line

    angle = np.arctan2(start[1] - end[1], start[0] - end[0])
    for p in range(2):
        new_angle = angle + (p - 0.5) * 2 * math.pi * 0.25
        flare = [
            near_end[0] + math.cos(new_angle) * head,
            near_end[1] + math.sin(new_angle) * head,
        ]
        pygame.draw.line(screen, color, near_end, flare, width=2)


def draw_species_circle(
    screen, s, coor, radius, sim, species_info, font, should_draw_arrow, ui
):
    color = species_to_color(s, ui)
    name = species_to_name(s, ui)
    info = species_info[s]
    cx, cy = coor

    pygame.draw.circle(screen, color, coor, radius)
    center_text(screen, name, cx, cy - 22, (0, 0, 0), font)

    creature = sim.get_create_with_id(info.reps[2])
    tiny_icon = pygame.transform.scale(creature.icons[0], (50, 50))
    screen.blit(tiny_icon, (cx - 25, cy - 11))

    if should_draw_arrow:
        ancestor_id = species_info[s].parent_species
        if ancestor_id is None:
            draw_arrow(screen, (cx, -radius * 2), (cx, cy), radius, radius / 2, color)
        else:
            draw_arrow(
                screen,
                species_info[ancestor_id].coor,
                info.coor,
                radius,
                radius / 2,
                color,
            )
