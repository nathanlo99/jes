import numpy as np
import math


class SpeciesInfo:
    def __init__(self, simulation, species, parent):
        self.simulation = simulation
        self.species_id = species.species
        self.parent_species = None
        self.level = 0
        if parent is not None:
            self.parent_species = parent.species
            self.level = self.simulation.species_info[parent.species].level + 1

        self.apex_pop = 0
        self.reign = []
        # Representative ancestor, first, apex, and last creatures of this species.
        self.representatives = np.zeros(4, dtype=int)
        self.prominent = False

        if parent is not None:
            self.representatives[0] = parent.id
        self.representatives[1] = species.id
        self.coords = None

    # if you are prominent, all your ancestors become prominent.
    def become_prominent(self):
        self.prominent = True
        self.insert_into_prominent_species_list()
        if self.parent_species is not None:
            ancestor = self.simulation.species_info[self.parent_species]
            if not ancestor.prominent:
                ancestor.become_prominent()

    def insert_into_prominent_species_list(self):
        prominent_species = self.simulation.prominent_species
        # this level doesn't exist yet. Add new levels of the genealogy tree to acommodate you
        while len(prominent_species) <= self.level:
            prominent_species.append([])
        prominent_species_level = prominent_species[self.level]
        insert_index = 0
        # inefficient sorting thing, but there are <50 species so who cares
        for index, other in enumerate(prominent_species_level):
            ancestor_compare = (
                0
                if self.level == 0
                else self.simulation.species_info[other].parent_species
                - self.parent_species
            )
            if ancestor_compare == 0:  # siblings
                if other < self.species_id:
                    insert_index = index + 1
            else:  # not siblings trick to avoid family trees tangling (all siblings should be adjacent)
                if ancestor_compare < 0:
                    insert_index = index + 1
        prominent_species_level.insert(insert_index, self.species_id)

    def get_when(self, index):
        return math.floor(self.representatives[index] // self.simulation.creature_count)

    def get_performance(self, sim, index):
        gen = math.floor(self.representatives[index] // self.simulation.creature_count)
        c = self.representatives[index] % self.simulation.creature_count
        creature = sim.creatures[gen][c]
        return creature.fitness
