from ursina import *
from ball import Ball
from brute_force import brute_force_collisions
from sweep_and_prune import sweep_and_prune_collisions
from bvh import bvh_collisions

app = Ursina()


class Balls(Entity):
    def __init__(self):
        super().__init__()
        self.brute_force_button = Button(position=window.top_left + (0.1,-0.1), text='brute force', scale=0.1, color=color.green, on_click = self.bfb_click)
        self.sweep_and_prune_button = Button(position=window.top_left + (0.3,-0.1), text='sweep and prune', scale=0.1, color=color.gray, on_click = self.sup_click)
        self.bvh_button = Button(position=window.top_left + (0.5,-0.1), text='bvh', scale=0.1, color=color.gray, on_click = self.bvh_click)
        self.elems = [Ball() for _ in range(100)]
        self.collision = sweep_and_prune_collisions

    def update(self):
        for ball in self.elems:
            ball.update()
        for ball in self.elems:
            ball.reset_collision()
        self.collision(self.elems)
          

    def bfb_click(self):
        self.brute_force_button.color = color.green
        self.sweep_and_prune_button.color = color.gray
        self.bvh_button.color = color.gray
        self.collision = brute_force_collisions

    def sup_click(self):
        self.brute_force_button.color = color.gray
        self.sweep_and_prune_button.color = color.green
        self.bvh_button.color = color.gray
        self.collision = sweep_and_prune_collisions

    def bvh_click(self):
        self.brute_force_button.color = color.gray
        self.sweep_and_prune_button.color = color.gray
        self.bvh_button.color = color.green
        self.collision = bvh_collisions



spheres = Balls()

camera.position = (0,0,-3)
app.run()

