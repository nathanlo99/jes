import bisect
import math

import pygame

import numpy as np
from utils import getUnit, dist_to_text, species_to_name, species_to_color
from jes_shapes import right_text, align_text, draw_species_circle


def draw_all_graphs(sim, ui):
    draw_line_graph(
        sim.percentiles, ui.graph, [70, 0, 30, 30], sim.units_per_meter, ui.small_font
    )
    draw_labels(sim.species_pops, ui.labels, [70, 0], ui)
    draw_gene_graph(
        sim.species_info, sim.prominent_species, ui.gene_graph, sim, ui, ui.tiny_font
    )


def draw_line_graph(data, graph, margins, u, font):
    black = (0, 0, 0)
    gray_25 = (70, 70, 70)
    gray_50 = (128, 128, 128)
    white = (255, 255, 255)
    red = (255, 0, 0)

    graph.fill(black)
    w = graph.get_width() - margins[0] - margins[1]
    h = graph.get_height() - margins[2] - margins[3]
    left = margins[0]
    right = graph.get_width() - margins[1]
    bottom = graph.get_height() - margins[3]

    min_val = np.amin(data)
    max_val = np.amax(data)
    unit = getUnit((max_val - min_val) / u) * u
    tick = math.floor(min_val / unit) * unit - unit
    while tick <= max_val + unit:
        ay = bottom - h * (tick - min_val) / (max_val - min_val)
        pygame.draw.line(graph, gray_25, (left, ay), (right, ay), width=1)
        right_text(graph, dist_to_text(tick, False, u), left - 7, ay, gray_50, font)
        tick += unit

    percentiles_to_display = [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        91,
        92,
        93,
        94,
        95,
        96,
        97,
        98,
        99,
        100,
    ]
    num_generations = len(data)
    for generation in range(num_generations):
        for percentile in percentiles_to_display:
            previous_value = 0 if generation == 0 else data[generation - 1][percentile]
            next_value = data[generation][percentile]

            x1 = left + (generation / num_generations) * w
            x2 = left + ((generation + 1) / num_generations) * w
            y1 = bottom - h * (previous_value - min_val) / (max_val - min_val)
            y2 = bottom - h * (next_value - min_val) / (max_val - min_val)

            is_important = percentile % 10 == 0
            thickness = 2 if is_important else 1
            color = white if is_important else gray_50
            if percentile == 50:
                color = red
                thickness = 3
            pygame.draw.line(graph, color, (x1, y1), (x2, y2), width=thickness)


def draw_labels(data, labels, margins, ui):
    labels.fill((0, 0, 0))
    for g in range(len(data)):
        scan_down_trapezoids(data, g, labels, margins, ui)


def scan_down_trapezoids(data, generation_idx, labels, margins, ui):
    width = labels.get_width() - margins[0] - margins[1]
    height = labels.get_height()
    num_generations = len(data)
    left = margins[0]
    x1 = left + (generation_idx / num_generations) * width
    x2 = left + ((generation_idx + 1) / num_generations) * width
    keys = sorted(list(data[generation_idx].keys()))
    creature_count = data[generation_idx][keys[-1]][2]  # ending index of the last entry
    height_per_creature = height / creature_count

    if generation_idx == 0:
        for sp in data[generation_idx].keys():
            pop = data[generation_idx][sp]
            points = [
                [x1, height / 2],
                [x1, height / 2],
                [x2, height - pop[1] * height_per_creature],
                [x2, height - pop[2] * height_per_creature],
            ]
            pygame.draw.polygon(labels, species_to_color(sp, ui), points)
    else:
        trapezoid_helper(
            labels,
            data,
            generation_idx,
            generation_idx - 1,
            x1,
            x2,
            height_per_creature,
            0,
            ui,
        )


# TODO naming
def get_range_even_if_none(dicty, key):
    keys = sorted(list(dicty.keys()))
    if key in keys:
        return dicty[key]
    else:
        n = bisect.bisect(keys, key + 0.5)
        if n >= len(keys):
            val = dicty[keys[n - 1]][2]
        else:
            val = dicty[keys[n]][1]
        return [0, val, val]


# TODO bruh naming
def trapezoid_helper(sac, data, g1, g2, x1, x2, pixels_per_creature, level, ui):
    pop2 = [0, 0, 0]
    h = sac.get_height()
    for sp in data[g1].keys():
        pop1 = data[g1][sp]
        if level == 0 and pop1[1] != pop2[2]:  # there was a gap
            trapezoid_helper(sac, data, g2, g1, x2, x1, pixels_per_creature, 1, ui)
        pop2 = get_range_even_if_none(data[g2], sp)
        points = [
            [x1, h - pop2[1] * pixels_per_creature],
            [x1, h - pop2[2] * pixels_per_creature],
            [x2, h - pop1[2] * pixels_per_creature],
            [x2, h - pop1[1] * pixels_per_creature],
        ]
        pygame.draw.polygon(sac, species_to_color(sp, ui), points)


def draw_gene_graph(species_info, prominent_species, gene_graph, sim, ui, font):
    r = ui.geneology_coords[4]
    h = gene_graph.get_height() - r * 2
    w = gene_graph.get_width() - r * 2
    gene_graph.fill((0, 0, 0))
    if len(sim.creatures) == 0:
        return

    for level in range(len(prominent_species)):
        for i in range(len(prominent_species[level])):
            s = prominent_species[level][i]
            x = (i + 0.5) / (len(prominent_species[level])) * w + r
            y = (level) / (len(prominent_species) - 0.8) * h + r
            species_info[s].coords = (x, y)

    for level in range(len(prominent_species)):
        for i in range(len(prominent_species[level])):
            s = prominent_species[level][i]
            draw_species_circle(
                gene_graph,
                s,
                species_info[s].coords,
                r,
                sim,
                species_info,
                font,
                True,
                ui,
            )


def display_all_graphs(screen, sim, ui):
    white = (255, 255, 255)
    blit_graphs_and_marks(screen, sim, ui)
    blit_gene_graph_and_marks(screen, sim, ui)

    if sim.last_gen_run_time >= 0:
        right_text(
            screen,
            f"Last gen runtime: {sim.last_gen_run_time:.3f}s",
            1200,
            28,
            white,
            ui.small_font,
        )


def blit_graphs_and_marks(screen, sim, ui):
    screen.blit(ui.graph, ui.graph_coords[0:2])
    screen.blit(ui.labels, ui.sac_coords[0:2])
    green = (0, 255, 0)
    white = (255, 255, 255)
    a = int(ui.generation_slider.val)
    b = int(ui.generation_slider.val_max)
    a2 = min(a, b - 1)
    if b == 0:
        return

    if a < b:
        frac = (a + 1) / b
        line_x = ui.sac_coords[0] + 70 + (ui.graph.get_width() - 70) * frac
        line_ys = [[50, 550], [560, 860]]
        for line_y in line_ys:
            pygame.draw.line(
                screen, green, (line_x, line_y[0]), (line_x, line_y[1]), width=2
            )

    frac = (a2 + 1) / b
    line_x = ui.sac_coords[0] + 70 + (ui.graph.get_width() - 70) * frac
    median = sim.percentiles[a2][50]
    right_text(
        screen,
        f"Median: {dist_to_text(median, True, sim.units_per_meter)}",
        1800,
        28,
        white,
        ui.small_font,
    )

    top_species = get_top_species(sim, a2)
    for sp in sim.species_pops[a2].keys():
        pop = sim.species_pops[a2][sp]
        if pop[0] >= sim.creature_count * sim.s_visible:
            species_i = (pop[1] + pop[2]) / 2
            species_y = 560 + 300 * (1 - species_i / sim.creature_count)
            name = species_to_name(sp, ui)
            color = species_to_color(sp, ui)
            outline_color = ui.white if sp == top_species else None
            align_text(
                screen,
                f"{name}: {pop[0]}",
                line_x + 10,
                species_y,
                color,
                ui.small_font,
                0.0,
                [ui.black, outline_color],
            )


def blit_gene_graph_and_marks(screen, sim, ui):
    screen.blit(ui.gene_graph, ui.geneology_coords[0:2])
    radius = 42
    a = int(ui.generation_slider.val)
    b = int(ui.generation_slider.val_max)
    a2 = min(a, b - 1)
    if b == 0:
        return
    top_species = get_top_species(sim, a2)

    for sp in sim.species_pops[a2].keys():
        info = sim.species_info[sp]
        if not info.prominent:
            continue
        circle_count = 2 if sp == top_species else 1
        cx = info.coords[0] + ui.geneology_coords[0]
        cy = info.coords[1] + ui.geneology_coords[1]
        for c in range(circle_count):
            pygame.draw.circle(screen, ui.white, (cx, cy), radius + 3 + 6 * c, 3)

    if ui.species_storage is not None:
        sp = ui.species_storage
        if sp in sim.species_pops[a2]:
            circle_count = 2 if sp == top_species else 1
            for c in range(circle_count):
                pygame.draw.circle(
                    screen, ui.white, ui.storage_coor, radius + 3 + 6 * c, 3
                )


def get_top_species(sim, g):
    data = sim.species_pops[g]
    return max(data, key=data.get)
