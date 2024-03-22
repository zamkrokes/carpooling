import osmnx as osm
import random
import numpy as np
import time
import datetime
import pandas as pd
import copy
import matplotlib.pyplot as plt
import os

def user_generation(M, N):
    users_willing_to_carpool = [i for i in range(1, M + N + 1)]
    users_willing_to_be_passengers = [i for i in range(M + 1, M + N + 1)]
    users_open_to_share_their_rides = [i for i in range(1, M + 1)]

    return users_willing_to_carpool, users_willing_to_be_passengers, users_open_to_share_their_rides

def path_distance(path, network): # in minutes
    path_distance = osm.utils_graph.route_to_gdf(network, path, 'travel_time')['travel_time'].sum() / 60
    return path_distance

def path_distance_ceiled(path, network): # in minutes
    path_distance = np.ceil(osm.utils_graph.route_to_gdf(network, path, 'travel_time')['travel_time'].sum() / 60)
    return path_distance

def shortest_path(network, origin, destination):
    path = osm.shortest_path(network, origin, destination, weight='travel_time')
    return path

def plot_route_of_passenger_and_assigned_driver(network, driver, passenger, driver_route, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route):
    fig, ax = osm.plot_graph_route(network, driver_route, show=False, close=False, route_color="b")
    passenger_to_driver_route = shortest_path(network, origin_destination_pairs[passenger][0], closest_driving_node_from_passengers_origin_to_drivers_route[(passenger, driver)])
    driver_to_passenger_route = shortest_path(network, closest_driving_node_from_drivers_route_to_passengers_destination[(passenger, driver)], origin_destination_pairs[passenger][1])
    osm.plot_graph_route(network, passenger_to_driver_route, ax=ax, show=False, close=False, route_color='r')
    osm.plot_graph_route(network, driver_to_passenger_route, ax=ax, show=False, close=False, route_color='y')

def plot_route_of_passenger_and_assigned_driver_in_combined(network_combined, network_drive_nodes, driver, passenger, driver_route_in_combined, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route):
    fig, ax= osm.plot_graph_route(network_combined, driver_route_in_combined, show=False, close=False, route_color="b")
    closest_driving_node_from_drivers_route_to_passengers_destination_in_combined = match_nodes_from_drive_network_to_network_combined(closest_driving_node_from_drivers_route_to_passengers_destination[passenger, driver], network_combined, network_drive_nodes)
    # match closest_driving_node_from_passengers_origin_to_drivers_route in network_combined
    closest_driving_node_from_passengers_origin_to_drivers_route_in_combined = match_nodes_from_drive_network_to_network_combined(closest_driving_node_from_passengers_origin_to_drivers_route[passenger, driver], network_combined, network_drive_nodes)
    # match passenger's origin in network_combined
    passenger_origin_in_combined = match_nodes_from_drive_network_to_network_combined(origin_destination_pairs[passenger][0], network_combined, network_drive_nodes)
    # match passenger's destination in network_combined
    passenger_destination_in_combined = match_nodes_from_drive_network_to_network_combined(origin_destination_pairs[passenger][1], network_combined, network_drive_nodes)

    passenger_to_driver_route = shortest_path(network_combined, passenger_origin_in_combined, closest_driving_node_from_passengers_origin_to_drivers_route_in_combined)
    driver_to_passenger_route = shortest_path(network_combined, closest_driving_node_from_drivers_route_to_passengers_destination_in_combined, passenger_destination_in_combined)
    osm.plot_graph_route(network_combined, passenger_to_driver_route, ax=ax, show=False, close=False, route_color='r')
    osm.plot_graph_route(network_combined, driver_to_passenger_route, ax=ax, show=False, close=False, route_color='y')
    filename = os.path.join("visualization", f"driver_{driver}_passenger_{passenger}.jpg")
    plt.savefig(filename, dpi=300, bbox_inches="tight")

def get_nodes_without_na_values(network):
    nodes = osm.graph_to_gdfs(network, nodes=True, edges=False)
    nodes_na = nodes.dropna(subset=['lon', 'lat'])
    return nodes_na

# Function to generate a valid origin node
def generate_node(nodes_na, network):
    generated_node = random.choice(nodes_na.index)
    while network.in_degree(generated_node) == 0 or network.out_degree(generated_node) == 0: # check if it is not an end node
        generated_node = random.choice(nodes_na.index)
    return generated_node

# Function to check if the distance between origin and destination is greater than threshold distance
def is_valid_distance(path, network, threshold_distance):
    path_distance_result = path_distance(path, network)
    return path_distance_result > threshold_distance, path_distance_result

# Function to generate valid origin and destination points
def generate_origin_destination(network_drive, threshold_distance, calculated_shortest_path_and_distances):
    nodes_na = get_nodes_without_na_values(network_drive)

    while True:
        origin = generate_node(nodes_na, network_drive)
        destination = generate_node(nodes_na, network_drive)
    
        while origin == destination:
            destination = generate_node(nodes_na, network_drive)

        if calculated_shortest_path_and_distances != {} and (origin, destination) in calculated_shortest_path_and_distances.keys():
            if calculated_shortest_path_and_distances[(origin, destination)][0] == False:
                continue
            else:
                if calculated_shortest_path_and_distances[(origin, destination)][2] > threshold_distance:
                    return [origin, destination], calculated_shortest_path_and_distances
            
        else:
            if not bool(shortest_path(network_drive, origin, destination)): # if the path from origin to destination does not exist
                calculated_shortest_path_and_distances[(origin, destination)] = False, False, False
            else: # if the path exists
                path = shortest_path(network_drive, origin, destination)
                is_valid_distance_result = is_valid_distance(path, network_drive, threshold_distance)
                calculated_shortest_path_and_distances[(origin, destination)] = bool(path), path, is_valid_distance_result[1]
                if is_valid_distance_result[0]: # if drive time from origin to destination is greater than the threshold distance
                    return [origin, destination], calculated_shortest_path_and_distances

# Function to generate valid origin and destination nodes for each user
def generate_origin_destination_pairs(users_willing_to_carpool, network_drive, threshold_distance, calculated_shortest_path_and_distances):
    origin_destination_pairs = {}
    for user in users_willing_to_carpool:
        origin_destination_pairs[user], calculated_shortest_path_and_distances = generate_origin_destination(network_drive, threshold_distance, calculated_shortest_path_and_distances)
    return origin_destination_pairs

# Function to generate driving routes for each user
def generate_driving_routes(origin_destination_pairs, calculated_shortest_path_and_distances):
    user_driving_routes = {}
    for key, value in origin_destination_pairs.items():
        user_driving_routes[key] = calculated_shortest_path_and_distances[(value[0], value[1])][1]
    return user_driving_routes

# function to generate driving routes of drivers in network_combined, this is needed when visualize = True
def generate_driving_routes_in_combined(network_combined, network_drive_nodes, user_driving_routes):
    # same route as user_driving_routes
    driving_routes_in_combined = {}
    for driver in user_driving_routes.keys():
        # start with origin user_driving_routes[driver][0]
        driver_origin_in_combined = match_nodes_from_drive_network_to_network_combined(user_driving_routes[driver][0], network_combined, network_drive_nodes)
        driver_destination_in_combined = match_nodes_from_drive_network_to_network_combined(user_driving_routes[driver][-1], network_combined, network_drive_nodes)
        # get the next nodes equivalent in network_combined, then add to the driving_routes_in_combined
        node_first = match_nodes_from_drive_network_to_network_combined(user_driving_routes[driver][1], network_combined, network_drive_nodes)
        first_subpath = shortest_path(network_combined, driver_origin_in_combined, node_first)
        for node in user_driving_routes[driver][2:-2]:
            node_second = match_nodes_from_drive_network_to_network_combined(node, network_combined, network_drive_nodes)
            second_subpath = shortest_path(network_combined, node_first, node_second)
            # delete the first node of the first subpath
            subpath = first_subpath + second_subpath[1:]
            first_subpath = subpath
            node_first = node_second
        last_subpath = shortest_path(network_combined, node_second, driver_destination_in_combined)
        # delete the first node of the last subpath
        driving_route_in_combined = subpath + last_subpath[1:]
        driving_routes_in_combined[driver] = driving_route_in_combined
    return driving_routes_in_combined

# Function for matching nodes between drive_network and walk_network by latitude and longitude
def match_nodes_from_drive_network_to_walk_network(node_from_network_drive, network_walk, network_drive_nodes):
    nearest_node_in_walk_network = osm.nearest_nodes(network_walk, network_drive_nodes.iloc[node_from_network_drive]['x'], network_drive_nodes.iloc[node_from_network_drive]['y'])    
    return nearest_node_in_walk_network

# Function for matching nodes from network to network_walk by lat and lot
def match_nodes_from_walk_network_to_drive_network(node_from_walk_network, network_drive, network_walk_nodes):
    nearest_node_in_drive_network = osm.nearest_nodes(network_drive, network_walk_nodes.iloc[node_from_walk_network]['x'], network_walk_nodes.iloc[node_from_walk_network]['y'])    
    return nearest_node_in_drive_network

# Function for matching nodes from drive_network to network_combined by latitude and longitude
def match_nodes_from_drive_network_to_network_combined(node, network_combined, network_drive_nodes):
    nearest_node_in_network_combined = osm.nearest_nodes(network_combined, network_drive_nodes.iloc[node]['x'], network_drive_nodes.iloc[node]['y'])
    return nearest_node_in_network_combined


# Function to get closest node from a user's point to a driver's route, by considering walking distances
def closest_node_and_walking_distance_from_passengers_node_to_drivers_route(driver, passenger_drive_node, passenger_walking_node, user_driving_routes, closest_walking_nodes_of_nodes_in_drivers_route, network_drive_nodes, network_walk):
    driver_route = user_driving_routes[driver]
    driver_walking_nodes = closest_walking_nodes_of_nodes_in_drivers_route[driver]

    closest_node = driver_route[0]
    closest_distance = np.inf

    common_walking_node = np.intersect1d(passenger_drive_node, driver_route)
    if common_walking_node.size > 0:
        closest_distance = 0
        closest_node = common_walking_node[0]
        return [closest_node, closest_distance]
        
    # find closest node in driver_route, considering Manhattan distance
    for node in driver_route:
        # manhattan distance
        distance = abs(network_drive_nodes.loc[node]['lon'] - network_drive_nodes.loc[passenger_drive_node]['lon']) + abs(network_drive_nodes.loc[node]['lat'] - network_drive_nodes.loc[passenger_drive_node]['lat'])
        if distance < closest_distance:
            closest_distance = distance
            closest_node_prior = closest_node
            closest_node = node

    # get index of closest_node in driver_route
    index = driver_route.index(closest_node)
    # convert closest_node into walk network
    closest_node_walk = driver_walking_nodes[index]

    if passenger_walking_node == closest_node_walk:
        closest_distance = 0
        return [closest_node, closest_distance]
    
    # calculate the walking distance from passenger_walk_node to closest_node_walk
    if bool(shortest_path(network_walk, passenger_walking_node, closest_node_walk)):
        closest_distance = path_distance(shortest_path(network_walk, passenger_walking_node, closest_node_walk), network_walk)
    else:
        # if there is no path between passenger_walk_node and closest_node_walk
        # get the closest_node_prior
        closest_node = closest_node_prior
        index = driver_route.index(closest_node)
        closest_node_walk = driver_walking_nodes[index]
        closest_distance = path_distance(shortest_path(network_walk, passenger_walking_node, closest_node_walk), network_walk)

    return [closest_node, closest_distance]

# Function to calculate driving times of users: from users' origin point to users' destination point
def get_driving_times_of_users(origin_destination_pairs, user_driving_routes, network_drive): # in minutes
    driving_distances_of_users = {}
    for key in origin_destination_pairs.keys():
        driving_distances_of_users[key] = path_distance(user_driving_routes[key], network_drive)
    return driving_distances_of_users

# Function to calculate driving time between two nodes
def get_driving_time(origin, destination, drive_network): # in minutes
    driving_time = path_distance(shortest_path(drive_network, origin, destination), drive_network)
    return driving_time

# Function to generate meaningful earliest departure and latest arrival times
def generate_earliest_departure_latest_arrival_times(users_willing_to_carpool, users_willing_to_be_passengers, driving_distances_of_users, W, day):
    earliest_departure_latest_arrival = {}
    for user in users_willing_to_carpool:

        # Generate random departure time within the specified range
        departure_time = datetime.time(hour=random.randint(6, 21), minute=random.randint(0, 59))
        arrival_time = datetime.time(hour=random.randint(7, 23), minute=random.randint(0, 59))

        departure_datetime = datetime.datetime.combine(day, departure_time)
        arrival_datetime = datetime.datetime.combine(day, arrival_time)
        earliest_departure_latest_arrival[user] = (departure_datetime, arrival_datetime)

        diff = arrival_datetime - departure_datetime
        driving_time_of_user_in_minutes = driving_distances_of_users[user]
        
        if abs(diff.total_seconds() / 60) < driving_time_of_user_in_minutes:
            if user in users_willing_to_be_passengers:
                earliest_departure_latest_arrival[user] = (earliest_departure_latest_arrival[user][0], earliest_departure_latest_arrival[user][0] + datetime.timedelta(minutes = int(np.floor((W + driving_time_of_user_in_minutes) * 2))))
            else: 
                earliest_departure_latest_arrival[user] = (earliest_departure_latest_arrival[user][0], earliest_departure_latest_arrival[user][0] + datetime.timedelta(minutes = driving_time_of_user_in_minutes * 2))
        if earliest_departure_latest_arrival[user][0] > earliest_departure_latest_arrival[user][1]:
            earliest_departure_latest_arrival[user] = (earliest_departure_latest_arrival[user][1], earliest_departure_latest_arrival[user][0])
    return earliest_departure_latest_arrival # in datetime.time(year, month, day, hour, minute)

# Function to get all possible drivers for each passenger as an initialization
def get_possible_drivers_for_passenger(users_willing_to_be_passengers, users_open_to_share_their_rides):
    # Create a dictionary for passenger-driver pairs
    possible_drivers_for_passenger = {}
    for passenger in users_willing_to_be_passengers:
        possible_drivers_for_passenger[passenger] = []
        for driver in users_open_to_share_their_rides:
            possible_drivers_for_passenger[passenger].append(driver)
    return possible_drivers_for_passenger

# Function to get closest walking nodes of nodes in drivers route
def get_closest_walking_nodes_of_nodes_in_drivers_route(network_walk, network_drive_nodes, user_driving_routes):
    closest_walking_nodes_of_nodes_in_drivers_route = {}
    for key, value in user_driving_routes.items():
        closest_walking_nodes_of_nodes_in_drivers_route[key] = match_nodes_from_drive_network_to_walk_network(value, network_walk, network_drive_nodes)
    return closest_walking_nodes_of_nodes_in_drivers_route

# Function to get closest nodes in network_drive from closest node in network_walk from passenger's origin point to driver's route and its walking distance for all users             
def get_closest_drive_and_walk_node_and_walking_distance_from_passengers_origin_to_drivers_route(origin_destination_pairs, possible_drivers_for_passenger, user_driving_routes, network_walk, network_drive_nodes, closest_walking_nodes_of_nodes_in_drivers_route): 
    closest_driving_node_from_passengers_origin_to_drivers_route = {}
    walking_distance_from_passengers_origin_to_driver = {}

    for key, value in possible_drivers_for_passenger.items():
        passenger_origin = origin_destination_pairs[key][0]
        passenger_walking_node =  match_nodes_from_drive_network_to_walk_network(passenger_origin, network_walk, network_drive_nodes)
        for driver in value:
            closest_driving_node_from_passengers_origin_to_drivers_route[(key, driver)], walking_distance_from_passengers_origin_to_driver[(key, driver)]  = closest_node_and_walking_distance_from_passengers_node_to_drivers_route(driver, passenger_origin, passenger_walking_node, user_driving_routes, closest_walking_nodes_of_nodes_in_drivers_route, network_drive_nodes, network_walk)
    return closest_driving_node_from_passengers_origin_to_drivers_route, walking_distance_from_passengers_origin_to_driver

# Function to get closest nodes in network_drive from closest node in network_walk from driver's route to passenger's destination point and its walking distance for all users             
def get_closest_drive_and_walk_node_and_walking_distance_from_drivers_route_to_passengers_destination(origin_destination_pairs, possible_drivers_for_passenger, user_driving_routes, network_walk, network_drive_nodes, closest_walking_nodes_of_nodes_in_drivers_route):
    closest_driving_node_from_drivers_route_to_passengers_destination = {}
    walking_distance_from_driver_to_passengers_destination = {}
    for key, value in possible_drivers_for_passenger.items():
        passenger_destination = origin_destination_pairs[key][1]
        passenger_walking_node =  match_nodes_from_drive_network_to_walk_network(passenger_destination, network_walk, network_drive_nodes)
        for driver in value:
            closest_driving_node_from_drivers_route_to_passengers_destination[(key, driver)], walking_distance_from_driver_to_passengers_destination[(key, driver)]  = closest_node_and_walking_distance_from_passengers_node_to_drivers_route(driver, passenger_destination, passenger_walking_node, user_driving_routes, closest_walking_nodes_of_nodes_in_drivers_route, network_drive_nodes, network_walk)
    return closest_driving_node_from_drivers_route_to_passengers_destination, walking_distance_from_driver_to_passengers_destination

# Function to pre-process passenger-driver pairs by eliminating drivers: earliest departure time of passenger > latest arrival time of driver
def first_preprocess(users_willing_to_be_passengers, users_open_to_share_their_rides, earliest_departure_latest_arrival, earliest_departure_latest_arrival_minutes, driving_time):
    possible_drivers_for_passenger = get_possible_drivers_for_passenger(users_willing_to_be_passengers, users_open_to_share_their_rides)
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for passenger in users_willing_to_be_passengers:
        for driver in users_open_to_share_their_rides:
            if earliest_departure_latest_arrival[passenger][0] > earliest_departure_latest_arrival[driver][1]:
                copy_dict[passenger].remove(driver)
            elif earliest_departure_latest_arrival[passenger][1] < earliest_departure_latest_arrival[driver][0]:
                copy_dict[passenger].remove(driver)
            elif earliest_departure_latest_arrival_minutes[passenger][0] + driving_time[passenger] > earliest_departure_latest_arrival_minutes[driver][1]:
                copy_dict[passenger].remove(driver)
            elif earliest_departure_latest_arrival_minutes[passenger][1] < earliest_departure_latest_arrival_minutes[driver][0] + driving_time[driver]:
                copy_dict[passenger].remove(driver)
    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to pre-process passenger-driver pairs by eliminating drivers: walking distance from passenger's origin point to driver's route > W
def second_preprocess(possible_drivers_for_passenger, walking_distance_from_passengers_origin_to_driver, W):  
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if walking_distance_from_passengers_origin_to_driver[(key, driver)] > W:
                copy_dict[key].remove(driver)
    possible_drivers_for_passenger = copy_dict

    return possible_drivers_for_passenger

# Function to eliminate passenger-driver pairs: if closest node from passenger's origin point to driver's route's index in user driving route is greater than the closest node from driver's route to passenger's destination point's index in user driving route
def order_preprocess(possible_drivers_for_passenger, user_driving_routes, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route):
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if user_driving_routes[driver].index(closest_driving_node_from_passengers_origin_to_drivers_route[key,driver]) > user_driving_routes[driver].index(closest_driving_node_from_drivers_route_to_passengers_destination[key,driver]):
                copy_dict[key].remove(driver)
    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to preprocess passenger-driver pairs by eliminating drivers: walking time from passenger's origin point to driver's route + walking time from driver's route to passenger's destination point > W
def third_preprocess(possible_drivers_for_passenger, walking_distance_from_passengers_origin_to_driver, walking_distance_from_driver_to_passengers_destination, W):
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if walking_distance_from_driver_to_passengers_destination[(key, driver)] > W:
                copy_dict[key].remove(driver)
            elif walking_distance_from_passengers_origin_to_driver[(key, driver)] + walking_distance_from_driver_to_passengers_destination[(key, driver)] > W:
                copy_dict[key].remove(driver)

    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to preprocess passenger-driver pairs by eliminating drivers: walking time from passenger's origin point to driver's route + earliest departure time of passenger < earliest departure time of driver + driving time from driver's origin point to passenger's closest point on driver's route
def forth_preprocess(possible_drivers_for_passenger, origin_destination_pairs, closest_driving_node_from_passengers_origin_to_drivers_route, earliest_departure_latest_arrival, walking_distance_from_passengers_origin_to_driver, drive_network):
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if origin_destination_pairs[driver][0] == closest_driving_node_from_passengers_origin_to_drivers_route[key,driver]:
                driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route = 0
            else:
                driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route = get_driving_time(origin_destination_pairs[driver][0], closest_driving_node_from_passengers_origin_to_drivers_route[(key,driver)], drive_network) 
            if earliest_departure_latest_arrival[key][0] + datetime.timedelta(minutes = walking_distance_from_passengers_origin_to_driver[(key, driver)]) < earliest_departure_latest_arrival[driver][0] + datetime.timedelta(minutes = driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route):
                copy_dict[key].remove(driver)
    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to preprocess passenger-driver pairs by eliminating drivers: latest arrival time of passenger < latest arrival time of driver - driving time from passenger's closest point on driver's route to driver's destination point + walking time from driver's destination point to passenger's destination point
def fifth_preprocess(possible_drivers_for_passenger, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, earliest_departure_latest_arrival, walking_distance_from_driver_to_passengers_destination, drive_network):
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if closest_driving_node_from_drivers_route_to_passengers_destination[key,driver] == origin_destination_pairs[driver][1]:
                driving_distance_from_passengers_closest_node_to_drivers_destination = 0
            else:
                driving_distance_from_passengers_closest_node_to_drivers_destination = get_driving_time(closest_driving_node_from_drivers_route_to_passengers_destination[key,driver], origin_destination_pairs[driver][1], drive_network)
            if earliest_departure_latest_arrival[key][1] < earliest_departure_latest_arrival[driver][1] - datetime.timedelta(minutes = driving_distance_from_passengers_closest_node_to_drivers_destination) + datetime.timedelta(minutes = int(walking_distance_from_driver_to_passengers_destination[(key, driver)])):
                copy_dict[key].remove(driver)
    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to calculate ride distances of passenger-driver pairs
def get_ride_distances_of_passenger_driver_pairs(possible_drivers_for_passenger, closest_driving_node_from_passengers_origin_to_drivers_route, closest_driving_node_from_drivers_route_to_passengers_destination, drive_network):
    ride_distances_of_passenger_driver_pairs = {}
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if closest_driving_node_from_drivers_route_to_passengers_destination[key,driver] == closest_driving_node_from_passengers_origin_to_drivers_route[key,driver]:
                ride_distances_of_passenger_driver_pairs[(key, driver)] = 0
            else:
                ride_distances_of_passenger_driver_pairs[(key, driver)] = get_driving_time(closest_driving_node_from_passengers_origin_to_drivers_route[key,driver], closest_driving_node_from_drivers_route_to_passengers_destination[key,driver], drive_network)
    return ride_distances_of_passenger_driver_pairs

# Function to eliminate passenger-driver pairs by considering ride distances, eliminate if too short
def ride_distance_preprocess(possible_drivers_for_passenger, ride_distances_of_passenger_driver_pairs, R):
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for passenger_id, driver_ids in possible_drivers_for_passenger.items():
        for driver_id in driver_ids.copy():  
            distance = ride_distances_of_passenger_driver_pairs[passenger_id, driver_id]
            if distance < R:
                copy_dict[passenger_id].remove(driver_id)
    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to preprocess passenger-driver pairs by eliminating drivers: 
def sixth_preprocess(possible_drivers_for_passenger, earliest_departure_latest_arrival, walking_distance_from_passengers_origin_to_driver, walking_distance_from_driver_to_passengers_destination, ride_distances_of_passenger_driver_pairs):
    copy_dict = copy.deepcopy(possible_drivers_for_passenger)
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if earliest_departure_latest_arrival[key][0] + datetime.timedelta(minutes = walking_distance_from_passengers_origin_to_driver[(key, driver)] + ride_distances_of_passenger_driver_pairs[key,driver] +walking_distance_from_driver_to_passengers_destination[(key,driver)] ) > earliest_departure_latest_arrival[key][1]:
                copy_dict[key].remove(driver)
    possible_drivers_for_passenger = copy_dict
    return possible_drivers_for_passenger

# Function to get all possible drivers
def get_all_possible_drivers(possible_drivers_for_passenger):
    possible_drivers_list = [driver for drivers_list in possible_drivers_for_passenger.values() for driver in drivers_list]
    return possible_drivers_list

# Function to get possible passengers for each driver
def get_possible_passengers_for_each_driver(possible_drivers_for_passenger):
    possible_drivers_list = get_all_possible_drivers(possible_drivers_for_passenger)
    possible_passengers_for_driver = {}
    for driver in possible_drivers_list:
        possible_passengers_for_driver[driver] = []
        for key, value in possible_drivers_for_passenger.items():
            if driver in value:
                possible_passengers_for_driver[driver].append(key)
    return possible_passengers_for_driver

# Function to create a dictionary for driver-passenger pairs from possible_drivers_for_passenger
def get_passenger_driver_pairs(possible_drivers_for_passenger):
    passenger_driver_pairs = {}
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if (driver, key) not in passenger_driver_pairs.keys():
                passenger_driver_pairs[(key, driver)] = 1
    return passenger_driver_pairs

# Function to get unique possible drivers list
def get_unique_possible_drivers_list(possible_drivers_for_passenger):
    unique_possible_drivers_list = []
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if driver not in unique_possible_drivers_list:
                unique_possible_drivers_list.append(driver)
    return unique_possible_drivers_list

def convert_datetime_to_minutes(datetime_obj):
    minutes = datetime_obj.minute + datetime_obj.hour * 60
    return minutes

def get_earliest_departure_latest_arrival_minutes(users_willing_to_carpool, earliest_departure_latest_arrival):
    earliest_departure_latest_arrival_minutes = {}
    for user in users_willing_to_carpool:
        earliest_departure_latest_arrival_minutes[user] = convert_datetime_to_minutes(earliest_departure_latest_arrival[user][0]), convert_datetime_to_minutes(earliest_departure_latest_arrival[user][1])
    
    return earliest_departure_latest_arrival_minutes

def generate_data_and_preprocess(network_drive, network_combined, network_walk, network_drive_nodes, threshold_distance, today_datetime, M, N, W, R, visualize = False):
    print("Data generation is started")
    start_time = time.time()
    users_willing_to_carpool, users_willing_to_be_passengers, users_open_to_share_their_rides = user_generation(M, N)
    print("Users are generated")
    calculated_shortest_path_and_distances = {}
    origin_destination_pairs = generate_origin_destination_pairs(users_willing_to_carpool, network_drive, threshold_distance, calculated_shortest_path_and_distances)
    print("Origin-destination pairs are generated")
    # to_csv
    pd.DataFrame.from_dict(origin_destination_pairs, orient='index').to_csv('origin_destination_pairs.csv')
    user_driving_routes = generate_driving_routes(origin_destination_pairs, calculated_shortest_path_and_distances)
    print("Driving routes are generated")
    if visualize == True:
        user_driving_routes_in_combined = generate_driving_routes_in_combined(network_combined, network_drive_nodes, user_driving_routes)
        print("Driving routes in combined are generated")
    driving_times = get_driving_times_of_users(origin_destination_pairs, user_driving_routes, network_drive)
    print("Driving times are calculated")
    earliest_departure_latest_arrival = generate_earliest_departure_latest_arrival_times(users_willing_to_carpool, users_willing_to_be_passengers, driving_times, W, today_datetime)
    print("Earliest departure and latest arrival times are generated")
    end_time = time.time()
    print("Data generation is completed")
    print("Data generation time: ", end_time - start_time)

    print("Pre-processing is started")
    start_time = time.time()
    closest_walking_nodes_of_nodes_in_drivers_route = get_closest_walking_nodes_of_nodes_in_drivers_route(network_walk, network_drive_nodes, user_driving_routes)
    end_time = time.time()
    print("get_closest_walking_nodes_of_nodes_in_drivers_route time: ", end_time - start_time)

    earliest_departure_latest_arrival_minutes = get_earliest_departure_latest_arrival_minutes(users_willing_to_carpool, earliest_departure_latest_arrival)
    start_time = time.time()    
    possible_drivers_for_passenger = first_preprocess(users_willing_to_be_passengers, users_open_to_share_their_rides, earliest_departure_latest_arrival, earliest_departure_latest_arrival_minutes, driving_times)
    end_time = time.time()
    print("first_preprocess time: ", end_time - start_time)

    # assertion for first_preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value: # assert if
            assert earliest_departure_latest_arrival[key][0] <= earliest_departure_latest_arrival[driver][1], "first_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)
            assert earliest_departure_latest_arrival[key][1] >= earliest_departure_latest_arrival[driver][0], "first_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)
            assert earliest_departure_latest_arrival_minutes[key][0] + driving_times[key] <= earliest_departure_latest_arrival_minutes[driver][1], "first_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)
            assert earliest_departure_latest_arrival_minutes[key][1] >= earliest_departure_latest_arrival_minutes[driver][0] + driving_times[driver], "first_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)

    start_time = time.time()
    closest_driving_node_from_passengers_origin_to_drivers_route, walking_distance_from_passengers_origin_to_driver = get_closest_drive_and_walk_node_and_walking_distance_from_passengers_origin_to_drivers_route(origin_destination_pairs, possible_drivers_for_passenger, user_driving_routes, network_walk, network_drive_nodes, closest_walking_nodes_of_nodes_in_drivers_route)
    end_time = time.time()
    print("get_closest_drive_and_walk_node_and_walking_distance_from_passengers_origin_to_drivers_route time: ", end_time - start_time)

    start_time = time.time()
    possible_drivers_for_passenger = second_preprocess(possible_drivers_for_passenger, walking_distance_from_passengers_origin_to_driver, W)
    end_time = time.time()
    print("second_preprocess time: ", end_time - start_time)

    # assertion for second preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            assert walking_distance_from_passengers_origin_to_driver[(key, driver)] <= W, "second_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)

    start_time = time.time()
    closest_driving_node_from_drivers_route_to_passengers_destination, walking_distance_from_driver_to_passengers_destination = get_closest_drive_and_walk_node_and_walking_distance_from_drivers_route_to_passengers_destination(origin_destination_pairs, possible_drivers_for_passenger, user_driving_routes, network_walk, network_drive_nodes, closest_walking_nodes_of_nodes_in_drivers_route)
    end_time = time.time()                                                                                                                                                               
    print("get_closest_drive_and_walk_node_and_walking_distance_from_drivers_route_to_passengers_destination time: ", end_time - start_time)

    start_time = time.time()
    possible_drivers_for_passenger = order_preprocess(possible_drivers_for_passenger, user_driving_routes, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route)
    end_time = time.time()
    print("order_preprocess time: ", end_time - start_time)

    # assertion for order_preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            assert user_driving_routes[driver].index(closest_driving_node_from_passengers_origin_to_drivers_route[key,driver]) <= user_driving_routes[driver].index(closest_driving_node_from_drivers_route_to_passengers_destination[key,driver]), "order_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)
                
    start_time = time.time()
    possible_drivers_for_passenger = third_preprocess(possible_drivers_for_passenger, walking_distance_from_passengers_origin_to_driver, walking_distance_from_driver_to_passengers_destination, W)
    end_time = time.time()
    print("third_preprocess time: ", end_time - start_time)

    # assertion for third_preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            assert walking_distance_from_passengers_origin_to_driver[(key, driver)] + walking_distance_from_driver_to_passengers_destination[(key, driver)] <= W, "third_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)


    start_time = time.time()
    possible_drivers_for_passenger = forth_preprocess(possible_drivers_for_passenger, origin_destination_pairs, closest_driving_node_from_passengers_origin_to_drivers_route, earliest_departure_latest_arrival, walking_distance_from_passengers_origin_to_driver, network_drive)
    end_time = time.time()
    print("forth_preprocess time: ", end_time - start_time)

    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if origin_destination_pairs[driver][0] == closest_driving_node_from_passengers_origin_to_drivers_route[key,driver]:
                driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route = 0
            else:
                driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route = get_driving_time(origin_destination_pairs[driver][0], closest_driving_node_from_passengers_origin_to_drivers_route[(key,driver)], network_drive) 
            assert earliest_departure_latest_arrival[key][0] + datetime.timedelta(minutes = walking_distance_from_passengers_origin_to_driver[(key, driver)]) >= earliest_departure_latest_arrival[driver][0] + datetime.timedelta(minutes = driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route), "forth_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)
    
    start_time = time.time()
    possible_drivers_for_passenger = fifth_preprocess(possible_drivers_for_passenger, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, earliest_departure_latest_arrival, walking_distance_from_driver_to_passengers_destination, network_drive)
    end_time = time.time()
    print("fifth_preprocess time: ", end_time - start_time)

    # assertion for fifth_preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if closest_driving_node_from_drivers_route_to_passengers_destination[key,driver] == origin_destination_pairs[driver][1]:
                assert earliest_departure_latest_arrival[key][1] >= earliest_departure_latest_arrival[driver][1] + datetime.timedelta(minutes = int(walking_distance_from_driver_to_passengers_destination[(key, driver)])), "fifth_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)
            else:
                assert earliest_departure_latest_arrival[key][1] >= earliest_departure_latest_arrival[driver][1] - datetime.timedelta(minutes = get_driving_time(closest_driving_node_from_drivers_route_to_passengers_destination[key,driver], origin_destination_pairs[driver][1], network_drive)) + datetime.timedelta(minutes = int(walking_distance_from_driver_to_passengers_destination[(key, driver)])), "fifth_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)

    start_time = time.time()
    ride_distances_of_passenger_driver_pairs = get_ride_distances_of_passenger_driver_pairs(possible_drivers_for_passenger, closest_driving_node_from_passengers_origin_to_drivers_route, closest_driving_node_from_drivers_route_to_passengers_destination, network_drive)
    end_time = time.time()
    print("get_ride_distances_of_passenger_driver_pairs time: ", end_time - start_time)

    start_time = time.time()
    possible_drivers_for_passenger = ride_distance_preprocess(possible_drivers_for_passenger, ride_distances_of_passenger_driver_pairs, R)
    end_time = time.time()
    print("ride_distance_preprocess time: ", end_time - start_time)

    # assertion for ride_distance_preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            assert ride_distances_of_passenger_driver_pairs[key,driver] >= R, "ride_distance_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)

    start_time = time.time()
    possible_drivers_for_passenger = sixth_preprocess(possible_drivers_for_passenger, earliest_departure_latest_arrival, walking_distance_from_passengers_origin_to_driver, walking_distance_from_driver_to_passengers_destination, ride_distances_of_passenger_driver_pairs)
    end_time = time.time()
    print("sixth_preprocess time: ", end_time - start_time)
    print("Pre-processing is completed")

    # assertion for sixth_preprocess
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            assert earliest_departure_latest_arrival[key][0] + datetime.timedelta(minutes = walking_distance_from_passengers_origin_to_driver[(key, driver)] + ride_distances_of_passenger_driver_pairs[key,driver] +walking_distance_from_driver_to_passengers_destination[(key,driver)] ) <= earliest_departure_latest_arrival[key][1], "sixth_preprocess assertion failed for passenger: " + str(key) + " and driver: " + str(driver)

    possible_passengers_for_driver = get_possible_passengers_for_each_driver(possible_drivers_for_passenger)
    passenger_driver_pairs = get_passenger_driver_pairs(possible_drivers_for_passenger)
    unique_possible_drivers_list =  get_unique_possible_drivers_list(possible_drivers_for_passenger)

    driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route = {}
    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if origin_destination_pairs[driver][0] == closest_driving_node_from_passengers_origin_to_drivers_route[key,driver]:
                driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route[key,driver] = 0
            else:
                driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route[key,driver] = get_driving_time(origin_destination_pairs[driver][0], closest_driving_node_from_passengers_origin_to_drivers_route[(key,driver)], network_drive)
    
    driving_distances_from_passengers_closest_node_to_drivers_destination = {}

    for key, value in possible_drivers_for_passenger.items():
        for driver in value:
            if origin_destination_pairs[driver][1] == closest_driving_node_from_drivers_route_to_passengers_destination[key,driver]:
                driving_distances_from_passengers_closest_node_to_drivers_destination[key,driver] = 0
            else:
                driving_distances_from_passengers_closest_node_to_drivers_destination[key,driver] = get_driving_time(closest_driving_node_from_drivers_route_to_passengers_destination[key,driver], origin_destination_pairs[driver][1], network_drive)
    
    return users_willing_to_carpool, users_willing_to_be_passengers, users_open_to_share_their_rides, passenger_driver_pairs, unique_possible_drivers_list, possible_passengers_for_driver, possible_drivers_for_passenger, user_driving_routes_in_combined, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route, driving_times, earliest_departure_latest_arrival_minutes, walking_distance_from_passengers_origin_to_driver, walking_distance_from_driver_to_passengers_destination, ride_distances_of_passenger_driver_pairs, driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route, earliest_departure_latest_arrival