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
        _W_W,
        _W_H,
        _MOVIE_SINGLE_DIM,
        _GRAPH_COOR,
        _SAC_COOR,
        _GENEALOGY_COOR,
        _COLUMN_MARGIN,
        _MOSAIC_DIM,
        _MENU_TEXT_UP,
        _CM_MARGIN1,
        _CM_MARGIN2,
    ):
        self.slider_list = []
        self.button_list = []
        pygame.font.init()
        font_location = "visuals/overpass.ttf"
        self.big_font = pygame.font.Font(font_location, 60)
        self.small_font = pygame.font.Font(font_location, 30)
        self.tiny_font = pygame.font.Font(font_location, 21)
        self.background_pic = pygame.image.load("visuals/background.png")
        self.W_W = _W_W
        self.W_H = _W_H
        self.MOVIE_SINGLE_DIM = _MOVIE_SINGLE_DIM
        self.INFO_W = self.MOVIE_SINGLE_DIM[0]

        self.GRAPH_COOR = _GRAPH_COOR
        self.graph = pygame.Surface(self.GRAPH_COOR[2:4], pygame.SRCALPHA, 32)
        self.SAC_COOR = _SAC_COOR
        self.sac = pygame.Surface(self.SAC_COOR[2:4], pygame.SRCALPHA, 32)
        self.GENEALOGY_COOR = _GENEALOGY_COOR
        self.gene_graph = pygame.Surface(self.GENEALOGY_COOR[2:4], pygame.SRCALPHA, 32)

        self.COLUMN_MARGIN = _COLUMN_MARGIN
        self.MOSAIC_DIM = _MOSAIC_DIM
        self.MENU_TEXT_UP = _MENU_TEXT_UP

        self.CM_MARGIN1 = _CM_MARGIN1
        self.CM_MARGIN2 = _CM_MARGIN2
        self.MS_W = self.W_W - self.CM_MARGIN1 * 2  # mosaic screen width
        self.MS_WC = (
            self.MS_W - self.INFO_W - self.COLUMN_MARGIN
        )  # mosaic screen width (just creatures)
        self.MS_H = self.W_H - self.MENU_TEXT_UP - self.CM_MARGIN1 * 2

        s1 = int((self.MS_WC) / self.MOSAIC_DIM[0] - self.CM_MARGIN2 * 2)
        s2 = int((self.MS_WC) / self.MOSAIC_DIM[1] - self.CM_MARGIN2 * 2)
        self.ICON_DIM = ((s1, s1), (s2, s2), (s2, s2))

        self.mosaic_visible = False
        self.CLH = [
            None,
            None,
            None,
        ]  # Creature Location Highlight. First: is it in the mosaic (0), or top-3? (1). Second: Index of highlighted creature? Third: rank of creature?
        self.creatureHighlight = []
        self.sliderDrag = None

        self.visualSimMemory = []
        self.movieScreens = []
        self.sim = None

        self.screen = pygame.display.set_mode((self.W_W, self.W_H))
        self.mosaicScreen = pygame.Surface((self.MS_WC, self.MS_H), pygame.SRCALPHA, 32)
        self.infoBarScreen = pygame.Surface(
            (self.INFO_W, self.MS_H), pygame.SRCALPHA, 32
        )
        self.previewLocations = [
            [570, 105, 250, 250],
            [570, 365, 250, 250],
            [570, 625, 250, 250],
        ]
        self.salt = str(random.uniform(0, 1))
        self.sc_colors = {}  # special-case colors: species colored by the user, not RNG

        # variables for the "Watch sample" button
        self.sampleFrames = 0
        self.sample_i = 0

        self.FPS = 30
        pygame.time.Clock().tick(self.FPS)

        # colors
        self.GREEN = (0, 255, 0)
        self.GRAYISH = (108, 118, 155)
        self.BLACK = (0, 0, 0)
        self.white = (255, 255, 255)
        self.MOSAIC_COLOR = (80, 80, 80)
        self.SAMPLE_FREEZE_TIME = 90
        self.showXs = True
        self.species_storage = None
        self.storage_coor = (660, 52)
        self.running = True

    def addButtonsAndSliders(self):
        self.genSlider = Slider(
            self,
            (40, self.W_H - 100, self.W_W - 80, 60, 140),
            0,
            0,
            0,
            True,
            True,
            self.updateGenSlider,
        )

        buttonCoor = []
        for i in range(6):
            buttonCoor.append(
                (self.W_W - 1340 + 220 * i, self.W_H - self.MENU_TEXT_UP, 200, 60)
            )
        self.showCreaturesButton = Button(
            self,
            buttonCoor[0],
            ["Show creatures", "Hide creatures"],
            self.toggleCreatures,
        )
        self.sortButton = Button(
            self,
            buttonCoor[1],
            ["Sort by ID", "Sort by fitness", "Sort by weakness"],
            self.toggleSort,
        )
        self.styleButton = Button(
            self,
            buttonCoor[2],
            ["Big Icons", "Small Icons", "Species Tiles"],
            self.toggleStyle,
        )
        self.sampleButton = Button(
            self, buttonCoor[3], ["Watch sample", "Stop sample"], self.startSample
        )
        self.doGenButton = Button(
            self, buttonCoor[4], ["Do a generation"], self.sim.doGeneration
        )
        self.ALAPButton = Button(
            self, buttonCoor[5], ["Turn on ALAP", "Turn off ALAP"], self.doNothing
        )

    def reverse(self, i):
        return self.sim.c_count - 1 - i

    def detectMouseMotion(self):
        if self.sampleButton.setting == 1:
            return
        gen = self.genSlider.val
        mouse_x, mouse_y = pygame.mouse.get_pos()
        newCLH = [None, None, None]
        if self.mosaic_visible:
            rel_mouseX = mouse_x - self.CM_MARGIN1
            rel_mouseY = mouse_y - self.CM_MARGIN1
            if (
                rel_mouseX >= 0
                and rel_mouseX < self.MS_WC
                and rel_mouseY >= 0
                and rel_mouseY < self.MS_H
            ):
                DIM = self.MOSAIC_DIM[self.styleButton.setting]
                SPACING = self.MS_WC / DIM
                ix = min(int(rel_mouseX / SPACING), DIM)
                iy = int(rel_mouseY / SPACING)
                i = iy * DIM + ix
                if 0 <= i < self.sim.c_count:
                    sort = self.sortButton.setting
                    if sort == 0 or gen >= len(self.sim.rankings):
                        newCLH = [0, i, i]
                    elif sort == 1:
                        newCLH = [0, self.sim.rankings[gen][i], i]
                    elif sort == 2:
                        newCLH = [0, self.sim.rankings[gen][self.reverse(i)], i]

        elif gen >= 0 and gen < len(self.sim.rankings):
            # rolling mouse over the Best+Median+Worst previews
            for r in range(len(self.previewLocations)):
                PL = self.previewLocations[r]
                if (
                    mouse_x >= PL[0]
                    and mouse_x < PL[0] + PL[2]
                    and mouse_y >= PL[1]
                    and mouse_y < PL[1] + PL[3]
                ):
                    index = self.sim.rankings[gen][self.r_to_rank(r)]
                    newCLH = [1, index, r]

            # rolling mouse over species circles
            rX = mouse_x - self.GENEALOGY_COOR[0]
            rY = mouse_y - self.GENEALOGY_COOR[1]
            if (
                rX >= 0
                and rX < self.GENEALOGY_COOR[2]
                and rY >= 0
                and rY < self.GENEALOGY_COOR[3]
            ):
                answer = self.getRollOver(rX, rY)
                if answer is not None:
                    newCLH = [2, answer]

            # rolling over storage
            if (
                self.species_storage is not None
                and getDist(
                    mouse_x, mouse_y, self.storage_coor[0], self.storage_coor[1]
                )
                <= self.GENEALOGY_COOR[4]
            ):
                newCLH = [2, self.species_storage]

        if newCLH[1] != self.CLH[1]:
            self.CLH = newCLH
            if self.CLH[1] is None:
                self.clearMovies()
            elif self.CLH[0] == 2:  # a species was highlighted
                info = self.sim.species_info[self.CLH[1]]
                L = len(info.reps)
                self.visualSimMemory = []
                self.creatureHighlight = []
                self.movieScreens = []
                for i in range(L):
                    ID = info.reps[i]
                    gen = ID // self.sim.c_count
                    c = ID % self.sim.c_count
                    self.creatureHighlight.append(self.sim.creatures[gen][c])
                    self.visualSimMemory.append(
                        self.sim.simulate_import(gen, c, c + 1, True)
                    )
                    self.movieScreens.append(None)
                self.drawInfoBarSpecies(self.CLH[1])
            else:  # a creature was highlighted!
                self.creatureHighlight = [self.sim.creatures[gen][self.CLH[1]]]
                self.visualSimMemory = [
                    self.sim.simulate_import(gen, self.CLH[1], self.CLH[1] + 1, True)
                ]
                self.movieScreens = [None] * 1
                self.drawInfoBarCreature(self.sim.creatures[gen][self.CLH[1]])

    def clearMovies(self):
        self.visualSimMemory = []
        self.creatureHighlight = []
        self.movieScreens = []
        self.CLH = [None, None, None]

    def getRollOver(self, mouse_x, mouse_y):
        answer = None
        ps = self.sim.prominent_species
        for level in range(len(ps)):
            for i in range(len(ps[level])):
                s = ps[level][i]
                sX, sY = self.sim.species_info[s].coor
                if getDist(mouse_x, mouse_y, sX, sY) <= self.GENEALOGY_COOR[4]:
                    answer = s
        return answer

    def drawCreatureMosaic(self, gen):
        self.mosaicScreen.fill(self.MOSAIC_COLOR)
        for c in range(self.sim.c_count):
            i = c
            if self.sim.creatures[gen][c].rank is not None:
                if self.sortButton.setting == 1:
                    i = self.sim.creatures[gen][c].rank
                elif self.sortButton.setting == 2:
                    i = self.reverse(self.sim.creatures[gen][c].rank)
            DIM = self.MOSAIC_DIM[self.styleButton.setting]
            x = i % DIM
            y = i // DIM
            creature = self.sim.creatures[gen][c]
            SPACING = self.MS_WC / DIM
            creature.icon_coor = (
                x * SPACING + self.CM_MARGIN2,
                y * SPACING + self.CM_MARGIN2,
                SPACING,
                SPACING,
            )
            if creature.icon_coor[1] < self.mosaicScreen.get_height():
                s = self.styleButton.setting
                if s <= 1:
                    self.mosaicScreen.blit(creature.icons[s], creature.icon_coor)
                elif s == 2:
                    EXTRA = 1
                    pygame.draw.rect(
                        self.mosaicScreen,
                        species_to_color(creature.species, self),
                        (
                            creature.icon_coor[0],
                            creature.icon_coor[1],
                            SPACING + EXTRA,
                            SPACING + EXTRA,
                        ),
                    )
                if not creature.living and self.showXs:
                    color = (255, 0, 0) if s <= 1 else (0, 0, 0)
                    draw_x(
                        creature.icon_coor,
                        self.ICON_DIM[s][0],
                        color,
                        self.mosaicScreen,
                    )

    def drawInfoBarCreature(self, creature):
        X_center = int(self.INFO_W * 0.5)
        self.infoBarScreen.fill(self.MOSAIC_COLOR)
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
                f"Fitness: {dist_to_text(creature.fitness, True, self.sim.UNITS_PER_METER)}",
                f"Rank: {creature.rank + 1} - {fate}",
            ]

        for i in range(len(stri)):
            color = self.white
            if stri[i][0:7] == "Species":
                color = species_to_color(creature.species, self)
            center_text(
                self.infoBarScreen,
                stri[i],
                X_center,
                self.MOVIE_SINGLE_DIM[1] + 40 + 42 * i,
                color,
                self.small_font,
            )

    def drawMovieGrid(self, screen, coor, mask, titles, colors, font):
        LMS = len(self.movieScreens)
        per_row = 1 if LMS == 1 else LMS // 2
        for i in range(LMS):
            if mask is not None and not mask[i]:
                continue
            ms = self.movieScreens[i]
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
                f"G{info.getWhen(i)}: {titles[i]} {stri} ({dist_to_text(performance, True, self.sim.UNITS_PER_METER)})"
            )
        coor = (self.CM_MARGIN1 + self.MS_WC, 0)
        self.drawMovieGrid(
            self.screen, coor, mask, titles, [self.GRAYISH] * L, self.tiny_font
        )

    def drawInfoBarSpecies(self, species):
        self.infoBarScreen.fill(self.MOSAIC_COLOR)
        info = self.sim.species_info[species]
        a_name = species_to_name(info.ancestor_id, self)
        s_name = species_to_name(species, self)
        now = min(self.genSlider.val, len(self.sim.species_pops) - 1)
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
            X_center = int(self.INFO_W * (0.5 if i == 3 else 0.3))
            center_text(
                self.infoBarScreen,
                strings[i],
                X_center,
                self.MOVIE_SINGLE_DIM[1] + 40 + 42 * i,
                colors[i],
                self.small_font,
            )

        self.drawLightboard(
            self.infoBarScreen,
            species,
            now,
            (
                self.INFO_W * 0.6,
                self.MOVIE_SINGLE_DIM[1] + 10,
                self.INFO_W * 0.37,
                self.MS_H - self.MOVIE_SINGLE_DIM[1] - 20,
            ),
        )

    def drawLightboard(self, screen, species, gen, coor):
        DIM = self.MOSAIC_DIM[-1]
        R = coor[2] / DIM
        for c in range(self.sim.c_count):
            x = coor[0] + R * (c % DIM)
            y = coor[1] + R * (c // DIM)
            col = (0, 0, 0)
            creature = self.sim.creatures[gen][self.sim.rankings[gen][c]]
            if creature.species == species:
                col = species_to_color(species, self)
            pygame.draw.rect(screen, col, (x, y, R, R))

    def drawMenuText(self):
        y = self.W_H - self.MENU_TEXT_UP
        titleSurface = self.big_font.render(
            "Jelly Evolution Simulator", False, self.GRAYISH
        )
        self.screen.blit(titleSurface, (40, 20))
        a = str(int(self.genSlider.val))
        b = str(int(self.genSlider.val_max))
        genSurface = self.big_font.render(
            "Generation " + a + " / " + b, False, (255, 255, 255)
        )
        self.screen.blit(genSurface, (40, y))
        if self.species_storage is not None:
            s = self.species_storage
            R = self.GENEALOGY_COOR[4]
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
            0 if r == 0 else (self.sim.c_count - 1 if r == 2 else self.sim.c_count // 2)
        )

    def drawPreviews(self):
        gen = self.genSlider.val
        if gen >= 0 and gen < len(self.sim.rankings):
            names = ["Best", "Median", "Worst"]
            for r in range(3):
                r_i = self.r_to_rank(r)
                index = self.sim.rankings[gen][r_i]
                creature = self.sim.creatures[gen][index]
                DIM = (self.previewLocations[r][2], self.previewLocations[r][3])
                preview = creature.draw_icon(
                    DIM, self.MOSAIC_COLOR, self.sim.beat_fade_time
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
                    dist_to_text(creature.fitness, True, self.sim.UNITS_PER_METER),
                    10,
                    20,
                    self.white,
                    self.small_font,
                    0.0,
                    None,
                )
                self.screen.blit(
                    preview, (self.previewLocations[r][0], self.previewLocations[r][1])
                )

    def doMovies(self):
        L = len(self.visualSimMemory)
        movie_screen_scale = [1, 1, 0.5, 0.70]
        if self.sampleButton.setting == 1:
            self.sample_frames += 1
            if self.sample_frames >= self.sim.trial_time + self.SAMPLE_FREEZE_TIME:
                self.startSampleHelper()
        for i in range(L):
            if self.visualSimMemory[i][2] < self.sim.trial_time:
                self.visualSimMemory[i] = self.sim.simulate_run(
                    self.visualSimMemory[i], 1, False
                )
            DIM = arrayIntMultiply(
                self.MOVIE_SINGLE_DIM, movie_screen_scale[self.CLH[0]]
            )
            self.movieScreens[i] = pygame.Surface(DIM, pygame.SRCALPHA, 32)

            node_array, _, current_frame = self.visualSimMemory[i]
            s = DIM[0] / (self.sim.CW + 2) * 0.5  # visual transform scale

            average_x = np.mean(node_array[:, :, :, 0])
            transform = [DIM[0] / 2 - average_x * s, DIM[1] * 0.8, s]
            self.creatureHighlight[i].draw_creature(
                self.movieScreens[i],
                node_array[0],
                current_frame,
                transform,
                True,
                (i == 0),
            )

    def get_highlighted_species(self):
        gen = self.genSlider.val
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
                    new_gen = max(0, self.genSlider.val - 1)
                if event.key == pygame.K_RIGHT:
                    new_gen = min(self.genSlider.val_max, self.genSlider.val + 1)
                if new_gen is not None:
                    self.genSlider.manualUpdate(new_gen)
                    self.clearMovies()
                    self.detectMouseMotion()
                # pressing X will hide the Xs showing killed creatures
                if event.key == 120:
                    self.showXs = not self.showXs
                    self.drawCreatureMosaic(self.genSlider.val)
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
                        self.detectMouseMotion()
                elif event.key == 13:  # pressing Enter
                    self.sim.doGeneration(None)
                elif event.key == 113:  # pressing 'Q'
                    self.showCreaturesButton.last_click_time = time.time()
                    self.showCreaturesButton.setting = (
                        1 - self.showCreaturesButton.setting
                    )
                    self.toggleCreatures(self.showCreaturesButton)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                for slider in self.slider_list:
                    s_x, s_y, s_w, s_h, _ = slider.dim
                    if s_x <= mouse_x < s_x + s_w and s_y <= mouse_y < s_y + s_h:
                        self.sliderDrag = slider
                        break
                for button in self.button_list:
                    s_x, s_y, s_w, s_h = button.dim
                    if s_x <= mouse_x < s_x + s_w and s_y <= mouse_y < s_y + s_h:
                        button.click()
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.sliderDrag is not None:
                    self.sliderDrag.updateVal()
                    self.sliderDrag = None

    def drawMenu(self):
        self.screen.blit(self.background_pic, (0, 0))
        self.drawMenuText()
        self.drawPreviews()
        display_all_graphs(self.screen, self.sim, self)
        self.drawSlidersAndButtons()
        self.displayCreatureMosaic(self.screen)
        self.display_movies(self.screen)

    def displayCreatureMosaic(self, screen):
        time_since_last_press = time.time() - self.showCreaturesButton.last_click_time
        pan_time = 0.2
        frac = bound(time_since_last_press / pan_time)
        panel_y = 0
        if self.mosaic_visible:
            panel_y = self.CM_MARGIN1 - self.mosaicScreen.get_height() * (1 - frac)
            screen.blit(self.mosaicScreen, (self.CM_MARGIN1, panel_y))
        if not self.mosaic_visible and frac < 1:
            self.screen.blit(
                self.mosaicScreen,
                (
                    self.CM_MARGIN1,
                    self.CM_MARGIN1 - self.mosaicScreen.get_height() * frac,
                ),
            )

    def display_movies(self, screen):
        if self.CLH[0] is None:
            return
        if self.CLH[0] == 3:
            num_movie_screens = len(self.movieScreens)
            species_names = [None] * num_movie_screens
            species_colors = [None] * num_movie_screens
            for i in range(num_movie_screens):
                sp = self.creatureHighlight[i].species
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
        gen = self.genSlider.val
        coor = (self.CM_MARGIN1 + self.MS_WC, 0)
        self.screen.blit(self.infoBarScreen, coor)
        if self.CLH[0] == 2:
            self.drawMovieQuad(self.CLH[1])
            return
        self.screen.blit(self.movieScreens[0], coor)
        if self.CLH[0] == 1:
            # TODO: destruct
            dimensions = self.previewLocations[self.CLH[2]]
            self.screen.blit(
                draw_ring_light(dimensions[2], dimensions[3], 6),
                (dimensions[0], dimensions[1]),
            )
        else:
            coor = self.sim.creatures[gen][self.CLH[1]].icon_coor
            x = coor[0] + self.CM_MARGIN1
            y = coor[1] + self.CM_MARGIN1
            self.screen.blit(draw_ring_light(coor[2], coor[3], 6), (x, y))

    def detectSliders(self):
        if self.sliderDrag is not None:
            mouse_x, _ = pygame.mouse.get_pos()
            s_x, _, s_w, _, s_dw = self.sliderDrag.dim
            ratio = bound(((mouse_x - s_dw * 0.5) - s_x) / (s_w - s_dw))

            s_range = self.sliderDrag.val_max - self.sliderDrag.val_min
            self.sliderDrag.tval = ratio * s_range + self.sliderDrag.val_min
            if self.sliderDrag.snap_to_int:
                self.sliderDrag.tval = round(self.sliderDrag.tval)
            if self.sliderDrag.update_live:
                self.sliderDrag.updateVal()

    def drawSlidersAndButtons(self):
        for slider in self.slider_list:
            slider.drawSlider(self.screen)
        for button in self.button_list:
            button.draw_button(self.screen, self.small_font)

    # Button and slider functions
    def updateGenSlider(self, gen):
        self.drawCreatureMosaic(gen)

    def toggleCreatures(self, button):
        self.mosaic_visible = button.setting == 1

    def toggleSort(self, button):
        self.drawCreatureMosaic(self.genSlider.val)

    def toggleStyle(self, button):
        self.drawCreatureMosaic(self.genSlider.val)

    def doNothing(self, button):
        a = 5

    def startSample(self, button):
        if button.setting == 1:
            self.sample_i = 0
            self.startSampleHelper()

    def startSampleHelper(self):
        L = 8
        self.creatureHighlight = []
        self.visualSimMemory = []
        self.movieScreens = []
        self.CLH = [3, 0]
        self.sample_frames = 0
        for i in range(L):
            gen = self.genSlider.val
            c = (self.sample_i + i) % self.sim.c_count
            self.creatureHighlight.append(self.sim.creatures[gen][c])
            self.visualSimMemory.append(self.sim.simulate_import(gen, c, c + 1, True))
            self.movieScreens.append(None)
        self.sample_i += L

    def show(self):
        pygame.display.flip()
