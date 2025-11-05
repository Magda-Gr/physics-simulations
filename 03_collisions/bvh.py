from ball import check_collision
from ursina import *
import math

def normalize_coord(val):
        return (val + window.size.x / 2) / window.size.x

def expand_bits(v):
    v = (v * 0x00010001) & 0xFF0000FF
    v = (v * 0x00000101) & 0x0F00F00F
    v = (v * 0x00000011) & 0xC30C30C3
    v = (v * 0x00000005) & 0x49249249
    return v

def calculate_morton_code(position):
    
    x = normalize_coord(position.x)
    y = normalize_coord(position.y)
    z = normalize_coord(position.z)
    
    # Clamp to ensure they're in [0,1]
    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    z = min(max(z, 0.0), 1.0)
    
    x = min(math.floor(x * 1023), 1023)
    y = min(math.floor(y * 1023), 1023)
    z = min(math.floor(z * 1023), 1023)
    
    xx = expand_bits(x)
    yy = expand_bits(y)
    zz = expand_bits(z)
    
    return xx | (yy << 1) | (zz << 2)



class Bvh_node:
    def __init__(self):
        self.elem = None
        self.minimum = Vec3(inf, inf, inf)
        self.maximum = Vec3(-inf, -inf, -inf)

    def is_leaf(self):
        return self.elem is not None
    
    

def create_tree(balls):
    elems = [ {"ball" : ball, "morton_code" : calculate_morton_code(ball.get_position()) } for ball in balls ]
    elems.sort(key = lambda x: x["morton_code"])

    return create_subtree(elems, 0, len(elems)-1)




def create_subtree(elems, begin, end):
    if begin == end:
        return create_leaf(elems[begin])

    else:
        middle = (begin+end)//2
        node = Bvh_node()

        node.left = create_subtree(elems, begin, middle)
        node.right = create_subtree(elems, middle+1, end)

        node.minimum.x = min(node.left.minimum.x, node.right.minimum.x)
        node.minimum.y = min(node.left.minimum.y, node.right.minimum.y)
        node.minimum.z = min(node.left.minimum.z, node.right.minimum.z)

        node.maximum.x = max(node.left.maximum.x, node.right.maximum.x)
        node.maximum.y = max(node.left.maximum.y, node.right.maximum.y)
        node.maximum.z = max(node.left.maximum.z, node.right.maximum.z)

        return node
    



def create_leaf(elem):
    node = Bvh_node()
    node.elem = elem["ball"]
    node.minimum = node.elem.minimum()
    node.maximum = node.elem.maximum()
    return node


def check_boxes_intersect(min_1, max_1, min_2, max_2):
    return (min_1.x <=max_2.x and min_2.x <= max_1.x
            and min_1.y <=max_2.y and min_2.y <= max_1.y
            and min_1.z <=max_2.z and min_2.z <= max_1.z)


def find_collisions(ball, minimum, maximum, node: Bvh_node):
    if check_boxes_intersect(minimum, maximum, node.minimum, node.maximum):
        if node.is_leaf():
            if node.elem != ball:
                check_collision(ball, node.elem)

        else:
            find_collisions(ball, minimum, maximum, node.left)
            find_collisions(ball, minimum, maximum, node.right)

    

def bvh_collisions(balls):
    tree = create_tree(balls)
    for ball in balls:
        if not ball.collided():
            find_collisions(ball, ball.minimum(), ball.maximum(), tree)