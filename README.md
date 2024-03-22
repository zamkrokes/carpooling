# Carpooling Optimization
## Project Description
This repository contains an optimization model and associated network generation and preprocessing scripts for carpooling applications.

### Key Features

- Data Generation and Preprocessing:
Generates synthetic data representing users, origin-destination pairs, earliest departure-latest arrival times, and more.
Calculates driving times, derives shortest paths, determines pick-up and drop-off points.
Performs preprocessing to eliminate infeasible passenger-driver pairs before creating optimization model.

- Network Analysis:
Utilizes network analysis techniques to model driving and walking networks.
Integrates OpenStreetMap data to create road networks for driving and walking.
Cleans and consolidates network data to ensure accuracy and efficiency.

- Optimization Model:
Implements an optimization model using the Gurobi optimization library.
Formulates the objective function to minimize total number of SOVs with weights as driving times while considering constraints.
Specifies constraints related to car capacity, assignments, and time-related factors.

- Parameter Adjustments:
Provides flexibility to adjust parameters such as the number of drivers, passengers, maximum walking time, and car capacity.
Allows customization of parameters to accommodate different scenarios and preferences.

- Result Visualization:
Visualizes optimization results, including driver-passenger assignments, departure times, and routes on the network.
Facilitates the analysis and interpretation of carpooling assignments.

## How to Run the Project? 

- Adjust Configuration Parameters
Open optimization.py file and adjust the parameters such as the number of drivers, passengers, maximum walking time, and minimum ride time based on your requirements.
Open network.py file, adjust 'area' according to your desired location.

- Run the Project
Run this command:
    python optimization.py

- View Results
After running the project, view the assignments.csv, departure_arrival_times.csv, users_going_by_its_own_car.csv files in the project folder. And view the visualization of the routes on network in the 'visualization' folder in the project folder.

## File Descriptions
### data_generation_and_preprocess.py:

This file includes functions for generating data, preprocessing the data, and performing various calculations related to carpooling.
It contains functions for user generation, path calculation, route plotting, origin-destination pair generation, preprocessing of passenger-driver pairs, and more.
The functions are extensively documented within the file for further details on their usage and parameters.

### network.py:
This file contains functions for retrieving, processing, and analyzing network data using the OSMnx and networkx library. It serves as a crucial component in the carpooling system, providing the necessary infrastructure for route calculation and analysis.

### optimization.py:
This file includes an optimization model built using the Gurobi optimization library for efficient carpooling assignments. It plays a central role in optimizing the allocation of drivers and passengers to minimize number of SOVs, with weights as drive times.

## Adjustable Parameters:
### in optimization.py
M: Number of drivers.
N: Number of passengers.
W: Maximum walking travel time that a user is willing to walk, in minutes.
R: Minimum ride travel time that a user is willing to ride, in minutes.
threshold_distance: Minimum travel time between origin and destination, in minutes (for origin destination generation).
car_capacity: Maximum number of passengers that a car can carry.
visualize: Boolean parameter to toggle result visualization on or off.
### in network.py
area: Location selection.

## Technologies Used:

Python, OpenStreetMap (OSM), OSMnx, NetworkX, Gurobi, Pandas, NumPy, Matplotlib, Plotly, Random, Datetime, Time