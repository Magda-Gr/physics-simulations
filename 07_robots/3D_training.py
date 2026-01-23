import gymnasium as gym
from stable_baselines3 import PPO

env = gym.make("Humanoid-v5")

model = PPO("MlpPolicy", env, verbose=1)

print("Rozpoczynam naukę... To może chwilę potrwać.")
model.learn(total_timesteps=1000000)

model.save("humanoid")
print("Model zapisany jako humanoid.zip!")

env.close()