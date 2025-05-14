import time
import random

import numpy as np
from utils import applyMuscles
from jes_creature import Creature
from jes_species_info import SpeciesInfo
from jes_dataviz import draw_all_graphs


class Simulation:
    def __init__(
        self,
        creature_count,
        _stabilization_time,
        _trial_time,
        _beat_time,
        _beat_fade_time,
        _c_dim,
        _beats_per_cycle,
        _node_coor_count,
        _y_clips,
        _ground_friction_coef,
        _gravity_acceleration_coef,
        _calming_friction_coef,
        _typical_friction_coef,
        _muscle_coef,
        _traits_per_box,
        _traits_extra,
        _mutation_rate,
        _big_mutation_rate,
        _units_per_meter,
    ):
        self.creature_count = creature_count
        self.species_count = creature_count
        self.stabilization_time = _stabilization_time
        self.trial_time = _trial_time
        self.beat_time = _beat_time
        self.beat_fade_time = _beat_fade_time
        self.c_dim = _c_dim
        self.CW, self.CH = self.c_dim
        self.beats_per_cycle = _beats_per_cycle
        self.node_coor_count = _node_coor_count
        self.y_clips = _y_clips
        self.ground_friction_coef = _ground_friction_coef
        self.gravity_acceleration_coef = _gravity_acceleration_coef
        self.calming_friction_coef = _calming_friction_coef
        self.typical_friction_coef = _typical_friction_coef
        self.muscle_coef = _muscle_coef

        self.traits_per_box = _traits_per_box
        self.traits_extra = _traits_extra
        self.trait_count = (
            self.CW * self.CH * self.beats_per_cycle * self.traits_per_box
            + self.traits_extra
        )

        self.mutation_rate = _mutation_rate
        self.big_mutation_rate = _big_mutation_rate

        # what proportion of the population does a species need to get a label?
        self.s_visible = 0.05
        # what proportion of the population does a species need to appear in the genealogy?
        self.s_notable = 0.10
        # change this if you want to change the resolution of the percentile-tracking
        self.percentile_base = 100
        self.units_per_meter = _units_per_meter
        self.creatures = None
        self.rankings = np.zeros((0, self.creature_count), dtype=int)
        self.percentiles = np.zeros((0, self.percentile_base + 1))
        self.species_pops = []
        self.species_info = []
        self.prominent_species = []
        self.ui = None
        self.last_gen_run_time = -1

    def initialize_universe(self):
        self.creatures = [[None] * self.creature_count]
        for c in range(self.creature_count):
            self.creatures[0][c] = self.create_new_creature(c)
            self.species_info.append(SpeciesInfo(self, self.creatures[0][c], None))

        # We want to make sure that all creatures, even in their
        # initial state, are in calm equilibrium. They shouldn't
        # be holding onto potential energy (e.g. compressed springs)
        # Calm the creatures down so no potential energy is stored
        self.get_calm_states(0, 0, self.creature_count, self.stabilization_time)

        for c in range(self.creature_count):
            for i in range(2):
                self.creatures[0][c].icons[i] = self.creatures[0][c].draw_icon(
                    self.ui.icon_dimension[i], self.ui.mosaic_color, self.beat_fade_time
                )

        self.ui.draw_creature_mosaic(0)

    def create_new_creature(self, id):
        dna = np.clip(np.random.normal(0.0, 1.0, self.trait_count), -3, 3)
        return Creature(dna, id, -1, self, self.ui)

    def get_calm_states(self, gen, start_idx, end_idx, frame_count):
        param = self.simulate_import(gen, start_idx, end_idx, False)
        node_coords, _, _ = self.simulate_run(param, frame_count, True)
        for c in range(self.creature_count):
            self.creatures[gen][c].save_calm_state(node_coords[c])

    def get_starting_node_coords(self, gen, start_idx, end_idx, from_calm_state):
        count = end_idx - start_idx
        node_coords = np.zeros((count, self.CH + 1, self.CW + 1, self.node_coor_count))
        if not from_calm_state or self.creatures[gen][0].calm_state is None:
            # create grid of nodes along perfect gridlines
            coordinate_grid = np.mgrid[0 : self.CW + 1, 0 : self.CH + 1]
            coordinate_grid = np.swapaxes(np.swapaxes(coordinate_grid, 0, 1), 1, 2)
            node_coords[:, :, :, 0:2] = coordinate_grid
        else:
            # load calm state into node_coords
            for c in range(start_idx, end_idx):
                node_coords[c - start_idx, :, :, :] = self.creatures[gen][c].calm_state
                # lift the creature above ground level
                node_coords[c - start_idx, :, :, 1] -= self.CH
        return node_coords

    def get_muscle_array(self, gen, start_idx, end_idx):
        count = end_idx - start_idx
        # Add one trait for diagonal length.
        m = np.zeros(
            (count, self.CH, self.CW, self.beats_per_cycle, self.traits_per_box + 1)
        )
        dna_length = self.CH * self.CW * self.beats_per_cycle * self.traits_per_box
        for c in range(start_idx, end_idx):
            dna = (
                self.creatures[gen][c]
                .dna[0:dna_length]
                .reshape(self.CH, self.CW, self.beats_per_cycle, self.traits_per_box)
            )
            m[c - start_idx, :, :, :, : self.traits_per_box] = 1.0 + (dna) / 3.0
        # Set diagonal tendons
        m[:, :, :, :, 3] = np.sqrt(
            np.square(m[:, :, :, :, 0]) + np.square(m[:, :, :, :, 1])
        )
        return m

    def simulate_import(self, gen, start_idx, end_idx, from_calm_state):
        node_coords = self.get_starting_node_coords(
            gen, start_idx, end_idx, from_calm_state
        )
        muscles = self.get_muscle_array(gen, start_idx, end_idx)
        current_frame = 0
        return node_coords, muscles, current_frame

    def frame_to_beat(self, f):
        return (f // self.beat_time) % self.beats_per_cycle

    def frame_to_beat_fade(self, f):
        prog = f % self.beat_time
        return min(prog / self.beat_fade_time, 1)

    def simulate_run(self, param, frame_count, calming_run):
        node_coords, muscles, start_current_frame = param
        friction = (
            self.calming_friction_coef if calming_run else self.typical_friction_coef
        )
        ceiling_y = self.y_clips[0]
        floor_y = self.y_clips[1]

        for f in range(frame_count):
            current_frame = start_current_frame + f
            beat = 0

            if not calming_run:
                beat = self.frame_to_beat(current_frame)
                # decrease y-velo (3rd node coor) by G
                node_coords[:, :, :, 3] += self.gravity_acceleration_coef

            applyMuscles(node_coords, muscles[:, :, :, beat, :], self.muscle_coef)
            node_coords[:, :, :, 2:4] *= friction
            # all node's x and y coordinates are adjusted by velocity_x and velocity_y
            node_coords[:, :, :, 0:2] += node_coords[:, :, :, 2:4]

            # dealing with collision with the ground.
            if not calming_run:
                nodes_touching_ground = np.ma.masked_where(
                    node_coords[:, :, :, 1] >= floor_y, node_coords[:, :, :, 1]
                )
                # mask that only countains 1's where nodes touch the floor
                m = nodes_touching_ground.mask.astype(float)
                pressure = node_coords[:, :, :, 1] - floor_y
                ground_friction_multiplier = 0.5 ** (
                    m * pressure * self.ground_friction_coef
                )

                # clip nodes below the ground back to ground level
                node_coords[:, :, :, 1] = np.clip(
                    node_coords[:, :, :, 1], ceiling_y, floor_y
                )
                # any nodes touching the ground must be slowed down by ground friction.
                node_coords[:, :, :, 2] *= ground_friction_multiplier

        # If it's a calming run, then take the average location of all nodes to center it at the origin.
        if calming_run:
            node_coords[:, :, :, 0] -= np.mean(
                node_coords[:, :, :, 0], axis=(1, 2), keepdims=True
            )
        return node_coords, muscles, start_current_frame + frame_count

    def do_species_info(self, new_species_populations, best_of_each_species):
        new_species_populations = dict(sorted(new_species_populations.items()))
        running = 0
        for sp, val in new_species_populations.items():
            pop = val[0]
            val[1] = running
            val[2] = running + pop
            running += pop

            info = self.species_info[sp]
            info.reps[3] = best_of_each_species[sp]  # most-recent representative
            if pop > info.apex_pop:  # This species reached its highest population
                info.apex_pop = pop
                info.reps[2] = best_of_each_species[sp]  # apex representative

            # prominent threshold
            if pop >= self.creature_count * self.s_notable and not info.prominent:
                info.become_prominent()

    def check_alap(self):
        if self.ui.alap_button.setting == 1:  # We're already ALAP-ing!
            self.simulate_generation(self.ui.do_generation_button)

    def simulate_generation(self, _button):
        # calculates how long each generation takes to run
        generation_start_time = time.monotonic()

        gen = len(self.creatures) - 1
        creature_state = self.simulate_import(gen, 0, self.creature_count, True)
        node_coords, _, _ = self.simulate_run(creature_state, self.trial_time, False)
        # find each creature's average X-coordinate
        final_scores = node_coords[:, :, :, 0].mean(axis=(1, 2))

        # Tallying up all the data
        current_rankings = np.flip(np.argsort(final_scores), axis=0)
        new_percentiles = np.zeros((self.percentile_base + 1))
        new_species_populations = {}
        best_of_each_species = {}
        for rank in range(self.creature_count):
            c = current_rankings[rank]
            self.creatures[gen][c].fitness = final_scores[c]
            self.creatures[gen][c].rank = rank

            species = self.creatures[gen][c].species
            if species in new_species_populations:
                new_species_populations[species][0] += 1
            else:
                new_species_populations[species] = [1, None, None]
            if species not in best_of_each_species:
                best_of_each_species[species] = self.creatures[gen][c].id
        self.do_species_info(new_species_populations, best_of_each_species)

        for percentile in range(self.percentile_base + 1):
            rank = min(
                int(self.creature_count * percentile / self.percentile_base),
                self.creature_count - 1,
            )
            c = current_rankings[rank]
            new_percentiles[percentile] = self.creatures[gen][c].fitness

        next_creatures = [None] * self.creature_count
        for rank in range(self.creature_count // 2):
            winner = current_rankings[rank]
            loser = current_rankings[(self.creature_count - 1) - rank]
            if random.uniform(0, 1) < rank / self.creature_count:
                loser, winner = winner, loser
            next_creatures[winner] = None
            # A 1st place finisher is guaranteed to make a clone, but as we get
            # closer to the middle the odds get more likely we just get 2 mutants.
            if random.uniform(0, 1) < rank / self.creature_count * 2.0:
                next_creatures[winner] = self.mutate(
                    self.creatures[gen][winner],
                    (gen + 1) * self.creature_count + winner,
                )
            else:
                next_creatures[winner] = self.clone(
                    self.creatures[gen][winner],
                    (gen + 1) * self.creature_count + winner,
                )
            next_creatures[loser] = self.mutate(
                self.creatures[gen][winner], (gen + 1) * self.creature_count + loser
            )
            self.creatures[gen][loser].living = False

        self.creatures.append(next_creatures)
        self.rankings = np.append(
            self.rankings, current_rankings.reshape((1, self.creature_count)), axis=0
        )
        self.percentiles = np.append(
            self.percentiles,
            new_percentiles.reshape((1, self.percentile_base + 1)),
            axis=0,
        )
        self.species_pops.append(new_species_populations)

        draw_all_graphs(self, self.ui)

        self.get_calm_states(gen + 1, 0, self.creature_count, self.stabilization_time)
        # Calm the creatures down so no potential energy is stored
        for c in range(self.creature_count):
            for i in range(2):
                self.creatures[gen + 1][c].icons[i] = self.creatures[gen + 1][
                    c
                ].draw_icon(
                    self.ui.icon_dimension[i], self.ui.mosaic_color, self.beat_fade_time
                )

        self.ui.generation_slider.val_max = gen + 1
        self.ui.generation_slider.manual_update(gen)
        self.last_gen_run_time = time.monotonic() - generation_start_time

        self.ui.detect_mouse_motion()

    def get_create_with_id(self, _id):
        return self.creatures[_id // self.creature_count][_id % self.creature_count]

    def clone(self, parent, new_id):
        return Creature(parent.dna, new_id, parent.species, self, self.ui)

    def mutate(self, parent, new_id):
        new_dna, new_species, cwc = parent.get_mutated_dna(self)
        new_creature = Creature(new_dna, new_id, new_species, self, self.ui)
        if new_creature.species != parent.species:
            self.species_info.append(SpeciesInfo(self, new_creature, parent))
            new_creature.codon_with_change = cwc
        return new_creature
