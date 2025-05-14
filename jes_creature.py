import math
import random

import pygame
import numpy as np

from utils import array_lerp, clamp, dist_to_text, species_to_color, list_lerp, lerp
from jes_shapes import draw_rect, draw_text_rect, display_centered_text, draw_clock


class Creature:
    def __init__(self, dna, id_number, parent_species, _sim, _ui):
        self.dna = dna
        self.calm_state = None
        self.icons = [None] * 2
        self.icon_coor = None
        self.id = id_number
        self.fitness = None
        self.rank = None
        self.living = True
        self.species = self.get_species(parent_species)
        self.sim = _sim
        self.ui = _ui
        self.codon_with_change = None

    def get_species(self, parent_species):
        return self.id if parent_species == -1 else parent_species

    def draw_cell(self, surface, node_state, frame, transform, x, y):
        tx, ty, s = transform
        color = self.traits_to_color(self.dna, x, y, frame)
        points = [None] * 4
        # TODO bruh
        for p in range(4):
            px = x
            if p in (1, 2):
                px += 1
            py = y + p // 2
            points[p] = [tx + node_state[px, py, 0] * s, ty + node_state[px, py, 1] * s]
        pygame.draw.polygon(surface, color, points)

    def draw_environment(self, surface, node_state, frame, transform):
        black = (0, 0, 0)
        white = (255, 255, 255)
        sign_color = (150, 100, 50)

        # sky
        draw_rect(surface, transform, None, black)

        # signs
        font = self.ui.big_font if transform[2] >= 50 else self.ui.small_font
        for meters in range(0, 3000, 100):
            u = meters * self.sim.units_per_meter
            draw_rect(surface, transform, [u - 0.2, -6, u + 0.2, 0], sign_color)
            draw_text_rect(
                surface,
                transform,
                [u - 1.5, -6.8, u + 1.5, -5.4],
                sign_color,
                white,
                f"{meters}cm",
                font,
            )

        # ground
        draw_rect(surface, transform, [None, 0, None, None], white)

    def draw_creature(
        self,
        surface,
        node_state,
        frame,
        transform,
        draw_labels: bool,
        should_draw_clock: bool,
    ):
        if draw_labels:
            self.draw_environment(surface, node_state, frame, transform)

        cell_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
        for x in range(self.sim.CW):
            for y in range(self.sim.CH):
                self.draw_cell(cell_surface, node_state, frame, transform, x, y)
        surface.blit(cell_surface, (0, 0))

        ratio = 1.0
        if draw_labels:
            tx, _, s = transform
            avg_x = np.mean(node_state[:, :, 0], axis=(0, 1))
            lx = tx + avg_x * s
            ly = 20
            lw = 100
            lh = 36
            ar = 15
            pygame.draw.rect(surface, (255, 0, 0), (lx - lw / 2, ly, lw, lh))
            pygame.draw.polygon(
                surface,
                (255, 0, 0),
                ((lx, ly + lh + ar), (lx - ar, ly + lh), (lx + ar, ly + lh)),
            )
            display_centered_text(
                surface,
                f"{dist_to_text(avg_x, True, self.sim.units_per_meter)}",
                lx,
                ly + 18,
                self.ui.white,
                self.ui.small_font,
            )

            ratio = 1 - frame / self.sim.trial_time
        if should_draw_clock:
            draw_clock(
                surface,
                [40, 40, 32],
                ratio,
                str(math.ceil(ratio * self.sim.trial_time / self.ui.fps)),
                self.ui.small_font,
            )

    def draw_icon(self, icon_dimension, background_color, beat_fade_time):
        icon = pygame.Surface(icon_dimension, pygame.SRCALPHA, 32)
        icon.fill(background_color)
        transform = [
            icon_dimension[0] / 2,
            icon_dimension[0] / (self.sim.CW + 2),
            icon_dimension[0] / (self.sim.CH + 2.85),
        ]
        self.draw_creature(
            icon, self.calm_state, beat_fade_time, transform, False, False
        )
        radius = icon_dimension[0] * 0.09
        radius2 = icon_dimension[0] * 0.12
        pygame.draw.circle(
            icon,
            species_to_color(self.species, self.ui),
            (icon_dimension[0] - radius2, radius2),
            radius,
        )
        return icon

    def save_calm_state(self, arr):
        self.calm_state = arr

    def get_mutated_dna(self, sim):
        mutation = np.clip(np.random.normal(0.0, 1.0, self.dna.shape[0]), -99, 99)
        result = self.dna + sim.mutation_rate * mutation
        new_species = self.species

        big_mut_loc = 0
        if random.uniform(0, 1) < self.sim.big_mutation_rate:  # do a big mutation
            new_species = sim.species_count
            sim.species_count += 1
            cell_x = random.randint(0, self.sim.CW - 1)
            cell_y = random.randint(0, self.sim.CH - 1)
            cell_beat = random.randint(0, self.sim.beats_per_cycle - 1)

            big_mut_loc = (
                cell_x * self.sim.CH * self.sim.beats_per_cycle
                + cell_y * self.sim.beats_per_cycle
                + cell_beat
            ) * self.sim.traits_per_box
            for i in range(self.sim.traits_per_box):
                delta = 0
                while abs(delta) < 0.5:
                    delta = np.random.normal(0.0, 1.0, 1)
                result[big_mut_loc + i] += delta

                # Cells that endure a big mutation are also required to be at
                # least somewhat rigid, because if a cell goes from super-short
                # to super-tall but has low rigidity the whole time, then it
                # doesn't really matter.
                if i == 2 and result[big_mut_loc + i] < 0.5:
                    result[big_mut_loc + i] = 0.5

        return result, new_species, big_mut_loc

    def traits_to_color(self, dna, x, y, frame):
        beat = self.sim.frame_to_beat(frame)
        beat_prev = (beat + self.sim.beats_per_cycle - 1) % self.sim.beats_per_cycle
        prog = self.sim.frame_to_beat_fade(frame)

        location_idx = x * self.sim.CH + y
        dna_idx = (
            location_idx * self.sim.beats_per_cycle + beat
        ) * self.sim.traits_per_box
        previous_dna_idx = (
            location_idx * self.sim.beats_per_cycle + beat_prev
        ) * self.sim.traits_per_box
        traits = dna[dna_idx : dna_idx + self.sim.traits_per_box]
        traits_prev = dna[previous_dna_idx : previous_dna_idx + self.sim.traits_per_box]
        traits = array_lerp(traits_prev, traits, prog)

        red = clamp(int(128 + traits[0] * 128), 0, 255)
        green = clamp(int(128 + traits[1] * 128), 0, 255)
        alpha = clamp(int(155 + traits[2] * 100), 64, 255)
        color_result = (red, green, 255, alpha)

        if self.codon_with_change is not None:
            next_green = 0.0
            if (
                self.codon_with_change >= dna_idx
                and self.codon_with_change < dna_idx + self.sim.traits_per_box
            ):
                next_green = 1.0
            previous_green = 0.0
            if (
                previous_dna_idx
                <= self.codon_with_change
                < previous_dna_idx + self.sim.traits_per_box
            ):
                previous_green = 1.0
            greenness = lerp(previous_green, next_green, prog)
            color_result = list_lerp(color_result, (0, 255, 0, 255), greenness)

        return color_result
