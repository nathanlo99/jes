#!/usr/bin/env python

from jes_sim import Simulation
from jes_ui import UI


def main() -> None:
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

    sim = Simulation(
        creature_count=creature_count,
        stabilization_time=200,
        trial_time=300,
        beat_time=20,
        beat_fade_time=5,
        creature_dimensions=[4, 4],
        beats_per_cycle=3,
        node_coord_size=4,  # x_position, y_position, x_velocity, y_velocity
        y_clips=[-10000000, 0],
        ground_friction_coefficient=25,
        gravity_acceleration_coeff=0.002,
        calming_friction_coeff=0.7,
        typical_friction_coeff=0.8,
        muscle_coeff=0.08,
        traits_per_box=3,  # desired width, desired height, rigidity
        traits_extra=1,  # heartbeat (time)
        mutation_rate=0.07,
        big_mutation_rate=0.025,
        units_per_meter=0.05,
    )

    ui = UI(
        window_width=1920,
        window_height=1078,
        movie_single_dimension=(650, 650),
        graph_coords=(850, 50, 900, 500),
        label_coords=(850, 560, 900, 300),
        ancestry_tree_coords=(20, 105, 530, 802, 42),
        column_margin=330,
        mosaic_dim=[10, 24, 24, 30],  # _MOSAIC_DIM=[10,10,17,22],
        menu_text_up=180,
        cm_margin1=20,
        cm_margin2=1,
    )

    sim.ui = ui
    ui.sim = sim
    ui.add_buttons_and_sliders()

    sim.initialize_universe()
    while ui.running:
        sim.check_alap()
        ui.detect_mouse_motion()
        ui.detect_events()
        ui.detect_sliders()
        ui.do_movies()
        ui.draw_menu()
        ui.show()


if __name__ == "__main__":
    main()
