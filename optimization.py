import gurobipy as gp
from gurobipy import GRB
import datetime
import random
import numpy as np
import pandas as pd
import os

from network import network_drive, network_walk, network_combined, network_drive_nodes
from data_generation_and_preprocess import generate_data_and_preprocess, plot_route_of_passenger_and_assigned_driver_in_combined

M = 60 # number of drivers
N = 90 # number of passengers
W = 1 # maximum walking travel_time that a user is willing to walk
R = 2 # minimum ride travel_time that a user is willing to ride, in minutes
threshold_distance = 3 # minimum travel_time between origin and destination, in minutes
car_capacity = 3 # maximum number of passengers that a car can carry
visualize = True
today_datetime = datetime.date(2024, 1, 1)
random.seed(1)

users_willing_to_carpool, users_willing_to_be_passengers, users_open_to_share_their_rides, passenger_driver_pairs, unique_possible_drivers_list, possible_passengers_for_driver, possible_drivers_for_passenger, user_driving_routes_in_combined, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route, driving_times, earliest_departure_latest_arrival_minutes, walking_distance_from_passengers_origin_to_driver, walking_distance_from_driver_to_passengers_destination, ride_distances_of_passenger_driver_pairs, driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route, earliest_departure_latest_arrival = generate_data_and_preprocess(network_drive, network_combined, network_walk, network_drive_nodes, threshold_distance, today_datetime, M, N, W, R, visualize)

model = gp.Model("model")

class Carpooling:
    def get_assignments(self, x):
        assignments = []
        for key in passenger_driver_pairs.keys():
            if x[key].x > model.params.IntFeasTol:
                data = {'passenger': key[0], 'driver': key[1]}
                assignments.append(data)

        # to_csv: columns: passenger, driver
        df = pd.DataFrame(assignments)
        df.to_csv('assignments.csv', index=False)
        return assignments
    
    def get_users_going_by_its_own_car(self, y):
        users_going_by_its_own_car = list()
        for passenger in users_willing_to_be_passengers:
            if y[passenger].x > model.params.IntFeasTol:
                users_going_by_its_own_car.append(passenger)

        # to_csv: columns: passenger, going by its own car
        df = pd.DataFrame(users_going_by_its_own_car, columns=['passenger'])
        df.to_csv('users_going_by_its_own_car.csv', index=False)

        return users_going_by_its_own_car
    
    # get departure times of assigned passengers and drivers
    def get_departure_times(self, departure_time, x):
        departure_time_dict = dict()

        # Create an empty list to store results
        results_list = [] 

        for driver in unique_possible_drivers_list:
            if departure_time[driver].x > model.params.IntFeasTol:
                # convert departure time from minutes to datetime with today's date
                dep_time = datetime.datetime.combine(today_datetime, datetime.time(hour=int(np.floor(departure_time[driver].x / 60)), minute=int(np.floor(departure_time[driver].x % 60))))
                departure_time_dict[driver] = dep_time

                # Add driver data
                driver_data = {'User': driver,
                                'Driver or Passenger': 'Driver',
                                'Departure Time': dep_time,
                                'Arrival Time': dep_time + datetime.timedelta(minutes=driving_times[driver]),
                                'Earliest Departure Time': earliest_departure_latest_arrival[driver][0],
                                'Latest Arrival Time': earliest_departure_latest_arrival[driver][1]}
                results_list.append(driver_data)  # Using list and conversion

                for passenger in possible_passengers_for_driver[driver]:
                    if x[passenger, driver].x > model.params.IntFeasTol:
                        # Add passenger data
                        passenger_data = {'User': passenger,
                                        'Driver or Passenger': 'Passenger',
                                        'Departure Time': dep_time - datetime.timedelta(minutes=int(np.floor(walking_distance_from_passengers_origin_to_driver[passenger, driver]))),
                                        'Arrival Time': dep_time + datetime.timedelta(minutes=ride_distances_of_passenger_driver_pairs[passenger, driver] + walking_distance_from_passengers_origin_to_driver[passenger, driver] + walking_distance_from_driver_to_passengers_destination[passenger, driver]),
                                        'Earliest Departure Time': earliest_departure_latest_arrival[passenger][0],
                                        'Latest Arrival Time': earliest_departure_latest_arrival[passenger][1]}
                        results_list.append(passenger_data)  

        # Create DataFrame from list
        if results_list:
            results = pd.DataFrame(results_list)

        # Save to CSV
        results.to_csv('departure_arrival_times.csv', index=False)
        return departure_time_dict


    def visualize_results(self,x):
        # visualization of the results
        for driver in unique_possible_drivers_list:
            if sum(x[passenger, driver].x for passenger in possible_passengers_for_driver[driver]) > 0:
                # print("Driver ", driver)
                #driver_route = user_driving_routes[driver]
                driver_route_in_combined = user_driving_routes_in_combined[driver]
                for passenger in possible_passengers_for_driver[driver]:
                    if x[passenger, driver].x > 0.5:
                            # print("   Passenger ", passenger)
                            # plot_route_of_passenger_and_assigned_driver(network_drive, driver, passenger, driver_route, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route)
                            plot_route_of_passenger_and_assigned_driver_in_combined(network_combined, network_drive_nodes, driver, passenger, driver_route_in_combined, origin_destination_pairs, closest_driving_node_from_drivers_route_to_passengers_destination, closest_driving_node_from_passengers_origin_to_drivers_route)

    def run(self):
        x = model.addVars(passenger_driver_pairs.keys(), vtype=GRB.BINARY, name='x')
        y = model.addVars(possible_drivers_for_passenger.keys(), vtype=GRB.BINARY, name='y')
        departure_time = model.addVars(unique_possible_drivers_list, vtype=GRB.CONTINUOUS, name='departure_time')

        model.update()

        # Objective function
        # Minimize the total driving times of users who are using their own cars
        model.setObjective(gp.quicksum(y[u] * driving_times[u] for u in users_willing_to_be_passengers)) 

        model.update()

        # Constraints
        # One passenger can be in only one car
        model.addConstrs(gp.quicksum(x[u,v] for v in possible_drivers_for_passenger[u]) <= 1 for u in possible_drivers_for_passenger.keys()) 

        # If a passenger is not assigned to a ride, he/she should drive by itself
        model.addConstrs(gp.quicksum(x[u,v] for v in possible_drivers_for_passenger[u]) == 1 - y[u] for u in possible_drivers_for_passenger.keys()) 

        # Car capacity constraint
        model.addConstrs(gp.quicksum(x[u,v] for u in possible_passengers_for_driver[v]) <= car_capacity for v in unique_possible_drivers_list) 


        # Time related constraints

        # Constraints for departure and arrival times
        model.addConstrs(departure_time[v] >= earliest_departure_latest_arrival_minutes[v][0] for v in unique_possible_drivers_list)  # Departure time should be after or equal to the earliest departure time of each driver
        model.addConstrs(departure_time[v] >= (earliest_departure_latest_arrival_minutes[u][0] + walking_distance_from_passengers_origin_to_driver[u,v] - driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route[u,v]) * x[u,v] for v in possible_passengers_for_driver.keys() for u in possible_passengers_for_driver[v])  # Departure time of driver should be after or equal to the departure time of passenger plus walking time from driver
        model.addConstrs(departure_time[v] <= (earliest_departure_latest_arrival_minutes[u][1] - walking_distance_from_driver_to_passengers_destination[u,v] - ride_distances_of_passenger_driver_pairs[u,v] - driving_distances_from_drivers_origin_to_passengers_closest_point_to_drivers_route[u,v]) * x[u,v] + (earliest_departure_latest_arrival_minutes[v][1] - driving_times[v]) * (1 - x[u,v]) for v in possible_passengers_for_driver.keys() for u in possible_passengers_for_driver[v])  # Arrival time of driver should be before or equal to the arrival time of passenger plus walking time to driver
        # driving_distance_from_drivers_origin_to_passengers_closest_point_to_drivers_route
        # driving_distance_from_passengers_closest_node_to_drivers_destination

        model.update()

        print("Model is ready to be solved.")
        model.optimize()
        print("Model is solved.")

        if model.Status == gp.GRB.OPTIMAL:
            self.get_assignments(x)
            self.get_users_going_by_its_own_car(y)
            self.get_departure_times(departure_time, x)
            if not os.path.exists("visualization"):
                os.makedirs("visualization")

        elif model.Status == gp.GRB.INFEASIBLE:
            model.computeIIS()
            model.write("iis.ilp")

        if visualize:
            print("Visualization of the results is saved in the folder 'visualization'.")
            self.visualize_results(x)
    
Carpooling().run()