#!/usr/bin/env python

from jes_sim import Simulation
from jes_ui import UI

creature_count = int(
    input(
        """
How many creatures do you want?
100: Lightweight
250: Standard (if you don't type anything, I'll go with this)
500: Strenuous (this is what my carykh video used)
"""
    )
    or "250"
)

# Simulation

sim = Simulation(
    creature_count=creature_count,
    _stabilization_time=200,
    _trial_time=300,
    _beat_time=20,
    _beat_fade_time=5,
    _c_dim=[4, 4],
    _beats_per_cycle=3,
    _node_coor_count=4,  # x_position, y_position, x_velocity, y_velocity
    _y_clips=[-10000000, 0],
    _ground_friction_coef=25,
    _gravity_acceleration_coef=0.002,
    _calming_friction_coef=0.7,
    _typical_friction_coef=0.8,
    _muscle_coef=0.08,
    _traits_per_box=3,  # desired width, desired height, rigidity
    _traits_extra=1,  # heartbeat (time)
    _mutation_rate=0.07,
    _big_mutation_rate=0.025,
    _units_per_meter=0.05,
)

# Cosmetic UI variables
ui = UI(
    window_width=1920,
    window_height=1078,
    _movie_single_dimension=(650, 650),
    _graph_coor=(850, 50, 900, 500),
    _sac_coor=(850, 560, 900, 300),
    _geneology_coor=(20, 105, 530, 802, 42),
    _column_margin=330,
    _mosaic_dim=[10, 24, 24, 30],  # _MOSAIC_DIM=[10,10,17,22],
    _menu_text_up=180,
    _cm_margin1=20,
    _cm_margin2=1,
)

sim.ui = ui
ui.sim = sim
ui.add_buttons_and_sliders()

sim.initialize_universe()
while ui.running:
    sim.check_alap()
    ui.detect_mouse_motion()
    ui.detectEvents()
    ui.detectSliders()
    ui.doMovies()
    ui.drawMenu()
    ui.show()
