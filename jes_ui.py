import random
import time

import numpy as np
import pygame

from utils import (
    species_to_color,
    species_to_name,
    dist_to_text,
    bound,
    getDist,
    arrayIntMultiply,
)
from jes_dataviz import display_all_graphs, draw_all_graphs
from jes_shapes import (
    draw_ring_light,
    draw_x,
    center_text,
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
        # Creature Location Highlight. First: is it in the mosaic (0), or top-3? (1). Second: Index of highlighted creature? Third: rank of creature?
        self.CLH = [None, None, None]
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
        self.sc_colors = {}  # special-case colors: species colored by the user, not RNG

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
            self.toggleCreatures,
        )
        self.sort_button = Button(
            self,
            button_coords[1],
            ["Sort by ID", "Sort by fitness", "Sort by weakness"],
            self.toggleSort,
        )
        self.style_button = Button(
            self,
            button_coords[2],
            ["Big Icons", "Small Icons", "Species Tiles"],
            self.toggleStyle,
        )
        self.sample_button = Button(
            self, button_coords[3], ["Watch sample", "Stop sample"], self.startSample
        )
        self.do_generation_button = Button(
            self, button_coords[4], ["Do a generation"], self.sim.simulate_generation
        )
        self.alap_button = Button(
            self, button_coords[5], ["Turn on ALAP", "Turn off ALAP"], self.doNothing
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
            rel_mouseX = mouse_x - self.cm_margin1
            rel_mouseY = mouse_y - self.cm_margin1
            if (
                rel_mouseX >= 0
                and rel_mouseX < self.mosaic_width_creatures
                and rel_mouseY >= 0
                and rel_mouseY < self.mosaic_height
            ):
                DIM = self.mosaic_dim[self.style_button.setting]
                SPACING = self.mosaic_width_creatures / DIM
                ix = min(int(rel_mouseX / SPACING), DIM)
                iy = int(rel_mouseY / SPACING)
                i = iy * DIM + ix
                if 0 <= i < self.sim.creature_count:
                    sort = self.sort_button.setting
                    if sort == 0 or gen >= len(self.sim.rankings):
                        new_clh = [0, i, i]
                    elif sort == 1:
                        new_clh = [0, self.sim.rankings[gen][i], i]
                    elif sort == 2:
                        new_clh = [0, self.sim.rankings[gen][self.reverse(i)], i]

        elif gen >= 0 and gen < len(self.sim.rankings):
            # rolling mouse over the Best+Median+Worst previews
            for r in range(len(self.preview_locations)):
                PL = self.preview_locations[r]
                if (
                    mouse_x >= PL[0]
                    and mouse_x < PL[0] + PL[2]
                    and mouse_y >= PL[1]
                    and mouse_y < PL[1] + PL[3]
                ):
                    index = self.sim.rankings[gen][self.r_to_rank(r)]
                    new_clh = [1, index, r]

            # rolling mouse over species circles
            rX = mouse_x - self.geneology_coords[0]
            rY = mouse_y - self.geneology_coords[1]
            if (
                rX >= 0
                and rX < self.geneology_coords[2]
                and rY >= 0
                and rY < self.geneology_coords[3]
            ):
                answer = self.getRollOver(rX, rY)
                if answer is not None:
                    new_clh = [2, answer]

            # rolling over storage
            if (
                self.species_storage is not None
                and getDist(
                    mouse_x, mouse_y, self.storage_coor[0], self.storage_coor[1]
                )
                <= self.geneology_coords[4]
            ):
                new_clh = [2, self.species_storage]

        if new_clh[1] != self.CLH[1]:
            self.CLH = new_clh
            if self.CLH[1] is None:
                self.clearMovies()
            elif self.CLH[0] == 2:  # a species was highlighted
                info = self.sim.species_info[self.CLH[1]]
                L = len(info.reps)
                self.visual_sim_memory = []
                self.creature_highlight = []
                self.movie_screens = []
                for i in range(L):
                    ID = info.reps[i]
                    gen = ID // self.sim.creature_count
                    c = ID % self.sim.creature_count
                    self.creature_highlight.append(self.sim.creatures[gen][c])
                    self.visual_sim_memory.append(
                        self.sim.simulate_import(gen, c, c + 1, True)
                    )
                    self.movie_screens.append(None)
                self.drawInfoBarSpecies(self.CLH[1])
            else:  # a creature was highlighted!
                self.creature_highlight = [self.sim.creatures[gen][self.CLH[1]]]
                self.visual_sim_memory = [
                    self.sim.simulate_import(gen, self.CLH[1], self.CLH[1] + 1, True)
                ]
                self.movie_screens = [None] * 1
                self.drawInfoBarCreature(self.sim.creatures[gen][self.CLH[1]])

    def clearMovies(self):
        self.visual_sim_memory = []
        self.creature_highlight = []
        self.movie_screens = []
        self.CLH = [None, None, None]

    def getRollOver(self, mouse_x, mouse_y):
        answer = None
        ps = self.sim.prominent_species
        for level in range(len(ps)):
            for i in range(len(ps[level])):
                s = ps[level][i]
                sX, sY = self.sim.species_info[s].coor
                if getDist(mouse_x, mouse_y, sX, sY) <= self.geneology_coords[4]:
                    answer = s
        return answer

    def drawCreatureMosaic(self, gen):
        self.mosaic_screen.fill(self.mosaic_color)
        for c in range(self.sim.creature_count):
            i = c
            if self.sim.creatures[gen][c].rank is not None:
                if self.sort_button.setting == 1:
                    i = self.sim.creatures[gen][c].rank
                elif self.sort_button.setting == 2:
                    i = self.reverse(self.sim.creatures[gen][c].rank)
            DIM = self.mosaic_dim[self.style_button.setting]
            x = i % DIM
            y = i // DIM
            creature = self.sim.creatures[gen][c]
            SPACING = self.mosaic_width_creatures / DIM
            creature.icon_coor = (
                x * SPACING + self.cm_margin2,
                y * SPACING + self.cm_margin2,
                SPACING,
                SPACING,
            )
            if creature.icon_coor[1] < self.mosaic_screen.get_height():
                s = self.style_button.setting
                if s <= 1:
                    self.mosaic_screen.blit(creature.icons[s], creature.icon_coor)
                elif s == 2:
                    EXTRA = 1
                    pygame.draw.rect(
                        self.mosaic_screen,
                        species_to_color(creature.species, self),
                        (
                            creature.icon_coor[0],
                            creature.icon_coor[1],
                            SPACING + EXTRA,
                            SPACING + EXTRA,
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

    def drawInfoBarCreature(self, creature):
        X_center = int(self.info_width * 0.5)
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

        for i in range(len(stri)):
            color = self.white
            if stri[i][0:7] == "Species":
                color = species_to_color(creature.species, self)
            center_text(
                self.info_bar_screen,
                stri[i],
                X_center,
                self.movie_single_dimension[1] + 40 + 42 * i,
                color,
                self.small_font,
            )

    def drawMovieGrid(self, screen, coor, mask, titles, colors, font):
        LMS = len(self.movie_screens)
        per_row = 1 if LMS == 1 else LMS // 2
        for i in range(LMS):
            if mask is not None and not mask[i]:
                continue
            ms = self.movie_screens[i]
            W = ms.get_width()
            H = ms.get_height()
            x = coor[0] + (i % per_row) * W
            y = coor[1] + (i // per_row) * H
            screen.blit(ms, (x, y))
            if titles is not None:
                center_text(screen, titles[i], x + W / 2, y + H - 30, colors[i], font)

    def drawMovieQuad(self, species):
        L = 4
        info = self.sim.species_info[species]
        a_name = species_to_name(info.ancestor_id, self)
        s_name = species_to_name(species, self)
        titles = ["Ancestor", "First", "Apex", "Last"]
        mask = [True] * 4
        for i in range(L):
            if (info.ancestor_id is None and i == 0) or (
                i >= 2 and info.getWhen(i) == info.getWhen(i - 1)
            ):
                mask[i] = False
                continue
            stri = a_name if i == 0 else s_name
            performance = info.getPerformance(self.sim, i)
            titles[i] = (
                f"G{info.getWhen(i)}: {titles[i]} {stri} ({dist_to_text(performance, True, self.sim.units_per_meter)})"
            )
        coor = (self.cm_margin1 + self.mosaic_width_creatures, 0)
        self.drawMovieGrid(
            self.screen, coor, mask, titles, [self.grayish] * L, self.tiny_font
        )

    def drawInfoBarSpecies(self, species):
        self.info_bar_screen.fill(self.mosaic_color)
        info = self.sim.species_info[species]
        a_name = species_to_name(info.ancestor_id, self)
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
            f"Lifespan: G{info.getWhen(1)} - G{info.getWhen(3)}{extinct_string}",
            f"Population:   {info.apex_pop} at apex (G{info.getWhen(2)})   |   {now_pop} now (G{now})",
        ]
        colors = [self.white] * len(strings)
        colors[0] = species_to_color(species, self)
        if info.ancestor_id is None:
            strings[1] = "Primordial species"
        else:
            colors[1] = species_to_color(info.ancestor_id, self)
        for i in range(len(strings)):
            X_center = int(self.info_width * (0.5 if i == 3 else 0.3))
            center_text(
                self.info_bar_screen,
                strings[i],
                X_center,
                self.movie_single_dimension[1] + 40 + 42 * i,
                colors[i],
                self.small_font,
            )

        self.drawLightboard(
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

    def drawLightboard(self, screen, species, gen, coor):
        DIM = self.mosaic_dim[-1]
        R = coor[2] / DIM
        for c in range(self.sim.creature_count):
            x = coor[0] + R * (c % DIM)
            y = coor[1] + R * (c // DIM)
            col = (0, 0, 0)
            creature = self.sim.creatures[gen][self.sim.rankings[gen][c]]
            if creature.species == species:
                col = species_to_color(species, self)
            pygame.draw.rect(screen, col, (x, y, R, R))

    def drawMenuText(self):
        y = self.window_height - self.menu_text_up
        titleSurface = self.big_font.render(
            "Jelly Evolution Simulator", False, self.grayish
        )
        self.screen.blit(titleSurface, (40, 20))
        a = str(int(self.generation_slider.val))
        b = str(int(self.generation_slider.val_max))
        genSurface = self.big_font.render(
            "Generation " + a + " / " + b, False, (255, 255, 255)
        )
        self.screen.blit(genSurface, (40, y))
        if self.species_storage is not None:
            s = self.species_storage
            R = self.geneology_coords[4]
            draw_species_circle(
                self.screen,
                s,
                self.storage_coor,
                R,
                self.sim,
                self.sim.species_info,
                self.tiny_font,
                False,
                self,
            )

    def r_to_rank(self, r):
        return (
            0
            if r == 0
            else (
                self.sim.creature_count - 1 if r == 2 else self.sim.creature_count // 2
            )
        )

    def drawPreviews(self):
        gen = self.generation_slider.val
        if gen >= 0 and gen < len(self.sim.rankings):
            names = ["Best", "Median", "Worst"]
            for r in range(3):
                r_i = self.r_to_rank(r)
                index = self.sim.rankings[gen][r_i]
                creature = self.sim.creatures[gen][index]
                DIM = (self.preview_locations[r][2], self.preview_locations[r][3])
                preview = creature.draw_icon(
                    DIM, self.mosaic_color, self.sim.beat_fade_time
                )
                center_text(
                    preview,
                    f"{names[r]} creature",
                    DIM[0] / 2,
                    DIM[1] - 20,
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

    def doMovies(self):
        L = len(self.visual_sim_memory)
        movie_screen_scale = [1, 1, 0.5, 0.70]
        if self.sample_button.setting == 1:
            self.sample_frames += 1
            if self.sample_frames >= self.sim.trial_time + self.sample_freeze_time:
                self.startSampleHelper()
        for i in range(L):
            if self.visual_sim_memory[i][2] < self.sim.trial_time:
                self.visual_sim_memory[i] = self.sim.simulate_run(
                    self.visual_sim_memory[i], 1, False
                )
            DIM = arrayIntMultiply(
                self.movie_single_dimension, movie_screen_scale[self.CLH[0]]
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
        if self.CLH[0] == 2:
            return self.CLH[1]
        if self.CLH[0] == 0 or self.CLH[0] == 1:
            return self.sim.creatures[gen][self.CLH[1]].species
        return None

    def detectEvents(self):
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
                    self.generation_slider.manualUpdate(new_gen)
                    self.clearMovies()
                    self.detect_mouse_motion()
                # pressing X will hide the Xs showing killed creatures
                if event.key == 120:
                    self.show_xs = not self.show_xs
                    self.drawCreatureMosaic(self.generation_slider.val)
                # pressing S will store the species of the creature you're rolling over into "storage".
                elif event.key == 115:
                    self.species_storage = self.get_highlighted_species()
                elif (
                    event.key == 99
                ):  # pressing C will change the highlighted species's color.
                    c = self.get_highlighted_species()
                    if c is not None:
                        self.sc_colors[c] = str(random.uniform(0, 1))
                        draw_all_graphs(self.sim, self)
                        self.clearMovies()
                        self.detect_mouse_motion()
                elif event.key == 13:  # pressing Enter
                    self.sim.simulate_generation(None)
                elif event.key == 113:  # pressing 'Q'
                    self.show_creatures_button.last_click_time = time.monotonic()
                    self.show_creatures_button.setting = (
                        1 - self.show_creatures_button.setting
                    )
                    self.toggleCreatures(self.show_creatures_button)

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
                    self.slider_drag.updateVal()
                    self.slider_drag = None

    def drawMenu(self):
        self.screen.blit(self.background_pic, (0, 0))
        self.drawMenuText()
        self.drawPreviews()
        display_all_graphs(self.screen, self.sim, self)
        self.drawSlidersAndButtons()
        self.displayCreatureMosaic(self.screen)
        self.display_movies(self.screen)

    def displayCreatureMosaic(self, screen):
        time_since_last_press = (
            time.monotonic() - self.show_creatures_button.last_click_time
        )
        pan_time = 0.2
        frac = bound(time_since_last_press / pan_time)
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
        if self.CLH[0] is None:
            return
        if self.CLH[0] == 3:
            num_movie_screens = len(self.movie_screens)
            species_names = [None] * num_movie_screens
            species_colors = [None] * num_movie_screens
            for i in range(num_movie_screens):
                sp = self.creature_highlight[i].species
                species_names[i] = species_to_name(sp, self)
                species_colors[i] = species_to_color(sp, self)
            self.drawMovieGrid(
                screen,
                (0, 0),
                [True] * num_movie_screens,
                species_names,
                species_colors,
                self.small_font,
            )
            return
        gen = self.generation_slider.val
        coor = (self.cm_margin1 + self.mosaic_width_creatures, 0)
        self.screen.blit(self.info_bar_screen, coor)
        if self.CLH[0] == 2:
            self.drawMovieQuad(self.CLH[1])
            return
        self.screen.blit(self.movie_screens[0], coor)
        if self.CLH[0] == 1:
            # TODO: destruct
            dimensions = self.preview_locations[self.CLH[2]]
            self.screen.blit(
                draw_ring_light(dimensions[2], dimensions[3], 6),
                (dimensions[0], dimensions[1]),
            )
        else:
            coor = self.sim.creatures[gen][self.CLH[1]].icon_coor
            x = coor[0] + self.cm_margin1
            y = coor[1] + self.cm_margin1
            self.screen.blit(draw_ring_light(coor[2], coor[3], 6), (x, y))

    def detectSliders(self):
        if self.slider_drag is not None:
            mouse_x, _ = pygame.mouse.get_pos()
            s_x, _, s_w, _, s_dw = self.slider_drag.dim
            ratio = bound(((mouse_x - s_dw * 0.5) - s_x) / (s_w - s_dw))

            s_range = self.slider_drag.val_max - self.slider_drag.val_min
            self.slider_drag.tval = ratio * s_range + self.slider_drag.val_min
            if self.slider_drag.snap_to_int:
                self.slider_drag.tval = round(self.slider_drag.tval)
            if self.slider_drag.update_live:
                self.slider_drag.updateVal()

    def drawSlidersAndButtons(self):
        for slider in self.slider_list:
            slider.drawSlider(self.screen)
        for button in self.button_list:
            button.draw_button(self.screen, self.small_font)

    # Button and slider functions
    def update_generation_slider(self, gen):
        self.drawCreatureMosaic(gen)

    def toggleCreatures(self, button):
        self.mosaic_visible = button.setting == 1

    def toggleSort(self, button):
        self.drawCreatureMosaic(self.generation_slider.val)

    def toggleStyle(self, button):
        self.drawCreatureMosaic(self.generation_slider.val)

    def doNothing(self, button):
        a = 5

    def startSample(self, button):
        if button.setting == 1:
            self.sample_i = 0
            self.startSampleHelper()

    def startSampleHelper(self):
        L = 8
        self.creature_highlight = []
        self.visual_sim_memory = []
        self.movie_screens = []
        self.CLH = [3, 0]
        self.sample_frames = 0
        for i in range(L):
            gen = self.generation_slider.val
            c = (self.sample_i + i) % self.sim.creature_count
            self.creature_highlight.append(self.sim.creatures[gen][c])
            self.visual_sim_memory.append(self.sim.simulate_import(gen, c, c + 1, True))
            self.movie_screens.append(None)
        self.sample_i += L

    def show(self):
        pygame.display.flip()
