from ball import check_collision

def sweep_and_prune_collisions(balls):
    balls.sort(key=lambda ball: ball.left())

    for i, ball in enumerate(balls):
        right = ball.right()
        for j in range(i+1, len(balls)):
            if right <= balls[j].left():
                break
            check_collision(ball, balls[j])