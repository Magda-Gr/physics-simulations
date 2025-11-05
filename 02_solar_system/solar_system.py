import pygame
import sys
import random
import math

"""
TODO
3 pkt:
- jedna kulka na okręgu
4 pkt:
- wiele kulek z kolizjami
5 pkt:
- środek ma masę < inf
- można ją zmieniać
"""

# --- konfiguracja okna ---
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Solar System")
clock = pygame.time.Clock()

# --- skalowanie symulacji ---
sim_min_width = 20.0
c_scale = min(WIDTH, HEIGHT) / sim_min_width
sim_width = WIDTH / c_scale
sim_height = HEIGHT / c_scale

def cX(x):
    return int(x * c_scale)

def cY(y):
    return int(HEIGHT - y * c_scale)

# --- fizyka ---
GRAVITY = pygame.Vector2(0.0, -100.0)
TIME_STEP = 1.0 / 60.0
DRAG = 0.005
COLLISION_DRAG = 0.01


def draw_circle(color, position: pygame.Vector2, radius, width = 0):
    pygame.draw.circle(
    screen,
    color,
    (cX(position.x), cY(position.y)),
    int(c_scale * radius),
    width
    )


class System:
    def __init__(self, number_of_planets = 10, sun_mass = math.inf):
        self.radius = 7.0
        self.sun = Sun(self, sun_mass)
        self.planets = Planets(self, number = number_of_planets)

    def update(self):
        screen.fill((255, 255, 255))
        self.sun.draw_orbit(self.radius)
        self.sun.draw()
        self.planets.update()

    def displacements_of_orbs(self, planet):
        p1 = planet.get_position()
        w1 = 1 / planet.get_mass()
        p2 = self.sun.get_position()
        w2 = 1 / self.sun.get_mass()

        p12 = p1 - p2
        p12_len = p12.length()
        mult = ( p12_len - self.radius ) * p12 / p12_len

        d1 = - w1 / ( w1 + w2 ) * mult
        planet.move(d1)
        d2 = w2 / ( w1 + w2 ) * mult
        self.sun.move(d2)

        planet.calc_velocity()


    def position_in_system(self):
        sun_pos = self.sun.get_position()
        position = pygame.Vector2(random.uniform(0, sim_width), random.uniform(0, sim_height))
        vec = (position - sun_pos).normalize()
        new_position = sun_pos + vec * self.radius
        return new_position



class Orb:
    def get_mass(self):
        return self.mass
    
    def get_position(self):
        return self.position.copy()
    
    def draw(self):
        draw_circle(self.color, self.position, self.radius)

    def move(self, disp):
        self.position += disp


class Sun(Orb):
    def __init__(self, system: System, mass):
        self.system = system
        self.position = pygame.Vector2(sim_width/2, sim_height/2)
        self.radius = 2.0
        self.color = '#FFFF00'
        self.mass = mass

    def draw_orbit(self, radius: pygame.Vector2):
        draw_circle("#000000", self.position, radius, 1)



class Planets:
    def __init__(self, system: System, number = 10):
        self.system = system
        self.planets = [ Planet(self.system.position_in_system()) for _ in range(number) ]

    def update(self):
        for i, planet in enumerate(self.planets):
            planet.count_step()
            self.system.displacements_of_orbs(planet)
            planet.drag()
            self.planets_collide(i)
            planet.draw()


    def planets_collide(self, num):
        for i in range(num + 1, len(self.planets)):
            collision(self.planets[num], self.planets[i])




class Planet(Orb):
    def __init__(self, position):
        self.radius = random.uniform(0.2, 1.0)
        self.position = position
        self.old_position = self.position.copy()
        self.velocity = pygame.Vector2(0,0)
        self.color = random_color()
        self.mass = self.radius**3

    def count_step(self):
        self.old_position = self.position.copy()
        new_vel = self.velocity + GRAVITY * TIME_STEP
        self.position += (self.velocity + new_vel) * TIME_STEP / 2

    def calc_velocity(self):
        self.velocity = (self.position - self.old_position) / TIME_STEP

    def drag(self):
        self.velocity -= DRAG * self.velocity / self.radius

    def colision_drag(self):
        self.velocity -= COLLISION_DRAG * self.velocity / self.radius



def collision(first: Planet, second: Planet):
    if (first.position - second.position).length_squared() < (first.radius + second.radius)**2:

        normal = second.position - first.position
        dist = normal.length()
        if dist == 0:
            return
        
        normal = normal.normalize()

        a1 = first.velocity.dot(normal)
        a2 = second.velocity.dot(normal)

        p = (2 * (a1 - a2)) / (first.mass + second.mass)

        first.velocity = first.velocity - p * second.mass * normal
        second.velocity = second.velocity + p * first.mass * normal
        
        vec = first.position - second.position
        overlap = (first.radius + second.radius) - vec.length()
        if overlap > 0:
            correction = overlap / 2 * vec.normalize()
            first.position += correction
            second.position -= correction

        first.colision_drag()
        second.colision_drag()


def random_color():
    levels = range(32,256,32)
    return tuple(random.choice(levels) for _ in range(3))



system = System(number_of_planets=5, sun_mass=1)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    system.update()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
