import gymnasium as gym
from stable_baselines3 import PPO # PPO świetnie działa z Cheetah

# 1. Tworzymy środowisko (bez renderowania, żeby było szybciej)
env = gym.make("Reacher-v5")

# 2. Definiujemy model
# PPO jest bardzo stabilne dla tego robota
model = PPO("MlpPolicy", env, verbose=1)

print("Rozpoczynam naukę... To może chwilę potrwać.")
# 1 000 000 kroków pozwoli mu biegać bardzo szybko
model.learn(total_timesteps=100000)

# 3. Zapisujemy wagi modelu do pliku .zip
model.save("reacher")
print("Model zapisany jako reacher.zip!")

env.close()