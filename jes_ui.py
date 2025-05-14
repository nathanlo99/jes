import random
import time

import numpy as np
import pygame

from utils import (
    species_to_color,
    species_to_name,
    dist_to_text,
    clamp,
    get_distance,
    array_int_multiply,
)
from jes_dataviz import display_all_graphs, draw_all_graphs
from jes_shapes import (
    draw_ring_light,
    draw_x,
    display_centered_text,
    align_text,
    draw_species_circle,
)
from jes_slider import Slider
from jes_button import Button


class UI:
    def __init__(
        self,
        window_width,
        window_height,
        _movie_single_dimension,
        _graph_coor,
        _sac_coor,
        _geneology_coor,
        _column_margin,
        _mosaic_dim,
        _menu_text_up,
        _cm_margin1,
        _cm_margin2,
    ):
        self.slider_list = []
        self.button_list = []
        pygame.font.init()
        font_location = "visuals/overpass.ttf"
        self.big_font = pygame.font.Font(font_location, 60)
        self.small_font = pygame.font.Font(font_location, 30)
        self.tiny_font = pygame.font.Font(font_location, 21)
        self.background_pic = pygame.image.load("visuals/background.png")
        self.window_width = window_width
        self.window_height = window_height
        self.movie_single_dimension = _movie_single_dimension
        self.info_width = self.movie_single_dimension[0]

        self.graph_coords = _graph_coor
        self.graph = pygame.Surface(self.graph_coords[2:4], pygame.SRCALPHA, 32)
        self.sac_coords = _sac_coor
        self.labels = pygame.Surface(self.sac_coords[2:4], pygame.SRCALPHA, 32)
        self.geneology_coords = _geneology_coor
        self.gene_graph = pygame.Surface(
            self.geneology_coords[2:4], pygame.SRCALPHA, 32
        )

        self.column_margin = _column_margin
        self.mosaic_dim = _mosaic_dim
        self.menu_text_up = _menu_text_up

        self.cm_margin1 = _cm_margin1
        self.cm_margin2 = _cm_margin2
        self.mosaic_width = self.window_width - self.cm_margin1 * 2
        self.mosaic_width_creatures = (
            self.mosaic_width - self.info_width - self.column_margin
        )
        self.mosaic_height = (
            self.window_height - self.menu_text_up - self.cm_margin1 * 2
        )

        s1 = int(
            (self.mosaic_width_creatures) / self.mosaic_dim[0] - self.cm_margin2 * 2
        )
        s2 = int(
            (self.mosaic_width_creatures) / self.mosaic_dim[1] - self.cm_margin2 * 2
        )
        self.icon_dimension = ((s1, s1), (s2, s2), (s2, s2))

        self.mosaic_visible = False
        # Creature Location Highlight.
        # First: is it in the mosaic (0), or top-3? (1).
        # Second: Index of highlighted creature?
        # Third: rank of creature?
        self.clh = [None, None, None]
        self.creature_highlight = []
        self.slider_drag = None

        self.visual_sim_memory = []
        self.movie_screens = []
        self.sim = None

        self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        self.mosaic_screen = pygame.Surface(
            (self.mosaic_width_creatures, self.mosaic_height), pygame.SRCALPHA, 32
        )
        self.info_bar_screen = pygame.Surface(
            (self.info_width, self.mosaic_height), pygame.SRCALPHA, 32
        )
        self.preview_locations = [
            [570, 105, 250, 250],
            [570, 365, 250, 250],
            [570, 625, 250, 250],
        ]
        self.salt = str(random.uniform(0, 1))
        self.overridden_colors = (
            {}
        )  # special-case colors: species colored by the user, not RNG

        # variables for the "Watch sample" button
        self.sample_frames = 0
        self.sample_i = 0

        self.fps = 30
        pygame.time.Clock().tick(self.fps)

        # colors
        self.green = (0, 255, 0)
        self.grayish = (108, 118, 155)
        self.black = (0, 0, 0)
        self.white = (255, 255, 255)
        self.mosaic_color = (80, 80, 80)
        self.sample_freeze_time = 90
        self.show_xs = True
        self.species_storage = None
        self.storage_coor = (660, 52)
        self.running = True

        self.generation_slider = None
        self.show_creatures_button = None
        self.sort_button = None
        self.style_button = None
        self.sample_button = None
        self.do_generation_button = None
        self.alap_button = None

    def add_buttons_and_sliders(self):
        self.generation_slider = Slider(
            self,
            (40, self.window_height - 100, self.window_width - 80, 60, 140),
            0,
            0,
            0,
            True,
            True,
            self.update_generation_slider,
        )

        button_coords = []
        for i in range(6):
            button_coords.append(
                (
                    self.window_width - 1340 + 220 * i,
                    self.window_height - self.menu_text_up,
                    200,
                    60,
                )
            )
        self.show_creatures_button = Button(
            self,
            button_coords[0],
            ["Show creatures", "Hide creatures"],
            self.toggle_creatures,
        )
        self.sort_button = Button(
            self,
            button_coords[1],
            ["Sort by ID", "Sort by fitness", "Sort by weakness"],
            self.toggle_sort,
        )
        self.style_button = Button(
            self,
            button_coords[2],
            ["Big Icons", "Small Icons", "Species Tiles"],
            self.toggle_style,
        )
        self.sample_button = Button(
            self, button_coords[3], ["Watch sample", "Stop sample"], self.start_sample
        )
        self.do_generation_button = Button(
            self, button_coords[4], ["Do a generation"], self.sim.simulate_generation
        )
        self.alap_button = Button(
            self, button_coords[5], ["Turn on ALAP", "Turn off ALAP"], self.do_nothing
        )

    def reverse(self, i):
        return self.sim.creature_count - 1 - i

    def detect_mouse_motion(self):
        if self.sample_button.setting == 1:
            return
        gen = self.generation_slider.val
        mouse_x, mouse_y = pygame.mouse.get_pos()
        new_clh = [None, None, None]
        if self.mosaic_visible:
            relative_mouse_x = mouse_x - self.cm_margin1
            relative_mouse_y = mouse_y - self.cm_margin1
            if (
                0 <= relative_mouse_x < self.mosaic_width_creatures
                and 0 <= relative_mouse_y < self.mosaic_height
            ):
                dimensions = self.mosaic_dim[self.style_button.setting]
                spacing = self.mosaic_width_creatures / dimensions
                ix = min(int(relative_mouse_x / spacing), dimensions)
                iy = int(relative_mouse_y / spacing)
                i = iy * dimensions + ix
                if 0 <= i < self.sim.creature_count:
                    sort = self.sort_button.setting
                    if sort == 0 or gen >= len(self.sim.rankings):
                        new_clh = [0, i, i]
                    elif sort == 1:
                        new_clh = [0, self.sim.rankings[gen][i], i]
                    elif sort == 2:
                        new_clh = [0, self.sim.rankings[gen][self.reverse(i)], i]

        elif 0 <= gen < len(self.sim.rankings):
            # rolling mouse over the Best+Median+Worst previews
            for r, preview_location in enumerate(self.preview_locations):
                if (
                    preview_location[0]
                    <= mouse_x
                    < preview_location[0] + preview_location[2]
                    and preview_location[1]
                    <= mouse_y
                    < preview_location[1] + preview_location[3]
                ):
                    index = self.sim.rankings[gen][self.r_to_rank(r)]
                    new_clh = [1, index, r]

            # rolling mouse over species circles
            rolling_x = mouse_x - self.geneology_coords[0]
            rolling_y = mouse_y - self.geneology_coords[1]
            if (
                0 <= rolling_x < self.geneology_coords[2]
                and 0 <= rolling_y < self.geneology_coords[3]
            ):
                answer = self.get_rollover(rolling_x, rolling_y)
                if answer is not None:
                    new_clh = [2, answer]

            # rolling over storage
            if (
                self.species_storage is not None
                and get_distance(
                    mouse_x, mouse_y, self.storage_coor[0], self.storage_coor[1]
                )
                <= self.geneology_coords[4]
            ):
                new_clh = [2, self.species_storage]

        if new_clh[1] != self.clh[1]:
            self.clh = new_clh
            if self.clh[1] is None:
                self.clear_movies()
            elif self.clh[0] == 2:  # a species was highlighted
                info = self.sim.species_info[self.clh[1]]
                self.visual_sim_memory = []
                self.creature_highlight = []
                self.movie_screens = []
                for representative_id in info.representatives:
                    gen = representative_id // self.sim.creature_count
                    c = representative_id % self.sim.creature_count
                    self.creature_highlight.append(self.sim.creatures[gen][c])
                    self.visual_sim_memory.append(
                        self.sim.simulate_import(gen, c, c + 1, True)
                    )
                    self.movie_screens.append(None)
                self.draw_info_bar_species(self.clh[1])
            else:  # a creature was highlighted!
                self.creature_highlight = [self.sim.creatures[gen][self.clh[1]]]
                self.visual_sim_memory = [
                    self.sim.simulate_import(gen, self.clh[1], self.clh[1] + 1, True)
                ]
                self.movie_screens = [None] * 1
                self.draw_info_bar_creature(self.sim.creatures[gen][self.clh[1]])

    def clear_movies(self):
        self.visual_sim_memory = []
        self.creature_highlight = []
        self.movie_screens = []
        self.clh = [None, None, None]

    def get_rollover(self, mouse_x, mouse_y):
        answer = None
        ps = self.sim.prominent_species
        for level in range(len(ps)):
            for i in range(len(ps[level])):
                s = ps[level][i]
                sX, sY = self.sim.species_info[s].coords
                if get_distance(mouse_x, mouse_y, sX, sY) <= self.geneology_coords[4]:
                    answer = s
        return answer

    def draw_creature_mosaic(self, gen):
        self.mosaic_screen.fill(self.mosaic_color)
        for c in range(self.sim.creature_count):
            i = c
            if self.sim.creatures[gen][c].rank is not None:
                if self.sort_button.setting == 1:
                    i = self.sim.creatures[gen][c].rank
                elif self.sort_button.setting == 2:
                    i = self.reverse(self.sim.creatures[gen][c].rank)
            mosaic_dimension = self.mosaic_dim[self.style_button.setting]
            x = i % mosaic_dimension
            y = i // mosaic_dimension
            creature = self.sim.creatures[gen][c]
            spacing = self.mosaic_width_creatures / mosaic_dimension
            creature.icon_coor = (
                x * spacing + self.cm_margin2,
                y * spacing + self.cm_margin2,
                spacing,
                spacing,
            )
            if creature.icon_coor[1] < self.mosaic_screen.get_height():
                s = self.style_button.setting
                if s <= 1:
                    self.mosaic_screen.blit(creature.icons[s], creature.icon_coor)
                elif s == 2:
                    extra = 1
                    pygame.draw.rect(
                        self.mosaic_screen,
                        species_to_color(creature.species, self),
                        (
                            creature.icon_coor[0],
                            creature.icon_coor[1],
                            spacing + extra,
                            spacing + extra,
                        ),
                    )
                if not creature.living and self.show_xs:
                    color = (255, 0, 0) if s <= 1 else (0, 0, 0)
                    draw_x(
                        creature.icon_coor,
                        self.icon_dimension[s][0],
                        color,
                        self.mosaic_screen,
                    )

    def draw_info_bar_creature(self, creature):
        x_center = int(self.info_width * 0.5)
        self.info_bar_screen.fill(self.mosaic_color)
        stri = [
            f"Creature #{creature.id}",
            f"Species: {species_to_name(creature.species, self)}",
            "Untested",
        ]
        if creature.fitness is not None:
            fate = "Living" if creature.living else "Killed"
            stri = [
                f"Creature #{creature.id}",
                f"Species: {species_to_name(creature.species, self)}",
                f"Fitness: {dist_to_text(creature.fitness, True, self.sim.units_per_meter)}",
                f"Rank: {creature.rank + 1} - {fate}",
            ]

        for i, description in enumerate(stri):
            color = self.white
            if description.startswith("Species"):
                color = species_to_color(creature.species, self)
            display_centered_text(
                self.info_bar_screen,
                description,
                x_center,
                self.movie_single_dimension[1] + 40 + 42 * i,
                color,
                self.small_font,
            )

    def draw_movie_grid(self, screen, coords, mask, titles, colors, font):
        num_movie_screens = len(self.movie_screens)
        per_row = 1 if num_movie_screens == 1 else num_movie_screens // 2
        for i in range(num_movie_screens):
            if mask is not None and not mask[i]:
                continue
            movie_screen = self.movie_screens[i]
            movie_width = movie_screen.get_width()
            movie_height = movie_screen.get_height()
            x = coords[0] + (i % per_row) * movie_width
            y = coords[1] + (i // per_row) * movie_height
            screen.blit(movie_screen, (x, y))
            if titles is not None:
                display_centered_text(
                    screen,
                    titles[i],
                    x + movie_width / 2,
                    y + movie_height - 30,
                    colors[i],
                    font,
                )

    def draw_movie_quad(self, species):
        L = 4
        info = self.sim.species_info[species]
        a_name = species_to_name(info.parent_species, self)
        s_name = species_to_name(species, self)
        titles = ["Ancestor", "First", "Apex", "Last"]
        mask = [True] * 4
        for i in range(L):
            if (info.parent_species is None and i == 0) or (
                i >= 2 and info.get_when(i) == info.get_when(i - 1)
            ):
                mask[i] = False
                continue
            stri = a_name if i == 0 else s_name
            performance = info.get_performance(self.sim, i)
            titles[i] = (
                f"G{info.get_when(i)}: {titles[i]} {stri} ({dist_to_text(performance, True, self.sim.units_per_meter)})"
            )
        coords = (self.cm_margin1 + self.mosaic_width_creatures, 0)
        self.draw_movie_grid(
            self.screen, coords, mask, titles, [self.grayish] * L, self.tiny_font
        )

    def draw_info_bar_species(self, species):
        self.info_bar_screen.fill(self.mosaic_color)
        info = self.sim.species_info[species]
        a_name = species_to_name(info.parent_species, self)
        s_name = species_to_name(species, self)
        now = min(self.generation_slider.val, len(self.sim.species_pops) - 1)
        now_pop = 0
        extinct_string = " (Extinct)"
        if species in self.sim.species_pops[now]:
            now_pop = self.sim.species_pops[now][species][0]
            extinct_string = ""
        strings = [
            f"Species {s_name}",
            f"Ancestor {a_name}",
            f"Lifespan: G{info.get_when(1)} - G{info.get_when(3)}{extinct_string}",
            f"Population:   {info.apex_pop} at apex (G{info.get_when(2)})   |   {now_pop} now (G{now})",
        ]
        colors = [self.white] * len(strings)
        colors[0] = species_to_color(species, self)
        if info.parent_species is None:
            strings[1] = "Primordial species"
        else:
            colors[1] = species_to_color(info.parent_species, self)
        for i, string in enumerate(strings):
            x_center = int(self.info_width * (0.5 if i == 3 else 0.3))
            display_centered_text(
                self.info_bar_screen,
                string,
                x_center,
                self.movie_single_dimension[1] + 40 + 42 * i,
                colors[i],
                self.small_font,
            )

        self.draw_lightboard(
            self.info_bar_screen,
            species,
            now,
            (
                self.info_width * 0.6,
                self.movie_single_dimension[1] + 10,
                self.info_width * 0.37,
                self.mosaic_height - self.movie_single_dimension[1] - 20,
            ),
        )

    def draw_lightboard(self, screen, species, gen, coords):
        DIM = self.mosaic_dim[-1]
        R = coords[2] / DIM
        for c in range(self.sim.creature_count):
            x = coords[0] + R * (c % DIM)
            y = coords[1] + R * (c // DIM)
            col = (0, 0, 0)
            creature = self.sim.creatures[gen][self.sim.rankings[gen][c]]
            if creature.species == species:
                col = species_to_color(species, self)
            pygame.draw.rect(screen, col, (x, y, R, R))

    def draw_menu_text(self):
        y = self.window_height - self.menu_text_up
        title_surface = self.big_font.render(
            "Jelly Evolution Simulator", False, self.grayish
        )
        self.screen.blit(title_surface, (40, 20))
        a = str(int(self.generation_slider.val))
        b = str(int(self.generation_slider.val_max))
        generation_surface = self.big_font.render(
            "Generation " + a + " / " + b, False, (255, 255, 255)
        )
        self.screen.blit(generation_surface, (40, y))
        if self.species_storage is not None:
            s = self.species_storage
            radius = self.geneology_coords[4]
            draw_species_circle(
                self.screen,
                s,
                self.storage_coor,
                radius,
                self.sim,
                self.sim.species_info,
                self.tiny_font,
                False,
                self,
            )

    def r_to_rank(self, r):
        if r == 0:
            return 0
        return self.sim.creature_count - 1 if r == 2 else self.sim.creature_count // 2

    def draw_previews(self):
        gen = self.generation_slider.val
        if 0 <= gen < len(self.sim.rankings):
            names = ["Best", "Median", "Worst"]
            for r in range(3):
                r_i = self.r_to_rank(r)
                index = self.sim.rankings[gen][r_i]
                creature = self.sim.creatures[gen][index]
                dimensions = (
                    self.preview_locations[r][2],
                    self.preview_locations[r][3],
                )
                preview = creature.draw_icon(
                    dimensions, self.mosaic_color, self.sim.beat_fade_time
                )
                display_centered_text(
                    preview,
                    f"{names[r]} creature",
                    dimensions[0] / 2,
                    dimensions[1] - 20,
                    self.white,
                    self.small_font,
                )
                align_text(
                    preview,
                    dist_to_text(creature.fitness, True, self.sim.units_per_meter),
                    10,
                    20,
                    self.white,
                    self.small_font,
                    0.0,
                    None,
                )
                self.screen.blit(
                    preview,
                    (self.preview_locations[r][0], self.preview_locations[r][1]),
                )

    def do_movies(self):
        L = len(self.visual_sim_memory)
        movie_screen_scale = [1, 1, 0.5, 0.70]
        if self.sample_button.setting == 1:
            self.sample_frames += 1
            if self.sample_frames >= self.sim.trial_time + self.sample_freeze_time:
                self.start_sample_helper()
        for i in range(L):
            if self.visual_sim_memory[i][2] < self.sim.trial_time:
                self.visual_sim_memory[i] = self.sim.simulate_run(
                    self.visual_sim_memory[i], 1, False
                )
            DIM = array_int_multiply(
                self.movie_single_dimension, movie_screen_scale[self.clh[0]]
            )
            self.movie_screens[i] = pygame.Surface(DIM, pygame.SRCALPHA, 32)

            node_array, _, current_frame = self.visual_sim_memory[i]
            s = DIM[0] / (self.sim.CW + 2) * 0.5  # visual transform scale

            average_x = np.mean(node_array[:, :, :, 0])
            transform = [DIM[0] / 2 - average_x * s, DIM[1] * 0.8, s]
            self.creature_highlight[i].draw_creature(
                self.movie_screens[i],
                node_array[0],
                current_frame,
                transform,
                True,
                (i == 0),
            )

    def get_highlighted_species(self):
        gen = self.generation_slider.val
        if self.clh[0] == 2:
            return self.clh[1]
        if self.clh[0] == 0 or self.clh[0] == 1:
            return self.sim.creatures[gen][self.clh[1]].species
        return None

    def detect_events(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                new_gen = None
                if event.key == pygame.K_LEFT:
                    new_gen = max(0, self.generation_slider.val - 1)
                if event.key == pygame.K_RIGHT:
                    new_gen = min(
                        self.generation_slider.val_max, self.generation_slider.val + 1
                    )
                if new_gen is not None:
                    self.generation_slider.manual_update(new_gen)
                    self.clear_movies()
                    self.detect_mouse_motion()
                # pressing X will hide the Xs showing killed creatures
                if event.key == 120:
                    self.show_xs = not self.show_xs
                    self.draw_creature_mosaic(self.generation_slider.val)
                # pressing S will store the species of the creature you're
                # rolling over into "storage".
                elif event.key == 115:
                    self.species_storage = self.get_highlighted_species()
                # pressing C will change the highlighted species's color.
                elif event.key == 99:
                    c = self.get_highlighted_species()
                    if c is not None:
                        self.overridden_colors[c] = str(random.uniform(0, 1))
                        draw_all_graphs(self.sim, self)
                        self.clear_movies()
                        self.detect_mouse_motion()
                elif event.key == 13:  # pressing Enter
                    self.sim.simulate_generation(None)
                elif event.key == 113:  # pressing 'Q'
                    self.show_creatures_button.last_click_time = time.monotonic()
                    self.show_creatures_button.setting = (
                        1 - self.show_creatures_button.setting
                    )
                    self.toggle_creatures(self.show_creatures_button)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                for slider in self.slider_list:
                    s_x, s_y, s_w, s_h, _ = slider.dim
                    if s_x <= mouse_x < s_x + s_w and s_y <= mouse_y < s_y + s_h:
                        self.slider_drag = slider
                        break
                for button in self.button_list:
                    s_x, s_y, s_w, s_h = button.dim
                    if s_x <= mouse_x < s_x + s_w and s_y <= mouse_y < s_y + s_h:
                        button.click()
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.slider_drag is not None:
                    self.slider_drag.set_value()
                    self.slider_drag = None

    def draw_menu(self):
        self.screen.blit(self.background_pic, (0, 0))
        self.draw_menu_text()
        self.draw_previews()
        display_all_graphs(self.screen, self.sim, self)
        self.draw_sliders_and_buttons()
        self.display_creature_mosaic(self.screen)
        self.display_movies(self.screen)

    def display_creature_mosaic(self, screen):
        time_since_last_press = (
            time.monotonic() - self.show_creatures_button.last_click_time
        )
        pan_time = 0.2
        frac = clamp(time_since_last_press / pan_time)
        panel_y = 0
        if self.mosaic_visible:
            panel_y = self.cm_margin1 - self.mosaic_screen.get_height() * (1 - frac)
            screen.blit(self.mosaic_screen, (self.cm_margin1, panel_y))
        if not self.mosaic_visible and frac < 1:
            self.screen.blit(
                self.mosaic_screen,
                (
                    self.cm_margin1,
                    self.cm_margin1 - self.mosaic_screen.get_height() * frac,
                ),
            )

    def display_movies(self, screen):
        if self.clh[0] is None:
            return
        if self.clh[0] == 3:
            num_movie_screens = len(self.movie_screens)
            species_names = [None] * num_movie_screens
            species_colors = [None] * num_movie_screens
            for i in range(num_movie_screens):
                sp = self.creature_highlight[i].species
                species_names[i] = species_to_name(sp, self)
                species_colors[i] = species_to_color(sp, self)
            self.draw_movie_grid(
                screen,
                (0, 0),
                [True] * num_movie_screens,
                species_names,
                species_colors,
                self.small_font,
            )
            return
        gen = self.generation_slider.val
        coords = (self.cm_margin1 + self.mosaic_width_creatures, 0)
        self.screen.blit(self.info_bar_screen, coords)
        if self.clh[0] == 2:
            self.draw_movie_quad(self.clh[1])
            return
        self.screen.blit(self.movie_screens[0], coords)
        if self.clh[0] == 1:
            # TODO: destruct
            dimensions = self.preview_locations[self.clh[2]]
            self.screen.blit(
                draw_ring_light(dimensions[2], dimensions[3], 6),
                (dimensions[0], dimensions[1]),
            )
        else:
            coords = self.sim.creatures[gen][self.clh[1]].icon_coor
            x = coords[0] + self.cm_margin1
            y = coords[1] + self.cm_margin1
            self.screen.blit(draw_ring_light(coords[2], coords[3], 6), (x, y))

    def detect_sliders(self):
        if self.slider_drag is not None:
            mouse_x, _ = pygame.mouse.get_pos()
            s_x, _, s_w, _, s_dw = self.slider_drag.dim
            ratio = clamp(((mouse_x - s_dw * 0.5) - s_x) / (s_w - s_dw))

            s_range = self.slider_drag.val_max - self.slider_drag.val_min
            self.slider_drag.tval = ratio * s_range + self.slider_drag.val_min
            if self.slider_drag.snap_to_int:
                self.slider_drag.tval = round(self.slider_drag.tval)
            if self.slider_drag.update_live:
                self.slider_drag.set_value()

    def draw_sliders_and_buttons(self):
        for slider in self.slider_list:
            slider.draw_slider(self.screen)
        for button in self.button_list:
            button.draw_button(self.screen, self.small_font)

    # Button and slider functions
    def update_generation_slider(self, gen):
        self.draw_creature_mosaic(gen)

    def toggle_creatures(self, button):
        self.mosaic_visible = button.setting == 1

    def toggle_sort(self, _button):
        self.draw_creature_mosaic(self.generation_slider.val)

    def toggle_style(self, _button):
        self.draw_creature_mosaic(self.generation_slider.val)

    def do_nothing(self, _button):
        pass

    def start_sample(self, button):
        if button.setting == 1:
            self.sample_i = 0
            self.start_sample_helper()

    def start_sample_helper(self):
        num_samples = 8
        self.creature_highlight = []
        self.visual_sim_memory = []
        self.movie_screens = []
        self.clh = [3, 0]
        self.sample_frames = 0
        for sample_idx in range(num_samples):
            gen = self.generation_slider.val
            c = (self.sample_i + sample_idx) % self.sim.creature_count
            self.creature_highlight.append(self.sim.creatures[gen][c])
            self.visual_sim_memory.append(self.sim.simulate_import(gen, c, c + 1, True))
            self.movie_screens.append(None)
        self.sample_i += num_samples

    def show(self):
        pygame.display.flip()
