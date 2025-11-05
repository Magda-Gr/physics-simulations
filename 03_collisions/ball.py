from ursina import *
from ursina.shaders import lit_with_shadows_shader

Entity.default_shader = lit_with_shadows_shader

TIME_STEP = 1.0 / 60.0
DEPTH = 2.0
MAX_RADIUS = 0.1
MIN_RADIUS = 0.05

class Ball(Entity):
    def __init__(self):
        super().__init__(model='sphere')
        self._radius = random.uniform(MIN_RADIUS, MAX_RADIUS)
        self.scale = 2*self._radius
        self.color = color.blue
        self.position = Vec3(random.uniform(window.left.x+MAX_RADIUS, window.right.x-MAX_RADIUS), random.uniform(window.bottom.y+MAX_RADIUS, window.top.y-MAX_RADIUS), random.uniform(MAX_RADIUS, DEPTH-MAX_RADIUS))
        self._velocity = Vec3(random.uniform(-1,1), random.uniform(-1,1), random.uniform(-1,1))

    def left(self):
        return self.x - self._radius
    
    def right(self):
        return self.x + self._radius
    
    def top(self):
        return self.y + self._radius
    
    def bottom(self):
        return self.y - self._radius
    
    def front(self):
        return self.z - self._radius
    
    def minimum(self):
        return Vec3(self.left(), self.bottom(), self.front())
    
    def maximum(self):
        return Vec3(self.right(), self.top(), self.back())
    
    def back(self):
        return self.z + self._radius
    
    def get_radius(self):
        return self._radius
    
    def collision(self):
        self.color = color.red

    def reset_collision(self):
        self.color = color.blue

    def collided(self):
        return self.color == color.red

    def update(self):
        self._count_step()
        self._bounce()
    
    def _count_step(self):
        self.old_position = self.position
        self.position += self._velocity * TIME_STEP

    def _bounce(self):
        if self.y <= window.bottom.y + self._radius:
            self.y = window.bottom.y + self._radius
            self._velocity.y = -self._velocity.y

        elif self.y >= window.top.y - self._radius:
            self.y = window.top.y - self._radius
            self._velocity.y = -self._velocity.y

        if self.x <= window.left.x + self._radius:
            self.x = -self.x + 2*(self._radius + window.left.x)
            self._velocity.x = -self._velocity.x

        elif self.x >= window.right.x - self._radius:
            self.x = -self.x + 2*(window.right.x - self._radius)
            self._velocity.x = -self._velocity.x

        if self.z <= self._radius:
            self.z = -self.z + 2*(self._radius)
            self._velocity.z = -self._velocity.z

        elif self.z >= DEPTH - self._radius:
            self.z = -self.z + 2*(DEPTH - self._radius)
            self._velocity.z = -self._velocity.z



def check_collision(ball_1: Ball, ball_2: Ball):
    r_1 = ball_1.get_radius()
    r_2 = ball_2.get_radius()
    if distance(ball_1, ball_2) < r_1 + r_2:
        ball_1.collision()
        ball_2.collision()