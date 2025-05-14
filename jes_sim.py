import time
import random

import numpy as np
from utils import applyMuscles
from jes_creature import Creature
from jes_species_info import SpeciesInfo
from jes_dataviz import drawAllGraphs


class Sim:
    def __init__(
        self,
        _c_count,
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
        _UNITS_PER_METER,
    ):
        self.c_count = _c_count  # creature count
        self.species_count = _c_count  # species count
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

        self.S_VISIBLE = 0.05  # what proportion of the population does a species need to appear on the SAC graph?
        self.S_NOTABLE = 0.10  # what proportion of the population does a species need to appear in the genealogy?
        self.HUNDRED = 100  # change this if you want to change the resolution of the percentile-tracking
        self.UNITS_PER_METER = _UNITS_PER_METER
        self.creatures = None
        self.rankings = np.zeros((0, self.c_count), dtype=int)
        self.percentiles = np.zeros((0, self.HUNDRED + 1))
        self.species_pops = []
        self.species_info = []
        self.prominent_species = []
        self.ui = None
        self.last_gen_run_time = -1

    def initializeUniverse(self):
        self.creatures = [[None] * self.c_count]
        for c in range(self.c_count):
            self.creatures[0][c] = self.createNewCreature(c)
            self.species_info.append(SpeciesInfo(self, self.creatures[0][c], None))

        # We want to make sure that all creatures, even in their
        # initial state, are in calm equilibrium. They shouldn't
        # be holding onto potential energy (e.g. compressed springs)
        self.getCalmStates(
            0, 0, self.c_count, self.stabilization_time, True
        )  # Calm the creatures down so no potential energy is stored

        for c in range(self.c_count):
            for i in range(2):
                self.creatures[0][c].icons[i] = self.creatures[0][c].draw_icon(
                    self.ui.ICON_DIM[i], self.ui.MOSAIC_COLOR, self.beat_fade_time
                )

        self.ui.drawCreatureMosaic(0)

    def createNewCreature(self, id):
        dna = np.clip(np.random.normal(0.0, 1.0, self.trait_count), -3, 3)
        return Creature(dna, id, -1, self, self.ui)

    def getCalmStates(self, gen, start_idx, end_idx, frameCount, calmingRun):
        param = self.simulate_import(gen, start_idx, end_idx, False)
        nodeCoor, muscles, _ = self.simulate_run(param, frameCount, True)
        for c in range(self.c_count):
            self.creatures[gen][c].save_calm_state(nodeCoor[c])

    def getStartingNodeCoor(self, gen, start_idx, end_idx, from_calm_state):
        COUNT = end_idx - start_idx
        n = np.zeros((COUNT, self.CH + 1, self.CW + 1, self.node_coor_count))
        if not from_calm_state or self.creatures[gen][0].calm_state is None:
            # create grid of nodes along perfect gridlines
            coorGrid = np.mgrid[0 : self.CW + 1, 0 : self.CH + 1]
            coorGrid = np.swapaxes(np.swapaxes(coorGrid, 0, 1), 1, 2)
            n[:, :, :, 0:2] = coorGrid
        else:
            # load calm state into nodeCoor
            for c in range(start_idx, end_idx):
                n[c - start_idx, :, :, :] = self.creatures[gen][c].calm_state
                n[
                    c - start_idx, :, :, 1
                ] -= self.CH  # lift the creature above ground level
        return n

    def getMuscleArray(self, gen, start_idx, end_idx):
        COUNT = end_idx - start_idx
        m = np.zeros(
            (COUNT, self.CH, self.CW, self.beats_per_cycle, self.traits_per_box + 1)
        )  # add one trait for diagonal length.
        DNA_LEN = self.CH * self.CW * self.beats_per_cycle * self.traits_per_box
        for c in range(start_idx, end_idx):
            dna = (
                self.creatures[gen][c]
                .dna[0:DNA_LEN]
                .reshape(self.CH, self.CW, self.beats_per_cycle, self.traits_per_box)
            )
            m[c - start_idx, :, :, :, : self.traits_per_box] = 1.0 + (dna) / 3.0
        m[:, :, :, :, 3] = np.sqrt(
            np.square(m[:, :, :, :, 0]) + np.square(m[:, :, :, :, 1])
        )  # Set diagonal tendons
        return m

    def simulate_import(self, gen, start_idx, end_idx, from_calm_state):
        nodeCoor = self.getStartingNodeCoor(gen, start_idx, end_idx, from_calm_state)
        muscles = self.getMuscleArray(gen, start_idx, end_idx)
        currentFrame = 0
        return nodeCoor, muscles, currentFrame

    def frame_to_beat(self, f):
        return (f // self.beat_time) % self.beats_per_cycle

    def frame_to_beat_fade(self, f):
        prog = f % self.beat_time
        return min(prog / self.beat_fade_time, 1)

    def simulate_run(self, param, frameCount, calmingRun):
        nodeCoor, muscles, startCurrentFrame = param
        friction = (
            self.calming_friction_coef if calmingRun else self.typical_friction_coef
        )
        CEILING_Y = self.y_clips[0]
        FLOOR_Y = self.y_clips[1]

        for f in range(frameCount):
            currentFrame = startCurrentFrame + f
            beat = 0

            if not calmingRun:
                beat = self.frame_to_beat(currentFrame)
                nodeCoor[:, :, :, 3] += self.gravity_acceleration_coef
                # decrease y-velo (3rd node coor) by G
            applyMuscles(nodeCoor, muscles[:, :, :, beat, :], self.muscle_coef)
            nodeCoor[:, :, :, 2:4] *= friction
            nodeCoor[:, :, :, 0:2] += nodeCoor[
                :, :, :, 2:4
            ]  # all node's x and y coordinates are adjusted by velocity_x and velocity_y

            if not calmingRun:  # dealing with collision with the ground.
                nodesTouchingGround = np.ma.masked_where(
                    nodeCoor[:, :, :, 1] >= FLOOR_Y, nodeCoor[:, :, :, 1]
                )
                m = nodesTouchingGround.mask.astype(
                    float
                )  # mask that only countains 1's where nodes touch the floor
                pressure = nodeCoor[:, :, :, 1] - FLOOR_Y
                groundFrictionMultiplier = 0.5 ** (
                    m * pressure * self.ground_friction_coef
                )

                nodeCoor[:, :, :, 1] = np.clip(
                    nodeCoor[:, :, :, 1], CEILING_Y, FLOOR_Y
                )  # clip nodes below the ground back to ground level
                nodeCoor[
                    :, :, :, 2
                ] *= groundFrictionMultiplier  # any nodes touching the ground must be slowed down by ground friction.

        if (
            calmingRun
        ):  # If it's a calming run, then take the average location of all nodes to center it at the origin.
            nodeCoor[:, :, :, 0] -= np.mean(
                nodeCoor[:, :, :, 0], axis=(1, 2), keepdims=True
            )
        return nodeCoor, muscles, startCurrentFrame + frameCount

    def doSpeciesInfo(self, nsp, best_of_each_species):
        nsp = dict(sorted(nsp.items()))
        running = 0
        for sp in nsp.keys():
            pop = nsp[sp][0]
            nsp[sp][1] = running
            nsp[sp][2] = running + pop
            running += pop

            info = self.species_info[sp]
            info.reps[3] = best_of_each_species[sp]  # most-recent representative
            if pop > info.apex_pop:  # This species reached its highest population
                info.apex_pop = pop
                info.reps[2] = best_of_each_species[sp]  # apex representative
            if (
                pop >= self.c_count * self.S_NOTABLE and not info.prominent
            ):  # prominent threshold
                info.becomeProminent()

    def checkALAP(self):
        if self.ui.ALAPButton.setting == 1:  # We're already ALAP-ing!
            self.doGeneration(self.ui.doGenButton)

    def doGeneration(self, button):
        generation_start_time = (
            time.time()
        )  # calculates how long each generation takes to run

        gen = len(self.creatures) - 1
        creatureState = self.simulate_import(gen, 0, self.c_count, True)
        nodeCoor, muscles, _ = self.simulate_run(creatureState, self.trial_time, False)
        finalScores = nodeCoor[:, :, :, 0].mean(
            axis=(1, 2)
        )  # find each creature's average X-coordinate

        # Tallying up all the data
        currRankings = np.flip(np.argsort(finalScores), axis=0)
        newPercentiles = np.zeros((self.HUNDRED + 1))
        newSpeciesPops = {}
        best_of_each_species = {}
        for rank in range(self.c_count):
            c = currRankings[rank]
            self.creatures[gen][c].fitness = finalScores[c]
            self.creatures[gen][c].rank = rank

            species = self.creatures[gen][c].species
            if species in newSpeciesPops:
                newSpeciesPops[species][0] += 1
            else:
                newSpeciesPops[species] = [1, None, None]
            if species not in best_of_each_species:
                best_of_each_species[species] = self.creatures[gen][c].id
        self.doSpeciesInfo(newSpeciesPops, best_of_each_species)

        for p in range(self.HUNDRED + 1):
            rank = min(int(self.c_count * p / self.HUNDRED), self.c_count - 1)
            c = currRankings[rank]
            newPercentiles[p] = self.creatures[gen][c].fitness

        next_creatures = [None] * self.c_count
        for rank in range(self.c_count // 2):
            winner = currRankings[rank]
            loser = currRankings[(self.c_count - 1) - rank]
            if random.uniform(0, 1) < rank / self.c_count:
                ph = loser
                loser = winner
                winner = ph
            next_creatures[winner] = None
            # A 1st place finisher is guaranteed to make a clone, but as we get closer to the middle the odds get more likely we just get 2 mutants.
            if random.uniform(0, 1) < rank / self.c_count * 2.0:
                next_creatures[winner] = self.mutate(
                    self.creatures[gen][winner], (gen + 1) * self.c_count + winner
                )
            else:
                next_creatures[winner] = self.clone(
                    self.creatures[gen][winner], (gen + 1) * self.c_count + winner
                )
            next_creatures[loser] = self.mutate(
                self.creatures[gen][winner], (gen + 1) * self.c_count + loser
            )
            self.creatures[gen][loser].living = False

        self.creatures.append(next_creatures)
        self.rankings = np.append(
            self.rankings, currRankings.reshape((1, self.c_count)), axis=0
        )
        self.percentiles = np.append(
            self.percentiles, newPercentiles.reshape((1, self.HUNDRED + 1)), axis=0
        )
        self.species_pops.append(newSpeciesPops)

        drawAllGraphs(self, self.ui)

        self.getCalmStates(gen + 1, 0, self.c_count, self.stabilization_time, True)
        # Calm the creatures down so no potential energy is stored
        for c in range(self.c_count):
            for i in range(2):
                self.creatures[gen + 1][c].icons[i] = self.creatures[gen + 1][
                    c
                ].draw_icon(
                    self.ui.ICON_DIM[i], self.ui.MOSAIC_COLOR, self.beat_fade_time
                )

        self.ui.genSlider.val_max = gen + 1
        self.ui.genSlider.manualUpdate(gen)
        self.last_gen_run_time = time.time() - generation_start_time

        self.ui.detectMouseMotion()

    def get_create_with_id(self, _id):
        return self.creatures[_id // self.c_count][_id % self.c_count]

    def clone(self, parent, new_id):
        return Creature(parent.dna, new_id, parent.species, self, self.ui)

    def mutate(self, parent, new_id):
        new_dna, new_species, cwc = parent.get_mutated_dna(self)
        new_creature = Creature(new_dna, new_id, new_species, self, self.ui)
        if new_creature.species != parent.species:
            self.species_info.append(SpeciesInfo(self, new_creature, parent))
            new_creature.codon_with_change = cwc
        return new_creature
