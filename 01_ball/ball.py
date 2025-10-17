import pygame
import sys
import random
import math
import itertools


"""
TODO
1. Wiele piłek DONE
2. "Sterowanie" myszką (przycisk->podbicie) DONE
3. Dodatkowe przeszkody - dodatkowe
4. Opory (powietrza/przy odbiciu) DONE
5. Odbicia między piłeczkami - dodatkowe DONE
"""


# --- konfiguracja okna ---
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cannonball")
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
GRAVITY = pygame.Vector2(0.0, -10.0)
TIME_STEP = 1.0 / 60.0
DRAG = 0.005
BOUNCE_DRAG = 0.05
COLLISION_DRAG = 0.01


def random_color():
    levels = range(32,256,32)
    return tuple(random.choice(levels) for _ in range(3))

class Ball:
    def __init__(self):
        self.radius = random.uniform(0.2, 1.0)
        self.position = pygame.Vector2(random.uniform(1.0, sim_width-1.0), random.uniform(1.0, sim_height-1.0))
        self.old_position = self.position
        self.velocity = pygame.Vector2(random.uniform(-15,15), random.uniform(-15,15))
        self.color = random_color()
        self.mass = self.radius**3
        self.energy = self.velocity.length_squared()/2 - GRAVITY.y * self.position.y

    def update(self):
        self.count_step()
        self.count_energy()
        self.bounce()
        self.drag()

    def count_step(self):
        self.old_position = self.position
        new_vel = self.velocity + GRAVITY * TIME_STEP
        self.position += (self.velocity + new_vel) * TIME_STEP / 2
        self.velocity = new_vel

    def count_energy(self):
        self.energy = self.velocity.length_squared()/2 - GRAVITY.y * self.position.y


    def bounce(self):
        if math.fabs(self.position.y) < self.radius * 1.1 and math.fabs(self.velocity.y) < 0.1 :
            self.position.y = self.radius
            self.velocity.y = 0
            self.velocity *= (1-BOUNCE_DRAG)

        elif self.position.y <= self.radius:
            self.position.y = self.radius
            vel_y_squared = (self.energy + GRAVITY.y * self.position.y) * 2 - self.velocity.x**2 if (self.energy + GRAVITY.y * self.position.y) * 2 - self.velocity.x**2 >= 0 else 0
            self.velocity.y = math.sqrt( vel_y_squared )
            self.velocity *= (1-BOUNCE_DRAG)

        if self.position.x <= self.radius:
            self.velocity *= (1-BOUNCE_DRAG)
            self.position.x = -self.position.x + 2*self.radius
            self.velocity.x = -self.velocity.x

        elif self.position.x >= sim_width - self.radius:
            self.velocity *= (1-BOUNCE_DRAG)
            self.position.x = -self.position.x + 2*(sim_width - self.radius)
            self.velocity.x = -self.velocity.x

    def drag(self):
        self.velocity -= DRAG * self.velocity / self.radius

    def undo(self):
        self.position = self.old_position

def collision(first: Ball, second: Ball):
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

        first.undo()
        first.update()
        
        vec = first.position - second.position
        overlap = (first.radius + second.radius) - vec.length()
        if overlap > 0:
            correction = overlap / 2 * vec.normalize()
            first.position += correction
            second.position -= correction

        first.velocity *= (1-COLLISION_DRAG)
        second.velocity *= (1-COLLISION_DRAG)


class Balls:
    def __init__(self, number = 10):
        self.balls = [ Ball() for _ in range(number) ]

    def bust(self, direction):
        for ball in self.balls:
            ball.velocity += direction

    def update(self):
        screen.fill((255, 255, 255))
        for i, ball in enumerate(self.balls):
            ball.update()
            self.balls_collide(i)
            pygame.draw.circle(
                screen,
                ball.color,
                (cX(ball.position.x), cY(ball.position.y)),
                int(c_scale * ball.radius)
            )

    def balls_collide(self, num):
        for i in range(num + 1, len(self.balls)):
            collision(self.balls[num], self.balls[i])

    def check_bust(self, key):
        if key == pygame.K_LEFT:
            self.bust(pygame.Vector2(-10,0))
        elif key == pygame.K_RIGHT:
            self.bust(pygame.Vector2(10,0))
        elif key == pygame.K_UP:
            self.bust(pygame.Vector2(0,10))
        elif key == pygame.K_DOWN:
            self.bust(pygame.Vector2(0,-10))




balls = Balls()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            balls.check_bust(event.key)

    balls.update()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

