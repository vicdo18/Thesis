import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import random
import math
from collections import defaultdict
import json
import pprint

class BikeSimulator:
    def __init__(self, grid_file='', station_file='', pref_file=''):
       
        #self.stations_per_region = stations_per_region
        

        self.preferences={}  
        
        with open(pref_file) as f:
            self.preferences=json.load(f)

        with open(grid_file) as f:
            self.grid_size=len(json.load(f))

        with open(station_file) as f:
            file_stations=json.load(f)
            self.total_stations = len(file_stations)
        
        # Initialize stations
        self.stations = []
        #strategies = list(self.preferences['strategies']['parameters'].keys()] #['adaptive', 'conservative', 'aggressive']
        #strategy_index = 0

        for station_id in range(self.total_stations):
            
            x = file_stations[station_id]['coordinates'][0]
            y = file_stations[station_id]['coordinates'][1]

            # Custom demand parameters
            peak_morning = random.uniform(self.preferences['stations']['morning_peak'][0],self.preferences['stations']['morning_peak'][1])
            peak_evening = random.uniform(self.preferences['stations']['evening_peak'][0],self.preferences['stations']['evening_peak'][1])
            demand_scale = random.uniform(0.8, 1.2)

            # Custom daily budget per station - apply more money to stations with greater population serve
            daily_budget = self.preferences['stations']['daily_budget']* file_stations[station_id]['population_density']/file_stations[station_id]['population_max']
            #print(station_id, daily_budget)
            #random.randint(80, 150)
            
            #strategy = strategies[station_id % len(strategies)]
            #if strategy == 'aggressive':
            #    x, y = random.uniform(0, 3), random.uniform(0, 3)  # Για να είναι πιο κοντά σε χρήστες
            #else:
            #    x, y = random.uniform(0, self.grid_size), random.uniform(0, self.grid_size)

            station = {                   #class station with all its parameters
                'id': station_id,
                'region': (int(x), int(y)),
                'position': (x, y),
                'bikes': random.randint(5, self.preferences['stations']['capacity']-2), #initial bikes on station, between 5 and 18
                'capacity': self.preferences['stations']['capacity'], #bike storage capacity
                'daily_budget': daily_budget, #money available each day
                'remaining_budget': daily_budget, #current money available
                'incentive_strategy': 'conservative', #initial strategy, will be updated if dynamic
                'demand_history': [], 
                'demand': 0,
                'revenue': 0,
                'total_incentives_paid': 0,
                'bike_shortage_events': 0,
                'hourly_shortage_events':{},
                'bike_docking_shortage_events': 0,
                'hourly_docking_shortage_events':{},
                'successful_incentives': 0,
                'peak_morning': peak_morning, #when is the peak time in the morning (between 7-9)
                'peak_evening': peak_evening, #when is the peak time in the evening (between 16-18)
                'demand_scale': demand_scale, #scaling factor for demand
                'population_density': file_stations[station_id]['population_density'], #how many people served by the station
                'popularity': file_stations[station_id]['popularity'] #percentage of station grid population who want to use bike-sharing
            }
            #strategy_index += 1
            self.stations.append(station)
            #print(f"Station {station_id} strategy: {station['incentive_strategy']}")
        
        # Simulation parameters
        self.current_hour = 0
        self.day = 1
        self.trips_in_progress = []
        self.completed_trips = []
        
        # User category distribution
        self.user_categories = {
            1: {'description': 'loyal', 'acceptance_range': (
                    self.preferences['users']['loyal'][0],
                    self.preferences['users']['loyal'][1]
                )},  # 0-10% chance of accepting incentive
            2: {'description': 'flexible', 'acceptance_range': (
                    self.preferences['users']['flexible'][0],
                    self.preferences['users']['flexible'][1]
                )},  # 30-60% chance
            3: {'description': 'opportunistic', 'acceptance_range': (
                    self.preferences['users']['opportunistic'][0],
                    self.preferences['users']['opportunistic'][1]
                )}  # 60-100% chance
        }
        
        # Define maximum incentive and distance parameters
        self.max_incentive = self.preferences['stations']['max_incentive']
        self.max_redirection_distance = self.preferences['users']['max_redirection']  
        # Maximum distance users would consider for redirection
        
        # Init metrics tracking
        self.hourly_metrics = []
        self.daily_metrics = []

    
    def distance(self, station1, station2):
        """Calculate Euclidean distance between two stations"""
        x1, y1 = station1['position']
        x2, y2 = station2['position']
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def get_trip_price(self, distance):
        """Calculate price based on distance"""
        base_price = self.preferences['trips']['base_price']
        per_km_price = self.preferences['trips']['price_per_km']
        return base_price + (per_km_price * distance)


    def demand_curve(self, station, hour):
        """Generate custom demand based on time of day for this station"""
        #morning_peak = (station['capacity'] + 5) * np.exp(-0.5 * ((hour - station['peak_morning']) / 2) ** 2)
        #evening_peak = (station['capacity'] + 3) * np.exp(-0.5 * ((hour - station['peak_evening']) / 2) ** 2)
        #base_demand = self.preferences['demand']['base_demand']
        #return station['demand_scale'] * (base_demand + morning_peak + evening_peak)


        morning_peak = (station['population_density']*station['popularity']) * np.exp(-0.5 * ((hour - station['peak_morning']) / 2) ** 2)
        evening_peak = (station['population_density']*station['popularity']) * np.exp(-0.5 * ((hour - station['peak_evening']) / 2) ** 2)
        return int(round(station['demand_scale'] * (morning_peak + evening_peak),0))


    def demand_curve_base(self, station, hour):
        """Generate incentive factor for hour"""

        morning_peak = np.exp(-0.5 * ((hour - station['peak_morning']) / 2) ** 2)
        evening_peak = np.exp(-0.5 * ((hour - station['peak_evening']) / 2) ** 2)
        
        return (morning_peak + evening_peak)

    
        
    def predict_demand(self, station, hour):
        """Predict future demand for a station based on historical data"""
        history_hours=72
        #return demand curve values if history is less than 1 day
        #if len(station['demand_history']) < 24:
        if len(station['demand_history']) < 24:
            #return self.demand_curve(station, hour)
            return 2

        recent_history = station['demand_history'][-history_hours:]
        hour_position = hour % 24
        relevant_hours = [recent_history[i] for i in range(len(recent_history)) if i % 24 == hour_position]

        if not relevant_hours:
            return self.demand_curve(station, hour)

        return np.mean(relevant_hours) * (0.9 + 0.2 * random.random())# Use historical data with some recency bias
        recent_history = station['demand_history'][-history_hours:]  # Last 3 days
        hour_position = hour % 24
        relevant_hours = [recent_history[i] for i in range(len(recent_history)) if i % 24 == hour_position]
        
        if not relevant_hours:
            return self.demand_curve(hour, hour)
        
        return np.mean(relevant_hours) * (0.9 + 0.2 * random.random())  # Add some randomness
    
    def calculate_incentive(self, station, trip_price, hour, is_currently_low_on_bikes=False):
        #consider remaining money first
        if station['remaining_budget']==0:
            print (station['id'], 'out of money')
            return 0

        #basic strategies
        if self.preferences['strategies']['mode'] == 'none':
            return 0

        if self.preferences['strategies']['mode'] == 'static':
            if is_currently_low_on_bikes:
                return trip_price*self.preferences['strategies']['parameters']['static']['incentive_factor']
            else:
                return 0

        #risk-considering strategies
        """Calculate the incentive a station offers based on predicted demand and current bikes"""
        predicted_demand = self.predict_demand(station, hour)
        available_bikes = station['bikes']
        
        # Calculate bike shortage risk (negative = excess bikes, positive = shortage risk)
        bike_balance = available_bikes - predicted_demand
        
        # If station has excess bikes, don't offer incentives
        #if bike_balance >= 0 and not is_currently_low_on_bikes:
        #if not is_currently_low_on_bikes:
        #    return 0.0
        
        # Calculate shortage severity - higher for bigger shortages
        shortage_risk = min(1.0, max(0.0, -bike_balance / max(1, predicted_demand)))
        
        # Calculate incentive based on shortage risk and remaining budget
        budget_factor = min(1.0, station['remaining_budget'] / (station['daily_budget'] / 24))
        #if budget_factor==0:
        #    print('out of money')

        incentive_factor=0
        
        if station['incentive_strategy'] == 'aggressive':
            incentive_factor = self.preferences['strategies']['parameters']['aggressive']['incentive_factor']
        elif station['incentive_strategy'] == 'conservative':
            incentive_factor = self.preferences['strategies']['parameters']['conservative']['incentive_factor']
        else:  # adaptive
            # Adapt based on time of day and historical demand
            #time_factor = self.preferences['strategies']['parameters']['adaptive']['base_incentive_factor']
            #self.preferences['stations']['morning_peak'][0],self.preferences['stations']['morning_peak'][1]
            #if self.preferences['stations']['morning_peak'][0] <= hour <= self.preferences['stations']['morning_peak'][1] or self.preferences['stations']['evening_peak'][0] <= hour <= self.preferences['stations']['evening_peak'][1]:  # Peak hours
            #    time_factor = self.preferences['strategies']['parameters']['adaptive']['peak_incentive_factor']
            incentive_factor = self.demand_curve_base(station, hour)
        
        incentive = self.max_incentive * shortage_risk * budget_factor * incentive_factor
        
        # Apply current capacity adjustment (higher incentive if already low on bikes)
        if is_currently_low_on_bikes:
            capacity_factor = max(0.1, min(1.0, 1 - (available_bikes / station['capacity'])))
            incentive *= (1 + capacity_factor)
        
        # Cap incentive based on remaining budget
        return min(incentive, station['remaining_budget'])
    
    def update_incentive_strategy(self, station):

        if self.preferences['strategies']['mode'] != 'dynamic':
            station['incentive_strategy']=self.preferences['strategies']['mode']
            return
        
        """Update a station's incentive strategy based on performance"""
        # This is where game theory comes in - stations adapt to others
        nearby_stations = []
        
        for other_station in self.stations:
            if other_station['id'] != station['id']:
                if self.distance(station, other_station) < self.preferences['users']['max_redirection']:  
                    # Consider stations within distance 3
                    nearby_stations.append(other_station)
        
        if not nearby_stations:
            return

        #tit-for-tat
        
        
        # Calculate average performance metrics of nearby stations
        nearby_incentives = sum(s.get('total_incentives_paid', 0) for s in nearby_stations) / len(nearby_stations)
        nearby_success_rate = sum(s.get('successful_incentives', 0) for s in nearby_stations) / max(1, sum(s.get('total_incentives_paid', 0) for s in nearby_stations))
        
        # Calculate this station's success rate
        station_success_rate = station.get('successful_incentives', 0) / max(1, station.get('total_incentives_paid', 0))

        if self.preferences['strategies']['mode']=='dynamic':
            # Adjust strategy based on comparison
            if station.get('bike_shortage_events', 0) / max(1,station['demand']) > 0.3 :
                # If experiencing many bike shortages, be more aggressive
                station['incentive_strategy'] = 'aggressive'
                return
            if station.get('total_incentives_paid', 0) > nearby_incentives * 1.3 and station_success_rate < nearby_success_rate:
                # If spending much more than neighbors but with lower success rate, be more conservative
                station['incentive_strategy'] = 'conservative'
            #elif station.get('total_incentives_paid', 0) < nearby_incentives * 0.7 and station.get('bike_shortage_events', 0) > 5:
            elif station.get('total_incentives_paid', 0) < nearby_incentives * 0.7 and station.get('bike_shortage_events', 0) / max(1,station['demand']) > 0.3:
                # If spending much less than neighbors but still having shortages, be more aggressive
                station['incentive_strategy'] = 'aggressive'
            else:
                # Otherwise be adaptive
                station['incentive_strategy'] = 'adaptive'
            return
            
    
    def generate_trips(self):
        """Generate trips based on current demand"""
        
        for station in self.stations:
            
            idx=station['id']
            
            #calculate station demand for the current hour
            base_demand = self.demand_curve(station, self.current_hour)
            # Add randomness to demand
            actual_demand = int(round(base_demand * (0.9 + 0.2 * random.random()),0))
            station['demand']=actual_demand
            
            station['hourly_shortage_events'][self.current_hour]=0
            
            #print('processing station',idx, station['id'], self.current_hour, station['hourly_shortage_events'][self.current_hour])
            #print ("Demand at", idx, self.current_hour, base_demand, actual_demand)

            #for each trip request
            for _ in range(actual_demand):
                #print(_)
                # Select random origin station
                origin_idx = idx
                origin_station = station
                #print("request",_,"at",origin_station['id'], station['id'])
                
                # Don't start trip if no bikes available
                if origin_station['bikes'] <= 0:
                    #print('shortage')
                    try:
                        origin_station['hourly_shortage_events'][self.current_hour]+=1
                        origin_station['bike_shortage_events'] = origin_station.get('bike_shortage_events', 0) + 1
                        break
                    except:
                        print('error')
                        print(origin_idx, self.current_hour)
                        print(station['id'])
                        print(origin_station['id'])
                        exit()
                
                # Destination more likely to be within reasonable distance
                candidates = []
                candidate_stations=[]
                weights = []
                
                for i, dstation in enumerate(self.stations):
                    if i != origin_idx:
                        dist = self.distance(origin_station, dstation)
                        #8 blocks away or more
                        if dist>=self.preferences['users']['base_distance']: 
                            # Higher probability for closer stations, but allow some long trips
                            #probability = 1.0 / (1.0 + dist/self.preferences['users']['base_distance'])
                            probability = max(0,0.8 - abs(dist-self.preferences['users']['base_distance'])/self.preferences['users']['base_distance'])
                            candidates.append(i)
                            candidate_stations.append(dstation)
                            weights.append(probability)

                            
                
                # Normalize weights
                total_weight = sum(weights)
                weights = [w/total_weight for w in weights]
                
                # Select initial destination
                dest_idx = np.random.choice(candidates, p=weights)
                dest_station = self.stations[dest_idx]
                
                # Calculate trip details
                dist = self.distance(origin_station, dest_station)
                price = self.get_trip_price(dist)
                
                # Assign user category
                user_category = np.random.choice([1, 2, 3], p=self.preferences['users']['category_distribution'])  # Distribution of user types
                
                # Get user's acceptance probability range
                min_prob, max_prob = self.user_categories[user_category]['acceptance_range']
                acceptance_probability = min_prob + random.random() * (max_prob - min_prob)
                
                # Find nearby stations to the selected dest that might offer incentives
                # nearby stations must have spaces to dock
                nearby_stations = []
                for i, nstation in enumerate(candidate_stations):
                    if i != dest_idx:  # Don't include the original destination
                        redirect_dist = self.distance(dest_station, nstation)
                        if redirect_dist <= self.max_redirection_distance and nstation['bikes']<self.preferences['stations']['capacity']:
                            nearby_stations.append((i, station, redirect_dist))
                
                # Sort by distance (closest first)
                nearby_stations.sort(key=lambda x: x[2])
                
                # Calculate incentives from nearby stations
                incentives = []
                for i, istation, redirect_dist in nearby_stations:
                    # Check if station needs bikes
                    # low capacity is 20% of station capacity
                    incentive_amount = self.calculate_incentive(istation, self.current_hour, price, station['bikes'] < int(self.preferences['stations']['capacity']*0.2))
                    
                    if incentive_amount > 0:
                        # Adjust incentive attractiveness based on distance from original destination
                        distance_penalty = redirect_dist / self.max_redirection_distance
                        effective_incentive = incentive_amount * (1 - distance_penalty * 0.7)
                        
                        # Add to incentives list
                        incentives.append({
                            'station_id': i,
                            'amount': incentive_amount,
                            'effective_amount': effective_incentive,
                            'redirect_distance': redirect_dist
                        })
                
                # Sort incentives by effective amount (most attractive first)
                incentives.sort(key=lambda x: x['effective_amount'], reverse=True)
                
                # Determine final destination based on incentives and user category
                final_dest_idx = dest_idx
                applied_incentive = 0
                incentive_station = None
                
                
                if incentives:
                    # Consider best incentive first
                    best_incentive = incentives[0]
                    
                    # User decision based on category and incentive attractiveness
                    incentive_attractiveness = best_incentive['effective_amount'] #/ self.max_incentive
                    
                    # Calculate probability of accepting the incentive
                    if self.preferences['strategies']['mode']!="none":
                        accept_probability = min(1.0, acceptance_probability * incentive_attractiveness * 1.5)
                    else:
                        accept_probability = 0

                    #print('found', len(incentives), 'incentives, p=', accept_probability)
                    
                    if random.random() < accept_probability:
                        # User accepts the incentive
                        final_dest_idx = best_incentive['station_id']
                        applied_incentive = best_incentive['amount']
                        incentive_station = self.stations[final_dest_idx]
                        
                        # Update incentive station stats
                        incentive_station['remaining_budget'] -= applied_incentive
                        incentive_station['total_incentives_paid'] = incentive_station.get('total_incentives_paid', 0) + applied_incentive
                        incentive_station['successful_incentives'] = incentive_station.get('successful_incentives', 0) + 1
                
                # Get the final destination station
                final_dest_station = self.stations[final_dest_idx]

                # no matter if the original station was chosen or an alternative, if there is no space to dock, abort
                if final_dest_station['bikes']>self.preferences['stations']['capacity']:
                    final_dest_station['hourly_docking_shortage_events'][self.current_hour]+=1
                    final_dest_station['bike_docking_shortage_events'] = final_dest_station.get('bike_docking_shortage_events', 0) + 1
                    break
                
                # Recalculate distance and price if destination changed
                final_dist = dist
                if final_dest_idx != dest_idx:
                    final_dist = self.distance(origin_station, final_dest_station)
                    # Keep the original price (don't charge extra for redirection)
                
                # Trip duration depends on distance (1 hour per 5 distance units)
                duration = int(final_dist * 0.2 * 60) + random.randint(-5, 5)  # Duration in minutes
                
                trip = {
                    'origin': origin_idx,
                    'initial_destination': dest_idx,
                    'final_destination': final_dest_idx,
                    'distance': final_dist,
                    'price': price,
                    'incentive': applied_incentive,
                    'user_category': user_category,
                    'start_time': (self.day-1)*24*60 + self.current_hour * 60 + random.randint(0, 59),  # Start time in minutes
                    'duration': duration,
                    'redirected': final_dest_idx != dest_idx  # Flag if trip was redirected
                }
                
                # Remove bike from origin
                origin_station['bikes'] -= 1
                
                # Record demand for this station
                origin_station['demand_history'].append(1)
                
                # Add trip to in-progress trips
                self.trips_in_progress.append(trip)
        
        # For stations with no demand this hour, still record it
        for station in self.stations:
            if len(station['demand_history']) < (self.day - 1) * 24 + self.current_hour + 1:
                station['demand_history'].append(0)
    
    def process_completed_trips(self):
        """Process trips that have been completed in the current time step"""
        current_time = self.day * 24 * 60 + self.current_hour * 60
        #print(current_time)
        
        # Find completed trips
        remaining_trips = []
        for trip in self.trips_in_progress:
            if trip['start_time'] + trip['duration'] <= current_time:
                # Trip completed
                dest_station = self.stations[trip['final_destination']]
                
                # If destination has space
                if dest_station['bikes'] < dest_station['capacity']:
                    # Add revenue to origin station
                    self.stations[trip['origin']]['revenue'] += trip['price']
                    
                    # Return bike to destination
                    dest_station['bikes'] += 1
                    
                    # Record completed trip
                    self.completed_trips.append(trip)
                else:
                    # Destination is full, find nearest station with space
                    # print('destination full')
                    nearest_station_idx = None
                    min_dist = float('inf')
                    
                    for i, station in enumerate(self.stations):
                        if station['bikes'] < station['capacity']:
                            dist = self.distance(dest_station, station)
                            if dist < min_dist:
                                min_dist = dist
                                nearest_station_idx = i
                    
                    if nearest_station_idx is not None:
                        # Modify trip to go to nearest available station
                        trip['final_destination'] = nearest_station_idx
                        trip['distance'] += min_dist
                        trip['duration'] += int(min_dist * 0.2 * 60)
                        remaining_trips.append(trip)
                    else:
                        # No space anywhere, create overflow bikes (simulation edge case)
                        self.stations[trip['final_destination']]['bikes'] += 1
                        self.completed_trips.append(trip)
            else:
                # Trip still in progress
                remaining_trips.append(trip)
        
        self.trips_in_progress = remaining_trips
    
    def step(self):
        """Advance simulation by one hour"""

        # set hourly docking shortage events to 0 for all stations and update their strategy
        for station in self.stations:
            if (not self.current_hour in station['hourly_docking_shortage_events']):
                station['hourly_docking_shortage_events'][self.current_hour]=0
            self.update_incentive_strategy(station)
            
        # Generate new trips
        self.generate_trips()
        #print('---- generated trips -----', self.current_hour)
        #print(len(self.trips_in_progress))
        
        # Process completed trips
        self.process_completed_trips()
        #print('---- completed trips -----', self.current_hour)
        #print(len(self.completed_trips))
        #if (self.day-1)*24+self.current_hour==24:
        #    print(self.completed_trips)
        #    exit()

        
        
        # Record metrics
        self.record_metrics()

        #print((self.day-1)*24+self.current_hour)
        #pprint.pp(self.hourly_metrics[(self.day-1)*24+self.current_hour])
        
        # Update time
        self.current_hour += 1
        #print(self.current_hour, self.hourly_metrics[len(self.hourly_metrics)-1]['avg_bikes_per_station'])
        #print('------ hour change ------')
        #print(self.current_hour, sum(station['remaining_budget'] for station in self.stations) / len(self.stations))
        #print('------------')
        
        #input("Press the Enter key to continue: ")


        if self.current_hour >= 24:
            self.current_hour = 0
            self.day += 1
            
            # Reset daily budgets
            print('resetting stations')
            for station in self.stations:
                station['remaining_budget'] = station['daily_budget']
                #print(station['id'],station['remaining_budget'])
                #station['bike_shortage_events'] = 0
                #station['bikes']= random.randint(5, self.preferences['stations']['capacity']-2) #initial bikes on station, between 5 and 18
                
                # Update incentive strategies
                #if self.preferences['strategies']['mode']!='none':
                
    
    def record_metrics(self):
        """Record metrics for current hour"""
        total_bikes = sum(station['bikes'] for station in self.stations) + len(self.trips_in_progress)
        avg_bikes_per_station = sum(station['bikes'] for station in self.stations) / len(self.stations)
        
        # Find trips that were completed or started this hour
        current_hour_trips = [trip for trip in self.completed_trips if 
                             (self.day - 1) * 24 + self.current_hour == trip['start_time'] // 60]

        #print('current hour trips', len(current_hour_trips))

        
        total_incentives = sum(trip['incentive'] for trip in current_hour_trips)
        redirected_trips = sum(1 for trip in current_hour_trips if trip['redirected'])
        
        avg_incentive = total_incentives/max(1,len(current_hour_trips))
        avg_trip_price = sum(trip['price'] for trip in current_hour_trips)/max(1,len(current_hour_trips))
        avg_trip_distance = sum(trip['distance'] for trip in current_hour_trips)/max(1,len(current_hour_trips))
        
        
        # Calculate imbalance (standard deviation of bikes across stations)
        bikes_list = [station['bikes'] for station in self.stations]
        imbalance = np.std(bikes_list)

        shortages =sum(station['hourly_shortage_events'][self.current_hour] for station in self.stations)
        docking_shortages =sum(station['hourly_docking_shortage_events'][self.current_hour] for station in self.stations)

        demand = sum(station['demand'] for station in self.stations) / len(self.stations)
        
        hourly_data = {
            'day': self.day,
            'hour': self.current_hour,
            'total_bikes': total_bikes,
            'avg_bikes_per_station': avg_bikes_per_station,
            'imbalance': imbalance,
            'trips_completed': len(current_hour_trips),
            'redirected_trips': redirected_trips,
            'total_incentives': total_incentives,
            'shortage_events': shortages,
            'docking_shortage_events':docking_shortages,
            'avg_demand': demand,
            'avg_incentive':avg_incentive,
            'avg_trip_price':avg_trip_price,
            'avg_trip_distance':avg_trip_distance
        }
        #print(hourly_data['shortage_events'])
        
        self.hourly_metrics.append(hourly_data)
        
        # Record daily metrics at end of day
        if self.current_hour == 23:
            daily_trips = [trip for trip in self.completed_trips if (self.day - 1) * 24 <= trip['start_time'] // 60 < self.day * 24]
            redirected_daily = sum(1 for trip in daily_trips if trip['redirected'])
            
            daily_data = {
                'day': self.day,
                'total_trips': len(daily_trips),
                'redirected_trips': redirected_daily,
                'redirect_rate': redirected_daily / max(1, len(daily_trips)),
                'total_revenue': sum(trip['price'] for trip in daily_trips),
                'total_incentives': sum(trip['incentive'] for trip in daily_trips),
                'avg_incentive': sum(trip['incentive'] for trip in daily_trips) / max(1, redirected_daily),
                'bike_shortages': sum(station.get('bike_shortage_events', 0) for station in self.stations),
                'bike_docking_shortages': sum(station.get('bike_docking_shortage_events', 0) for station in self.stations)
            }
            
            self.daily_metrics.append(daily_data)
            #print(daily_data['bike_shortages'])
    
    def run_simulation(self, days=7):
        """Run simulation for specified number of days"""
        total_hours = days * 24
        for _ in range(total_hours):
            self.step()
        
        return {
            'hourly_metrics': self.hourly_metrics,
            'daily_metrics': self.daily_metrics,
            'completed_trips': self.completed_trips
        }
    
    def visualize_current_state(self):
        """Visualize the current state of the system"""
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Plot grid
        for i in range(self.grid_size + 1):
            ax.axhline(i, color='gray', alpha=0.3)
            ax.axvline(i, color='gray', alpha=0.3)
        
        # Plot stations
        x_coords = [station['position'][0] for station in self.stations]
        y_coords = [station['position'][1] for station in self.stations]
        sizes = [20 + station['bikes'] * 5 for station in self.stations]
        
        # Color based on need for bikes (red = needs bikes, blue = has excess)
        # Calculated as available bikes - predicted demand
        need_values = [station['bikes'] - self.predict_demand(station, self.current_hour) for station in self.stations]
        # Normalize to range -1 to 1 for colormap
        max_need = max(abs(min(need_values)), abs(max(need_values)))
        if max_need == 0:
            max_need = 1  # Avoid division by zero
            
        # Map to [-1, 1] range for colormap
        normalized_need = [n / max_need for n in need_values]
        
        # Create a custom colormap
        cmap = plt.cm.coolwarm
        
        # Plot stations
        scatter = ax.scatter(x_coords, y_coords, s=sizes, c=normalized_need, cmap=cmap, alpha=0.7)
        
        # Plot in-progress trips
        for trip in self.trips_in_progress:
            origin = self.stations[trip['origin']]['position']
            dest = self.stations[trip['final_destination']]['position']
            
            # Use different line style for redirected trips
            if trip.get('redirected', False):
                ax.plot([origin[0], dest[0]], [origin[1], dest[1]], 'g-', alpha=0.4)
                
                # Also show original destination with a dotted line
                orig_dest = self.stations[trip['initial_destination']]['position']
                ax.plot([origin[0], orig_dest[0]], [origin[1], orig_dest[1]], 'r--', alpha=0.2)
            else:
                ax.plot([origin[0], dest[0]], [origin[1], dest[1]], 'r-', alpha=0.2)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Bike Balance (Negative = Needs Bikes)')
        
        # Add title with current time
        ax.set_title(f'Bike Sharing System - Day {self.day}, Hour {self.current_hour}')
        ax.set_xlabel('X Coordinate')
        ax.set_ylabel('Y Coordinate')
        ax.set_xlim(-0.5, self.grid_size + 0.5)
        ax.set_ylim(-0.5, self.grid_size + 0.5)
        
        plt.tight_layout()
        return fig
    
    def create_animation(self, days=1):
        """Create an animation of the simulation over time"""
        # Reset simulation
        self.__init__(self.grid_size, self.stations_per_region)
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        def update(frame):
            ax.clear()
            
            # Advance simulation
            self.step()
            
            # Plot grid
            for i in range(self.grid_size + 1):
                ax.axhline(i, color='gray', alpha=0.3)
                ax.axvline(i, color='gray', alpha=0.3)
            
            # Plot stations
            x_coords = [station['position'][0] for station in self.stations]
            y_coords = [station['position'][1] for station in self.stations]
            sizes = [20 + station['bikes'] * 5 for station in self.stations]
            
            # Color based on need for bikes (red = needs bikes, blue = has excess)
            need_values = [station['bikes'] - self.predict_demand(station, self.current_hour) for station in self.stations]
            max_need = max(abs(min(need_values)), abs(max(need_values)))
            if max_need == 0:
                max_need = 1  # Avoid division by zero
                
            # Map to [-1, 1] range for colormap
            normalized_need = [n / max_need for n in need_values]
            
            scatter = ax.scatter(x_coords, y_coords, s=sizes, c=normalized_need, cmap=plt.cm.coolwarm, alpha=0.7)
            
            # Plot in-progress trips
            for trip in self.trips_in_progress:
                origin = self.stations[trip['origin']]['position']
                dest = self.stations[trip['final_destination']]['position']
                
                # Use different line style for redirected trips
                if trip.get('redirected', False):
                    ax.plot([origin[0], dest[0]], [origin[1], dest[1]], 'g-', alpha=0.4)
                    
                    # Also show original destination with a dotted line
                    orig_dest = self.stations[trip['initial_destination']]['position']
                    ax.plot([origin[0], orig_dest[0]], [origin[1], orig_dest[1]], 'r--', alpha=0.2)
                else:
                    ax.plot([origin[0], dest[0]], [origin[1], dest[1]], 'r-', alpha=0.2)
            
            # Add title with current time
            ax.set_title(f'Bike Sharing System - Day {self.day}, Hour {self.current_hour}')
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
            ax.set_xlim(-0.5, self.grid_size + 0.5)
            ax.set_ylim(-0.5, self.grid_size + 0.5)
            
            return scatter,
        
        anim = FuncAnimation(fig, update, frames=days*24, interval=200, blit=False)
        plt.close()  # Prevent displaying the figure
        
        return anim

    def plot_metrics(self):
        """Plot key metrics from the simulation"""
        if not self.hourly_metrics:
            print("No metrics to plot yet. Run the simulation first.")
            return
            
        # Convert metrics to numpy arrays for easier plotting
        hours = np.array([(m['day']-1)*24 + m['hour'] for m in self.hourly_metrics])
        days = np.array([m['day'] for m in self.hourly_metrics])
        avg_bikes = np.array([m['avg_bikes_per_station'] for m in self.hourly_metrics])
        imbalance = np.array([m['imbalance'] for m in self.hourly_metrics])
        trips = np.array([m['trips_completed'] for m in self.hourly_metrics])
        incentives = np.array([m['total_incentives'] for m in self.hourly_metrics])
        redirected = np.array([m['redirected_trips'] for m in self.hourly_metrics])
        shortages = np.array([m['shortage_events'] for m in self.hourly_metrics])
        docking_shortages = np.array([m['docking_shortage_events'] for m in self.hourly_metrics])
        demand = np.array([m['avg_demand'] for m in self.hourly_metrics])
        
        fig, axs = plt.subplots(6, 1, figsize=(6, 9), sharex=True)
        
        # Plot average bikes per station
        axs[0].plot(hours, avg_bikes)
        axs[0].set_ylabel('Avg Bikes per Station')
        axs[0].set_title('Average Bikes per Station Over Time')
        axs[0].grid(True)
        
        # Plot system imbalance
        axs[1].plot(hours, imbalance)
        axs[1].set_ylabel('System Imbalance')
        axs[1].set_title('Bike Distribution Imbalance (StdDev)')
        axs[1].grid(True)
        
        # Plot completed trips
        axs[2].plot(hours, trips)
        axs[2].plot(hours, demand)
        axs[2].set_ylabel('Trips Completed')
        axs[2].set_title('Trips Completed Each Hour')
        axs[2].grid(True)
        
        # Plot redirected trips
        axs[3].plot(hours, redirected, color='green')
        axs[3].set_ylabel('Redirected Trips')
        axs[3].set_title('Trips Redirected via Incentives Each Hour')
        axs[3].grid(True)
        
        # Plot incentives
        axs[4].plot(hours, incentives, color='purple')
        axs[4].set_ylabel('Total Incentives')
        axs[4].set_title('Total Incentives Paid Each Hour')
        axs[4].grid(True)

        # Plot shortages
        axs[5].plot(hours, shortages, color='purple')
        axs[5].set_ylabel('Total Shortages')
        axs[5].set_title('Total Shortages Each Hour')
        axs[5].grid(True)

        # Plot docking shortages
        axs[5].plot(hours, docking_shortages, color='red')
        axs[5].set_ylabel('Total Shortages')
        axs[5].set_title('Total Shortages Each Hour')
        axs[5].grid(True)
        
        # Set x-axis labels with day markers
        axs[5].set_xlabel('Hour')
        
        # Add day markers
        for day in range(1, int(max(days))+1):
            for ax in axs:
                ax.axvline(x=day*24, color='r', linestyle='--', alpha=0.3)
                
        plt.tight_layout()
        return fig
        
    def analyze_incentive_effectiveness(self):
        """Analyze the effectiveness of incentives by user category"""
        if not self.completed_trips:
            print("No completed trips to analyze. Run the simulation first.")
            return
        
        # Group trips by user category
        trips_by_category = {1: [], 2: [], 3: []}
        for trip in self.completed_trips:
            category = trip.get('user_category', 1)  # Default to category 1 if missing
            trips_by_category[category].append(trip)
        
        # Calculate statistics for each category
        category_stats = {}
        for category, trips in trips_by_category.items():
            total_trips = len(trips)
            redirected_trips = sum(1 for trip in trips if trip.get('redirected', False))
            incentives_paid = sum(trip.get('incentive', 0) for trip in trips)
            
            category_stats[category] = {
                'total_trips': total_trips,
                'redirected_trips': redirected_trips,
                'redirect_rate': redirected_trips / max(1, total_trips),
                'total_incentives': incentives_paid,
                'avg_incentive': incentives_paid / max(1, redirected_trips),
                'incentive_per_trip': incentives_paid / max(1, total_trips)
            }
        
        # Calculate overall statistics
        total_trips = len(self.completed_trips)
        redirected_trips = sum(1 for trip in self.completed_trips if trip.get('redirected', False))
        total_incentives = sum(trip.get('incentive', 0) for trip in self.completed_trips)
        
        overall_stats = {
            'total_trips': total_trips,
            'redirected_trips': redirected_trips,
            'redirect_rate': redirected_trips / max(1, total_trips),
            'total_incentives': total_incentives,
            'avg_incentive': total_incentives / max(1, redirected_trips)
        }
        
        return {
            'category_stats': category_stats,
            'overall_stats': overall_stats
        }
    
    def analyze_station_performance(self):
        """Analyze and report on station performance"""
        if not self.daily_metrics:
            print("No metrics to analyze yet. Run the simulation first.")
            return
            
        # Calculate metrics by station
        station_metrics = []
        for i, station in enumerate(self.stations):
            # Calculate trips originating and ending at this station
            origin_trips = [trip for trip in self.completed_trips if trip['origin'] == i]
            dest_trips = [trip for trip in self.completed_trips if trip['final_destination'] == i]
            redirected_to = [trip for trip in self.completed_trips if trip['final_destination'] == i and trip['initial_destination'] != i]
            redirected_from = [trip for trip in self.completed_trips if trip['initial_destination'] == i and trip['final_destination'] != i]
            
            metrics = {
                'station_id': i,
                'region': station['region'],
                'revenue': station['revenue'],
                'total_incentives': station.get('total_incentives_paid', 0),
                'profit': station['revenue'] - station.get('total_incentives_paid', 0),
                'trips_originated': len(origin_trips),
                'trips_ended': len(dest_trips),
                'redirected_to': len(redirected_to),
                'redirected_from': len(redirected_from),
                'redirection_net': len(redirected_to) - len(redirected_from),
                'avg_incentive': station.get('total_incentives_paid', 0) / max(1, len(redirected_to)),
                'strategy': station['incentive_strategy']
            }
            
            station_metrics.append(metrics)
            
        # Sort stations by profit
        station_metrics.sort(key=lambda x: x['profit'], reverse=True)
        
        # Analyze strategies
        strategies = defaultdict(list)
        for metric in station_metrics:
            strategies[metric['strategy']].append({
                'profit': metric['profit'],
                'incentives': metric['total_incentives'],
                'redirected_to': metric['redirected_to']
            })
        
        strategy_performance = {
            strategy: {
                'count': len(data),
                'avg_profit': sum(item['profit'] for item in data) / len(data) if data else 0,
                'avg_incentives': sum(item['incentives'] for item in data) / len(data) if data else 0,
                'avg_redirections': sum(item['redirected_to'] for item in data) / len(data) if data else 0,
                'total_profit': sum(item['profit'] for item in data),
                'total_incentives': sum(item['incentives'] for item in data)
            }
            for strategy, data in strategies.items()
        }
        
        # Analyze regions
        region_performance = defaultdict(lambda: {'profit': 0, 'stations': 0, 'incentives': 0, 'redirections': 0})
        for metric in station_metrics:
            region = metric['region']
            region_performance[region]['profit'] += metric['profit']
            region_performance[region]['stations'] += 1
            region_performance[region]['incentives'] += metric['total_incentives']
            region_performance[region]['redirections'] += metric['redirected_to']
        
        for region, data in region_performance.items():
            data['avg_profit'] = data['profit'] / data['stations']
            data['avg_incentives'] = data['incentives'] / data['stations']
            data['avg_redirections'] = data['redirections'] / data['stations']
        
        # Sort regions by average profit
        sorted_regions = sorted(region_performance.items(), key=lambda x: x[1]['avg_profit'], reverse=True)
        for s in strategy_performance:
            print(f"[DEBUG] {s}: count = {strategy_performance[s]['count']}")
        return {
            'top_stations': station_metrics[:10],  # Top 10 stations
            'bottom_stations': station_metrics[-10:],  # Bottom 10 stations
            'strategy_performance': strategy_performance,
            'top_regions': sorted_regions[:5],  # Top 5 regions
            'bottom_regions': sorted_regions[-5:]  # Bottom 5 regions
        }
        
    def analyze_user_categories(self):
        """Analyze the behavior and impact of different user categories"""
        if not self.completed_trips:
            print("No completed trips to analyze. Run the simulation first.")
            return
            
        # Group trips by category
        categories = {1: [], 2: [], 3: []}
        for trip in self.completed_trips:
            cat = trip.get('user_category', 1)
            categories[cat].append(trip)
            
        # Calculate metrics for each category
        category_metrics = {}
        for cat, trips in categories.items():
            total = len(trips)
            redirected = sum(1 for t in trips if t.get('redirected', False))
            total_distance = sum(t['distance'] for t in trips)
            total_revenue = sum(t['price'] for t in trips)
            total_incentives = sum(t.get('incentive', 0) for t in trips)
            
            category_metrics[cat] = {
                'description': self.user_categories[cat]['description'],
                'total_trips': total,
                'redirected_trips': redirected,
                'redirection_rate': redirected / max(1, total),
                'avg_trip_distance': total_distance / max(1, total),
                'avg_revenue': total_revenue / max(1, total),
                'total_incentives': total_incentives,
                'avg_incentive': total_incentives / max(1, redirected) if redirected > 0 else 0
            }
            
        return category_metrics
    
    def visualize_user_category_performance(self):
        """Create visualizations of user category performance metrics"""
        category_metrics = self.analyze_user_categories()
        if not category_metrics:
            return None
            
        # Prepare data for plotting
        categories = list(category_metrics.keys())
        descriptions = [f"Cat {c} ({category_metrics[c]['description']})" for c in categories]
        redirection_rates = [category_metrics[c]['redirection_rate'] * 100 for c in categories]
        avg_incentives = [category_metrics[c]['avg_incentive'] for c in categories]
        total_trips = [category_metrics[c]['total_trips'] for c in categories]
        
        fig, axs = plt.subplots(1, 3, figsize=(15, 5))
        
        # Plot redirection rates
        axs[0].bar(descriptions, redirection_rates)
        axs[0].set_title('Redirection Rate by User Category')
        axs[0].set_ylabel('Redirection Rate (%)')
        axs[0].set_ylim([0, 100])
        
        # Plot average incentive amount
        axs[1].bar(descriptions, avg_incentives)
        axs[1].set_title('Average Incentive by User Category')
        axs[1].set_ylabel('Avg Incentive Amount')
        
        # Plot trip distribution
        axs[2].pie(total_trips, labels=descriptions, autopct='%1.1f%%')
        axs[2].set_title('Trip Distribution by User Category')
        
        plt.tight_layout()
        return fig
    
    def visualize_incentive_effectiveness(self):
        """Create visualization of incentive effectiveness"""
        if not self.daily_metrics:
            print("No metrics to visualize yet. Run the simulation first.")
            return None
            
        # Extract metrics
        days = [m['day'] for m in self.daily_metrics]
        redirect_rates = [m['redirect_rate'] * 100 for m in self.daily_metrics]
        avg_incentives = [m['avg_incentive'] for m in self.daily_metrics]
        
        fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Plot redirection rate over time
        axs[0].plot(days, redirect_rates, 'g-o')
        axs[0].set_ylabel('Redirection Rate (%)')
        axs[0].set_title('Trip Redirection Rate by Day')
        axs[0].grid(True)
        
        # Plot average incentive over time
        axs[1].plot(days, avg_incentives, 'b-o')
        axs[1].set_xlabel('Day')
        axs[1].set_ylabel('Average Incentive')
        axs[1].set_title('Average Incentive Amount by Day')
        axs[1].grid(True)
        
        plt.tight_layout()
        return fig

    def plot_game_theory_analysis(self):
        """Plot game theory analysis of station strategies"""
        if not self.completed_trips:
            print("No completed trips to analyze. Run the simulation first.")
            return
            
        # Get strategy performance data
        analysis = self.analyze_station_performance()
        strategy_perf = analysis['strategy_performance']

        # Ensure all strategies are included even if no data
        all_strategies = ['adaptive', 'conservative', 'aggressive']
        for s in all_strategies:
            if s not in strategy_perf:
                strategy_perf[s] = {
                    'count': 0,
                    'avg_profit': 0,
                    'avg_incentives': 0,
                    'avg_redirections': 0
                }

        # Prepare data for plotting
        strategies = all_strategies
        counts = [strategy_perf[s]['count'] for s in strategies]
        avg_profits = [strategy_perf[s]['avg_profit'] for s in strategies]
        avg_incentives = [strategy_perf[s]['avg_incentives'] for s in strategies]
        avg_redirections = [strategy_perf[s]['avg_redirections'] for s in strategies]
        
        # Create figure
        fig, axs = plt.subplots(2, 2, figsize=(12, 10))

        # Plot strategy distribution
        axs[0, 0].bar(strategies, counts)
        axs[0, 0].set_title('Distribution of Station Strategies')
        axs[0, 0].set_ylabel('Number of Stations')
        
        # Plot average profit by strategy
        axs[0, 1].bar(strategies, avg_profits)
        axs[0, 1].set_title('Average Profit by Strategy')
        axs[0, 1].set_ylabel('Profit')
        
        # Plot average incentives by strategy
        axs[1, 0].bar(strategies, avg_incentives)
        axs[1, 0].set_title('Average Incentives Paid by Strategy')
        axs[1, 0].set_ylabel('Incentives')
        
        # Plot average redirections by strategy
        axs[1, 1].bar(strategies, avg_redirections)
        axs[1, 1].set_title('Average Successful Redirections by Strategy')
        axs[1, 1].set_ylabel('Redirected Trips')
        
        plt.tight_layout()
        return fig

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super(NpEncoder, self).default(obj)

# Example usage demonstrating the simulator
if __name__ == "__main__":
    # Create simulator with smaller grid for testing
    

    for mode in ['none','conservative','adaptive','aggressive','dynamic','static']:
    #for mode in ['static','dynamic']:
        print ('=========')
        print (mode)
        print ('=========')
        simulator = BikeSimulator(
            grid_file='data/population_density_250000_100.json', 
            station_file='data/bike_stations_250000_100.json', 
            pref_file='data/options.json'
        )
        simulator.preferences['strategies']['mode']=mode
        # Run simulation for 7 days
        results = simulator.run_simulation(days=5)
    
        # Serializing json (Metrics)
        json_object = json.dumps(results, indent=4, cls=NpEncoder)
        # --- ΑΛΛΑΓΗ 1: Προσθέσαμε το 'outputs/' ---
        filename = 'outputs/metrics_' + mode + '.json'
        
        with open(filename, "w") as outfile:
            outfile.write(json_object)
            print(f"Metrics data saved to {filename}")
    
        # Analyze incentive effectiveness by user category
        incentive_analysis = simulator.analyze_incentive_effectiveness()
        # --- ΑΛΛΑΓΗ 2: Προσθέσαμε το 'outputs/' ---
        filename = 'outputs/incentive_analysis_' + mode + '.json'
        
        # --- ΔΙΟΡΘΩΣΗ BUG: Γράφουμε το incentive_analysis, όχι το results ---
        incentive_json = json.dumps(incentive_analysis, indent=4, cls=NpEncoder)
        
        with open(filename, "w") as outfile:
            outfile.write(incentive_json)
            print(f"Incentive data saved to {filename}")
            
        print("\nOverall Incentive Effectiveness:")
        print(f"  Total trips: {incentive_analysis['overall_stats']['total_trips']}")
        print(f"  Redirected trips: {incentive_analysis['overall_stats']['redirected_trips']} " +
              f"({incentive_analysis['overall_stats']['redirect_rate']*100:.1f}%)")
        print(f"  Total incentives paid: ${incentive_analysis['overall_stats']['total_incentives']:.2f}")
        print(f"  Average incentive: ${incentive_analysis['overall_stats']['avg_incentive']:.2f}")
    
    # Show user category analysis visualization
    #cat_fig = simulator.visualize_user_category_performance()
    #plt.show()
    
    # Show game theory analysis
    #game_fig = simulator.plot_game_theory_analysis()
    #plt.show()
    
    # Show incentive effectiveness over time
    #incentive_fig = simulator.visualize_incentive_effectiveness()
    #plt.show()

    #anim = simulator.create_animation(days=1)
    #anim.save(filename="ffmpeg_example.mp4", writer="ffmpeg")




