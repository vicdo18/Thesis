import numpy as np
import json
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter # Import for smoothing the population density heatmap
from sklearn import preprocessing


def generate_population_data(n: int = 10, total_population: int = 100000):
    """
    Generates simulated population density data for an n x n grid,
    grouping population into clusters (neighborhoods).

    Args:
        n (int): The number of divisions along each axis (e.g., n=10 creates a 10x10 grid).
        total_population (int): The total population to distribute across the grid.

    Returns:
        tuple: A tuple containing:
            - np.ndarray: The n x n population density grid.
            - list: A list of dictionaries, each representing a grid cell
                    with its location, population density, and proportion of total population.
    """
    population_grid = np.zeros((n, n), dtype=float)

    # Determine the number of neighborhoods.
    # We'll create one neighborhood for every 5 grid cells, ensuring at least one.
    #num_neighborhoods = max(1, (n * n) // 5)
    num_neighborhoods = int(n/3)

    # Randomly assign unique center coordinates for each neighborhood.
    # We use np.random.choice to pick unique indices from a flattened grid.
    center_indices = np.random.choice(n * n, num_neighborhoods, replace=False)
    neighborhood_centers = [(idx // n, idx % n) for idx in center_indices]

    # Distribute population around each neighborhood center using a Gaussian falloff.
    # A smaller sigma means tighter clusters, larger means more spread out.
    sigma_neighborhood = n / 5.0 # Adjust this value to control neighborhood spread

    for center_row, center_col in neighborhood_centers:
        # Create a temporary grid for this neighborhood's population distribution
        neighborhood_distribution = np.zeros((n, n), dtype=float)
        neighborhood_distribution[center_row, center_col] = 1.0 # Peak at the center

        # Apply a Gaussian filter to simulate diminishing population further from the center
        smoothed_neighborhood = gaussian_filter(neighborhood_distribution, sigma=sigma_neighborhood)

        # Add this neighborhood's smoothed population to the main grid
        population_grid += smoothed_neighborhood

    # Normalize the entire grid to the total_population
    if population_grid.sum() > 0:
        population_grid = (population_grid / population_grid.sum()) * total_population
    else:
        # If no population was generated (e.g., very small n and num_neighborhoods),
        # ensure the grid is all zeros to prevent errors.
        population_grid = np.zeros((n, n))

    # Convert the population values to integers for the final grid representation
    population_grid = population_grid.astype(int)

    # Prepare data for JSON output.
    density_data = []
    for i in range(n):
        for j in range(n):
            cell_population = population_grid[i, j].item()
            # Calculate the proportion of the total population for the current cell
            population_proportion = cell_population / total_population if total_population > 0 else 0.0
            density_data.append({
                "grid_location": [i,j],
                "population_density": cell_population,
                "population_proportion": population_proportion
            })
    return population_grid, density_data

def allocate_bike_sharing_stations(density_data: list, num_stations: int, bikers_min, bikers_max):
    """
    Allocates a fixed number of bike sharing stations to grid positions
    to serve the greatest number of people, but with a chance for low-population
    cells to be selected. The station coordinates are returned as floating-point numbers,
    representing the center of the selected grid cell.

    Args:
        density_data (list): A list of dictionaries, each representing a grid cell
                             with its location and population density.
        num_stations (int): The fixed number of bike sharing stations to allocate.

    Returns:
        list: A list of dictionaries, each representing a selected grid location
              for a bike sharing station, including its floating-point coordinates.
    """
    if not density_data:
        print("No density data available for station allocation.")
        return []

    # Extract population densities and create a list of indices for selection
    populations = np.array([d['population_density'] for d in density_data])
    grid_indices = np.arange(len(density_data))

    # Calculate probabilities for selection.
    # Add a small constant (e.g., 1) to each population to ensure even zero-population
    # cells have a non-zero chance of being selected.
    # Normalize these values to sum to 1 to form valid probabilities.
    probabilities = populations + 0 # Add 1 to ensure non-zero probability
    probabilities = probabilities / probabilities.sum()
    #scaler = preprocessing.MinMaxScaler(feature_range=(0.01, 1))
    #d = scaler.fit_transform(california_housing.data)
    #print(probabilities)

    # Determine the actual number of stations to select, ensuring it doesn't exceed
    # the number of available grid cells.
    num_to_select = min(num_stations, len(density_data))

    # Randomly select unique grid indices based on the calculated probabilities.
    # 'replace=False' ensures that each selected grid cell is unique.
    try:
        selected_indices = np.random.choice(grid_indices, size=num_to_select, p=probabilities, replace=False)
    except ValueError as e:
        print(f"Error during random choice: {e}. This might happen if num_stations is too large or probabilities are ill-defined.")
        return []

    # Process the selected stations to include their floating-point coordinates.
    selected_stations_processed = []
    print(f"\nAllocated {len(selected_indices)} bike sharing stations:")
    for idx in selected_indices:
        station = density_data[idx]
        row = station['grid_location'][0]
        col = station['grid_location'][1]
        # Assign floating-point coordinates (e.g., center of the grid cell)
        if row<len(grid_indices)**0.5-1:
            float_row = row + round(np.random.random(),3)
        else:
            float_row = row - round(np.random.random(),3)
        if col<len(grid_indices)**0.5-1:
            float_col = col + round(np.random.random(),3)
        else:
            float_col = col - round(np.random.random(),3)
            
        selected_stations_processed.append({
            "grid_location": station['grid_location'],
            "population_density": station['population_density'],
            "population_proportion": station['population_density']/populations.sum(),
            "population_max": int(populations.max()),
            "coordinates": [float_col, float_row], # (x, y) for plotting, so (col, row)
            "popularity": np.random.uniform(bikers_min, bikers_max)
        })
        print(f"  Grid Location: {station['grid_location']}, Population Density: {station['population_density']}, Coordinates: ({float_col:.1f}, {float_row:.1f}), Pop_proportion: {station['population_density']/populations.sum()}")

    print(populations.max())

    return selected_stations_processed

def visualize_map(population_grid: np.ndarray, selected_stations: list, n: int, population, stations):
    """
    Visualizes both the smoothed population density heatmap and the locations
    of the allocated bike sharing stations.

    Args:
        population_grid (np.ndarray): The n x n population density grid.
        selected_stations (list): A list of dictionaries, each representing a selected
                                  grid location for a bike sharing station,
                                  including its floating-point coordinates.
        n (int): The number of divisions along each axis of the grid.
    """
    plt.figure(figsize=(8, 6)) # Set the figure size for better visualization

    # Apply a Gaussian filter for smoothing the heatmap
    smoothed_density = gaussian_filter(population_grid.astype(float), sigma=1)

    # Create the smoothed heatmap
    plt.imshow(smoothed_density, cmap='viridis', interpolation='bilinear')
    plt.colorbar(label='Smoothed Population Density')
    plt.title(f'Smoothed Population Density Heatmap with Bike Stations ({n}x{n} Grid)')
    plt.xlabel('Grid Column')
    plt.ylabel('Grid Row')
    plt.xticks(np.arange(n)) # Set x-axis ticks for each grid column
    plt.yticks(np.arange(n)) # Set y-axis ticks for each grid row
    plt.grid(True, which='both', color='gray', linestyle='-', linewidth=0.5)

    # Plot bike station locations using floating-point coordinates
    station_x = [s['coordinates'][0] for s in selected_stations]
    station_y = [s['coordinates'][1] for s in selected_stations]

    # Plot the stations as distinct markers (e.g., green stars)
    plt.scatter(station_x, station_y, marker='o', s=50, color='lime', edgecolor='black', linewidth=1, label='Bike Stations', zorder=2)
    plt.legend() # Display the legend for bike stations
    plt.savefig("city_"+str(population)+"_"+str(stations)+".png")
    plt.show() # Display the plot

# --- Main execution flow ---
if __name__ == "__main__":
    grid_size = 20
    total_pop = 250000
    num_bike_stations = 100
    population_filename = "population_density_"+str(total_pop)+"_"+str(num_bike_stations)+".json"
    station_filename = "bike_stations_"+str(total_pop)+"_"+str(num_bike_stations)+".json"

    # 1. Generate population data
    population_data_grid, population_data_json = generate_population_data(n=grid_size, total_population=total_pop)

    # Save the generated JSON data to a file
    try:
        with open(population_filename, 'w') as f:
            json.dump(population_data_json, f, indent=4)
        print(f"Population density data saved to {population_filename}")
    except IOError as e:
        print(f"Error saving file {population_filename}: {e}")

    # 2. Allocate bike sharing stations
    # The returned 'allocated_stations' now contains floating-point 'coordinates'
    allocated_stations = allocate_bike_sharing_stations(population_data_json, num_bike_stations, 0.05, 0.15)

    # Save the generated JSON data to a file
    try:
        with open(station_filename, 'w') as f:
            print(allocated_stations)
            json.dump(allocated_stations, f, indent=4)
        print(f"Station data saved to {station_filename}")
    except IOError as e:
        print(f"Error saving file {station_filename}: {e}")

    # 3. Visualize both population density and bike station locations
    visualize_map(population_data_grid, allocated_stations, n=grid_size, population=total_pop, stations=num_bike_stations)
