import time
import pygame
from jes_shapes import center_text


class Button:
    def __init__(self, ui, pdim, pnames, pfunc) -> None:
        self.dim = pdim  # Dim is a list of 4 parameters: x, y, width, height
        self.names = pnames
        self.setting = 0
        self.last_click_time: float = 0
        self.func = pfunc
        ui.button_list.append(self)

    def draw_button(self, screen, font) -> None:
        x, y, w, h = self.dim
        name = self.names[self.setting]

        slider_surface = pygame.Surface((w, h), pygame.SRCALPHA, 32)
        slider_surface.fill((30, 150, 230))
        if name == "Turn off ALAP" or name.endswith("Stop") or name.endswith("Hide"):
            slider_surface.fill((128, 255, 255))
        center_text(slider_surface, name, w / 2, h / 2, (0, 0, 0), font)

        screen.blit(slider_surface, (x, y))

    def click(self) -> None:
        self.setting = (self.setting + 1) % len(self.names)
        self.last_click_time = time.monotonic()
        self.func(self)
