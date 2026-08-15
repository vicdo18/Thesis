import os
import sys
import subprocess

def run_simulation():
    #searches for the core/simulator.py file and runs it
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # defines path for core/simulator.py
    simulator_path = os.path.join(base_dir, 'core', 'Bike-sharing-simulator-v4_AK.py')
    
    print("--- Starting Simulator (BikeSim) ---")
    print(f"Working Directory: {base_dir}")
    
    # runs the simulator
    try:
        subprocess.run([sys.executable, simulator_path], cwd=base_dir, check=True)
        print("--- The Simulation Completed Successfully ---")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running the simulation: {e}")

if __name__ == "__main__":
    run_simulation()