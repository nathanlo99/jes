import numpy as np
import math


class SpeciesInfo:
    def __init__(self, _sim, me, parent):
        self.sim = _sim
        self.species_id = me.species
        self.parent_species = None
        self.level = 0
        if parent is not None:
            self.parent_species = parent.species
            self.level = self.sim.species_info[parent.species].level + 1

        self.apex_pop = 0
        self.reign = []
        # Representative ancestor, first, apex, and last creatures of this species.
        self.reps = np.zeros(4, dtype=int)
        self.prominent = False

        if parent is not None:
            self.reps[0] = parent.id
        self.reps[1] = me.id
        self.coor = None

    # if you are prominent, all your ancestors become prominent.
    def become_prominent(self):
        self.prominent = True
        self.insert_into_prominent_species_list()
        if self.parent_species is not None:
            ancestor = self.sim.species_info[self.parent_species]
            if not ancestor.prominent:
                ancestor.become_prominent()

    def insert_into_prominent_species_list(self):
        p = self.sim.prominent_species
        # this level doesn't exist yet. Add new levels of the genealogy tree to acommodate you
        while len(p) <= self.level:
            p.append([])
        pL = p[self.level]
        insert_index = 0
        # inefficient sorting thing, but there are <50 species so who cares
        for index, other in enumerate(pL):
            ancestor_compare = (
                0
                if self.level == 0
                else self.sim.species_info[other].parent_species - self.parent_species
            )
            if ancestor_compare == 0:  # siblings
                if other < self.species_id:
                    insert_index = index + 1
            else:  # not siblings trick to avoid family trees tangling (all siblings should be adjacent)
                if ancestor_compare < 0:
                    insert_index = index + 1
        pL.insert(insert_index, self.species_id)

    def get_when(self, index):
        return math.floor(self.reps[index] // self.sim.creature_count)

    def get_performance(self, sim, index):
        gen = math.floor(self.reps[index] // self.sim.creature_count)
        c = self.reps[index] % self.sim.creature_count
        creature = sim.creatures[gen][c]
        return creature.fitness
