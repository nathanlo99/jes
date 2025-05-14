import pygame


class Slider:
    def __init__(
        self,
        ui,
        dim,
        val,
        val_min,
        val_max,
        snap_to_int: bool,
        update_live: bool,
        update_function,
    ) -> None:
        # Dim is a list of 5 parameters: x, y, width, height, draggable_width
        self.dim = dim
        self.val = val
        self.val_min = val_min
        self.val_max = val_max
        self.tval = self.val
        self.snap_to_int = snap_to_int
        self.update_live = update_live
        self.update_function = update_function
        ui.slider_list.append(self)

    def draw_slider(self, screen):
        x, y, w, h, dw = self.dim
        ratio = (self.tval - self.val_min) / self.get_length()
        slider_surface = pygame.Surface((w, h), pygame.SRCALPHA, 32)
        slider_surface.fill((80, 80, 80))
        pygame.draw.rect(slider_surface, (230, 230, 230), (ratio * (w - dw), 0, dw, h))
        screen.blit(slider_surface, (x, y))

    def get_length(self):
        return max(self.val_max - self.val_min, 1)

    def set_value(self):
        if self.tval != self.val:
            self.val = self.tval
            self.update_function(self.val)

    def manual_update(self, val):
        self.tval = val
        self.set_value()
        self.update_function(self.val)
