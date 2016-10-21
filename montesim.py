#!/usr/bin/env python3
###############################################################################
# Copyright 2015-2016 Patrick Ingham - License: BSD 2-Clause License 
# 
# This file is a part of msu-bikedata, which currently licensed for public
# use and distribution under terms of the BSD License. Refer to the 'License'
# section of README.md in the project root directory file for full copyright 
# information. 
# 
###############################################################################
# 
# This file is used to run the montecarlo simulations on compiled data and 
# manage the timing of the other pieces of software. Effectively treated as a 
# main python file from which the others are intersected. 
# 
###############################################################################
import yaml 
import math 
import time 
import random 
import csv 
import os 
import logging 

import compiledata 
import obsprocrep 
import procopt
import visrep  

DEFLOGFILE = 'data/montesim.log' 

def _logging_setup(): 
    logging.basicConfig(format='MONTESIM:%(levelname)s:%(asctime)s:  %(message)s',
            filename=DEFLOGFILE, level=logging.INFO)
    logging.info('--- Starting new montesim logging ---')


def get_coord_distance(c1, c2):
    """
    Coordinates c1 and c2 are tuples of (x, y) or (longitude, lattitude)  
    """
    #print(c1, c2) 
    R = 6371000  # Radius of the earth in meters
    lat1 = math.radians(c1[1])
    lat2 = math.radians(c2[1])

    lon1 = math.radians(c1[0])
    lon2 = math.radians(c2[0]) 
    
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * \
            math.sin(dlon/2)**2
    
    c = 2 * math.asin(math.sqrt(a)) 

    return c * R 


def _tup_coords_dict(c): 
    x = c[0] 
    y = c[1] 
    return {'x': x, 'y': y} 


def name_rackpad(coords, n='def'): 
    n = "{}_({}, {})".format(n, coords[0], coords[1]) 
    return n 


class Biker: 
    def __init__(self, name, schedule, 
            starting_coords=(-111.048614, 45.670256), 
            starting_build=None): 
        self._biker_name = str(name) 
        
        self._coordinates = starting_coords 
        self._building = starting_build

        # schedule is a list of buildings the Biker would like to go to. 
        self._schedule = schedule 

        # item num is where the schedule is at. 
        self._item_num = 0 

    
    def get_name(self): 
        return self._biker_name 

    
    def get_coords(self): 
        return self._coordinates 


    def get_location(self): 
        return self._building, self._coordinates 

    
    def dict_dump(self): 
        build, coords = self.get_location() 
        d = {
                'name': self.get_name(), 
                #'building': build, 
                #'coordinates': coords, 
                'schedule': self._schedule, 
                'step_num': self._item_num
            }
        return d 

                
    def relocate_to(self, new_coordinates, new_building): 
        # TODO: Log this 
        cur_build, cur_coords = self.get_location() 
        logging.debug("relocating Biker({}) from {} {} to {} {}".format(self.get_name(), 
            cur_build, cur_coords, new_building, new_coordinates)) 
        self._coordinates = new_coordinates 
        self._building = new_building 
        return 0 


    def get_destination(self): 
        # does not iterate! 
        i = self._item_num 
        if i >= len(self._schedule): 
            return None 

        else: 
            return self._schedule[i] 
    

    def advance_schedule(self): 
        # iterates. 
        # first get previous number and what the new number will be 
        pi = self._item_num 
        ni = self._item_num + 1 
        
        # iterate 
        self._item_num += 1

        if pi >= len(self._schedule): 
            # The previous number was still too high. 
            return -1, -1 

        elif ni >= len(self._schedule): 
            # the new number will be too high. 
            return -2, -2 

        else:
            # returns the previous/current entry, and the new entry
            return self._schedule[pi], self._schedule[ni] 


class RackPad: 
    def __init__(self, building_name, rack_name, coordinates, max_bikes, 
            racks=1): 
        self._rack_name = str(rack_name) 
        self._building_name = str(building_name) 

        self._longitude = coordinates[0] 
        self._lattitude = coordinates[1] 
        
        self._satisfied_requests = 0 
        self._unsatisfied_requests = 0 
        self._total_requests = 0 

        # The number of racks on the pad
        self._rack_count = racks 

        # the maximum number of slots available. 
        self._max_bikes = int(max_bikes)

        # a list to store all the bikes 
        self._rack_slots = [] 


    def get_building_name(self): 
        return self._building_name 

    
    def count_empty_slots(self): 
        full_slots = len(self._rack_slots) 
        return self._max_bikes - full_slots 


    def register_request(self): 
        self._total_requests += 1 
        if self.has_empty_slots() is True: 
            self._satisfied_requests += 1 

        else: 
            self._unsatisfied_requests += 1 


    def has_empty_slots(self): 
        full_slots = len(self._rack_slots) 
        if full_slots >= self._max_bikes: 
            return False

        else: 
            return True 

    
    def dict_dump(self): 
        c = self.get_coordinates() 
        d = {
                'lat': c[1], 
                'lon': c[0], 
                'cap': self._max_bikes, 
                'racks': self._rack_count, 
                'open cap': self.count_empty_slots(), 
                'requests': {
                    'sat': self._satisfied_requests, 
                    'unsat': self._unsatisfied_requests, 
                    'total': self._total_requests
                    },
                'bikes': []
            }
        for b in self._rack_slots: 
            d['bikes'].append(b.dict_dump()) 

        return d 


    def get_coordinates(self): 
        t = (self._longitude, self._lattitude) 
        return t 


    def add_biker(self, biker): 
        """
        Does not check if a bike can be added. Adds it regardless. 
        """
        biker.relocate_to(self.get_coordinates(), self.get_building_name())
        self._rack_slots.append(biker) 
        return 0 

    
    def get_name(self): 
        return self._rack_name 


    def remove_biker(self, biker_name): 
        """
        Rather slow because it uses loops. 
        """
        rb = str(biker_name) 

        new_racks = [] 
        num_removed = 1 
        for b in self._rack_slots:
            if b.get_name() == rb: 
                num_removed -= 1 
                continue 

            else: 
                new_racks.append(b) 

        self._rack_slots = new_racks 
        return num_removed


class Locale: 
    def __init__(self, name, rack_precursors, occupancy): 
        self._locale_name = name 
        self._building_pop = occupancy 

        self._bike_racks = [] 
        for rp in rack_precursors:
            # (x, y, number of racks, capacity) 
            c = (rp['lon'], rp['lat']) 
            n = name_rackpad(c, n=name) 
            rn = rp['racks'] 
            
            s = rp['cap'] 
            r = RackPad(self._locale_name, n, c, s, racks=rn) 

            self._bike_racks.append(r) 

    def get_name(self): 
        return self._locale_name 

    
    def _total_openings(self): 
        spots = 0 
        for rp in self._bike_racks: 
            spots += rp._max_bikes 

        return spots 
    

    def dict_dump(self): 
        d = { 
                'building': self.get_name(), 
                'occupancy': self._building_pop, 
                'total cap': self._total_openings(), 
                'rack pads': []
            }

        open_cap = 0 
        for rp in self._bike_racks: 
            dn = rp.dict_dump() 
            open_cap += dn['open cap'] 
            d['rack pads'].append(dn) 

        d['total open cap'] = open_cap 

        return d 


    def remove_biker(self, biker_name): 
        total_r = 0 
        for br in self._bike_racks: 
            total_r = br.remove_biker(biker_name) 
        
        return total_r


    def all_pads(self): 
        r = list(self._bike_racks) 
        return r 


    def has_empty_rack(self): 
        for r in self._bike_racks: 
            if r.has_empty_slots() is True: 
                return True 
        return False 


    def nearest_pad(self, coords, exclude_pads=[]): 
        """
        Finds the nearest bike pad attached to this Locale and returns it, 
        does not check if spots are open on that pad. 
        """
        min_dist = None
        cur_best = None 
        for rp in self._bike_racks:
            padn = rp.get_name() 

            if padn in exclude_pads: 
                continue 

            c = rp.get_coordinates() 
            dist = get_coord_distance(coords, c) 

            if min_dist is None: 
                min_dist = dist 
                cur_best = rp 

            elif dist < min_dist: 
                min_dist = dist 
                cur_best = rp 

        return cur_best 


    def nearest_available_pad(self, start_coords): 
        if self.has_empty_rack() is False: 
            return None 

        el = [] 
        while True: 
            r = self.nearest_pad(start_coords, exclude_pads=el) 
            if r is None: 
                break 

            if r.has_empty_slots() is True: 
                return r 

            else: 
                el.append(r.get_name()) 
                
        return None 


class Campus:
    """
    A campus is there to hold all other locales and work on finding paths. 
    """
    def __init__(self, info): 
        self._locales_db = info.pop('locs') 
        self._locales_names = info.pop('build_names') 
        
        self._max_pop = info.pop('total_occ') 
        self._max_bike_cap = info.pop('total_bike_cap') 

        # campus is a semi-unique locale because it should never be a 
        # destination
        self._campus_db = info.pop('campus')
        self._campus = Locale('campus', self._campus_db['rack_pads'], 
                self._campus_db['occupancy']) 
        
        self._locales = {} 
        for building in self._locales_names: 
            v = self._locales_db[building] 
            self._locales[building] = Locale(building, v['rack_pads'], 
                    v['occupancy']) 


    def all_pads(self): 
        pads = [] 

        # Non-campus locales 
        for l in self._locales_names: 
            loc = self._locales[l] 
            pads += loc.all_pads() 

        pads += self._campus.all_pads() 
        return pads 

    
    def dict_dump(self): 
        d = {
                'max pop': self._max_pop, 
                'bike cap': self._max_bike_cap, 
                'locales': []
            }
        for l in self._locales_names: 
            loc = self._locales[l] 
            d['locales'].append(loc.dict_dump())

        d['locales'].append(self._campus.dict_dump())

        return d 


    def get_locale(self, loc_name): 
        if loc_name == 'campus': 
            return self._campus 

        else: 
            return self._locales.get(loc_name)

    
    def nearest_pad(self, start_coords, end_build): 
        """
        Does not check spot availability

        returns the nearest possible bike pad. 
        """
        logging.debug("finding nearest {} rack from {}".format(end_build, 
            start_coords)) 
        end_locale = self._locales[end_build] 
        end_pad = end_locale.nearest_pad(start_coords) 
        return end_pad

    
    def nearest_available_pad(self, start_coords, end_build): 
        """
        Does check for spot availability, does not check other locales 

        returns nearest possible bike pad at the end building.
        """
        end_locale = self._locales[end_build] 
        end_pad = end_locale.nearest_available_pad(start_coords) 
        return end_pad


    def nearest_campus_wide_pad(self, start_coords, ignore_start=True): 
        """
        Returns the nearest, objective pad to the start coordinates. 

        If ignore_start is set to True, then identical coordinates will get 
        skipped past. 
        """
        ap = self.all_pads() 
        min_dist = None 
        pad = None 

        for p in ap: 
            if p.has_empty_slots() is not True: 
                continue 
            
            pcoords = p.get_coordinates() 
            dist = get_coord_distance(start_coords, pcoords)

            if pcoords[0] == start_coords[0] and \
                pcoords[1] == start_coords[1] and \
                ignore_start is True: 
                continue 

            if min_dist is None: 
                min_dist = dist 
                pad = p 

            elif min_dist > dist: 
                min_dist = dist 
                pad = p 

        return pad 


    def relocate_biker(self, biker, end_pad): 
        biker_name = biker.get_name() 
        # 1. Remove the biker from all possible pads. 
        ap = self.all_pads() 
        for p in ap: 
            p.remove_biker(biker_name) 

        # 2. Now that they are 'nowhere', put them at the new pad
        end_pad.add_biker(biker)  
        # NOTE: add_biker will set the new information in the Biker object. 



class ScheduleGen: 
    def __init__(self, info, 
            starting_coords=[
                (-111.048614, 45.670256),  # near Johnstone
                (-111.052060, 45.665160),  # corner of 11th and Grant
                (-111.059246, 45.671103),  # Grant Chamberlain
                (-111.045374, 45.669165)]  # 6th and Cleveland
            ): 
        self._building_list = tuple(info['build_names']) 
        self._full_schedule = [] 
        self._names_list = [] 
        
        self._regen_data = [] 
        for building in self._building_list: 
            newb = info['locs'][building].copy() 
            x_range = newb['occupancy'] 

            rd_ent = (building, x_range) 
            self._regen_data.append(rd_ent) 

            for x in range(x_range): 
                self._full_schedule.append(building) 

        random.shuffle(self._full_schedule) 
        self._start_coords = starting_coords 

    
    def _refresh_scheduling(self): 
        for i in self._regen_data: 
            x_range = i[1] 
            building = i[0] 
            for x in range(x_range): 
                self._full_schedule.append(building) 

        random.shuffle(self._full_schedule) 


    def _get_entries(self, entries=5): 
        if len(self._full_schedule) < entries: 
            logging.info("Refreshing schedule") 
            self._refresh_scheduling() 
        
        r = [] 
        for x in range(entries): 
            n = str(self._full_schedule.pop()) 
            r.append(n) 

        return r 
    
    def _get_new_name(self, characters=7, max_tries=10): 
        l = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        n = '' 
        tries = 0 
        while True:
            if tries > max_tries: 
                n = None
                break

            for x in range(characters): 
                n += random.choice(l) 

            if n not in self._names_list: 
                self._names_list.append(n) 
                break 

            tries += 1 

        return n 


    def generate_new_Biker(self, schedule_entries=5, name_len=7): 
        sched = self._get_entries(schedule_entries)
        name = self._get_new_name(characters=name_len) 
        coords = random.choice(self._start_coords)

        b = Biker(name, sched, starting_coords=coords) 

        return b


def load_compiled_data(config): 
    data_loc = config['compiled data'] 

    if os.path.isfile(data_loc): 
        with open(data_loc, 'r') as f: 
            r1 = yaml.load(f) 
            return r1.copy() 

    else:
        _brf = config['rack file'] 
        _bof = config['building file']
        _oef = config['entrances file'] 
        _min_occ = config['minimum occupancy'] 

        r1 = compiledata.compile_data(bike_rack_file=_brf, buildings_file=_bof, 
                min_occupancy=_min_occ, ent_file=_oef) 
        with open(data_loc, 'w') as f: 
            yaml.dump(r1, f, explicit_start=True, default_flow_style=False) 
        return r1 


def calc_dists(start_pos, end_build, ideal_end_pad, real_end_pad): 
    """
    Calculates the distance between the ideal path and the real path. 
    """
    min_dist = 0.0 
    act_dist = 0.0 
    
    iepc = ideal_end_pad.get_coordinates() 
    repc = real_end_pad.get_coordinates() 

    if ideal_end_pad.get_name() == real_end_pad.get_name(): 
        return round(get_coord_distance(start_pos, iepc), 2), round(0.0, 2) 
    
    # If it is away from the end building, add in the path from the 
    # real_end_pad over to the ideal_end_pad
    if real_end_pad.get_building_name() != end_build: 
        act_dist += get_coord_distance(iepc, repc)

    min_dist += get_coord_distance(start_pos, iepc)
    act_dist += get_coord_distance(start_pos, repc)

    return round(act_dist, 2), round(act_dist - min_dist, 2)


def monte_test_once(cd, data_dir='data', bikers=1000, start_seed=1036, 
        sleep_delay=0.0, sched_len=5, record_tick=150):
    _start_time = time.time() 
    random.seed(start_seed)

    datalogs_f = '{}/datalogs.yml'.format(data_dir)
    _ylogfile = open(datalogs_f, 'w') 
    
    comp_dat_lateruse = cd.copy()
    SG = ScheduleGen(cd) 
    camp = Campus(cd)

    bikers_list = [] 
    for x in range(bikers): 
        bikers_list.append(SG.generate_new_Biker(schedule_entries=sched_len)) 
    
    monte_f = '{}/goldwater_monte.csv'.format(data_dir)
    m_csv_f = open(monte_f, 'w') 
    csv_header = ('step_num', 'rider_id', 'start_lon', 'start_lat', 
            'start_build', 'best_lon', 'best_lat', 'dest_build', 'end_lon', 
            'end_lat', 'end_build', 'distance', 'extra_distance') 
    writer = csv.writer(m_csv_f) 
    writer.writerow(csv_header) 

    for x in range(sched_len): 
        logging.info("Schedule step #{}".format(x)) 
        r_count = 0 
        for rider in bikers_list: 
            r_count += 1 
            if (r_count % record_tick) == 0: 
                print('=', end='', flush=True) 

            logging.debug("Step #{} in seed {} For biker {}/{}:".format(x, 
                start_seed, r_count, bikers))

            # Get the starting location information 
            sched = rider.get_destination() 
            start_build, start_coords = rider.get_location() 

            # Get the ending location information.
            ideal_end_pad = camp.nearest_pad(start_coords, sched)  
            ideal_end_pad.register_request() 
            ideal_end_coords = ideal_end_pad.get_coordinates()  

            end_pad = camp.nearest_campus_wide_pad(ideal_end_coords, ignore_start=False) 
            camp.relocate_biker(rider, end_pad)
            end_coords = end_pad.get_coordinates() 

            distance, extra_distance = calc_dists(start_coords, sched, 
                    ideal_end_pad, end_pad) 
            
            if extra_distance > 0: 
                # Then this was not the ideal pad, so register a request there
                # This ensures that all used pads are properly requested 
                end_pad.register_request()
                
            # Advance the schedule 
            rider.advance_schedule() 
            
            new_row = (x, rider.get_name(), start_coords[0], start_coords[1], 
                    start_build, ideal_end_coords[0], ideal_end_coords[1], 
                    sched, end_coords[0], end_coords[1], 
                    end_pad.get_building_name(), distance, extra_distance) 
            writer.writerow(new_row) 
            time.sleep(sleep_delay)
            #print() 

        report_d = {
                'start time': _start_time, 
                'time': time.time(), 
                'seed': start_seed, 
                'bikers': bikers, 
                'sleep delay': sleep_delay, 
                'schedule length': sched_len, 
                'campus data': camp.dict_dump() 
                } 
        yaml.dump(report_d, _ylogfile, explicit_start=True, default_flow_style=False) 
        _ylogfile.write('\n') 

    m_csv_f.close() 
    _ylogfile.close() 
    ndat = obsprocrep.process_reports(datalogs_f, monte_f, data_dir)

    return ndat 


def monte_testing(config_file='config.yml'): 
    # config set up.
    config_f = open(config_file, 'r') 
    config = yaml.load(config_f).copy() 
    config_f.close() 
    
    s_delay = config['sleep delay']
    sched_events = config['scheduled events'] 
    data_dir_base = config['data directory'] 
    report_dir = config['report directory'] 
    
    bike_count = config['number of bikes'] 
    moves_per_cycle = config['moves per cycle']

    building_names = config['building equivalents'] 
    compiledata._load_building_names(building_names) 
    
    for s in config['rand seeds']: 
        comp_dat = load_compiled_data(config) 
        for opt_cycle in range(config['optimizing cycles']): 
            print("Cycle #{} on seed {} [".format(opt_cycle+1, s), end='', flush=True) 
            logging.info("Starting optimizing cycle {} on seed {}".format(opt_cycle, s)) 
            
            new_dir = os.path.join(data_dir_base, 'seed_{}_cycle_{}'.format(s, opt_cycle))
            report_txt_file = os.path.join(new_dir, 'moves_report.yml') 
            if not os.path.isdir(new_dir): 
                os.mkdir(new_dir) 
            cdat_filename = '{}/comp_dat.yml'.format(new_dir)
            with open(cdat_filename, 'w') as f: 
                f.write('# This file created for cycle #{} from seed {}\n'.format(
                    opt_cycle, s)) 
                yaml.dump(comp_dat, f, explicit_start=True, default_flow_style=False) 
            
            report_dat = monte_test_once(comp_dat, data_dir=new_dir, bikers=bike_count, start_seed=s,
                    sleep_delay=s_delay, sched_len=sched_events)
            
            with open(cdat_filename, 'r') as f: 
                comp_dat2 = yaml.load(f) 
                comp_dat = procopt.sl_exec(comp_dat2, report_dat, 
                        sched_events, moves_per_cycle, outfile=report_txt_file) 
                print(']\n') 

        bronzemarsh.inspect_summary_reports(data_dir=data_dir_base, 
                reports_dir=report_dir, seed_num=s, 
                max_cycles=(config['optimizing cycles']+1))


if __name__ == "__main__":
    #cd = compiledata.compile_data()
    #print(cd) 
    _logging_setup() 
    monte_testing() 

