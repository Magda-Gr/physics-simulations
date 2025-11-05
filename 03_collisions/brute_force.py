from ball import check_collision


def brute_force_collisions(balls):
    for i, ball in enumerate(balls):
        for j in range(i+1, len(balls)):
            ball_2 = balls[j]
            check_collision(ball, ball_2)