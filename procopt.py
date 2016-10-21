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
# This particular file handles the summary and optimization steps, by intaking 
# data generated each cycle and creating a recomended configuration for the 
# next cycle. 
# 
# By repeating this process several times, the best configuration of racks and 
# pads will begin to emerge 
# 
###############################################################################
import yaml 
import math 
import time 
import random 
import csv 
import os 
import logging

import montesim 

DEFLOGFILE = 'data/procopt.log' 

def _logging_setup(): 
    logging.basicConfig(format='PROCOPT:%(levelname)s:%(asctime)s:%(message)s',
            filename=DEFLOGFILE, level=logging.DEBUG)
    logging.info('--- Starting new procopt logging ---')


class Rack: 
    def __init__(self, name, cap): 
        logging.debug("Initiating Rack '{}' with {} capacity".format(
            name, cap)) 
        self._rack_name = name 
        self._capacity = cap 


    def get_name(self): 
        return self._rack_name 


    def get_capacity(self): 
        return self._capacity 
    

class Pad: 
    def __init__(self, locale, name, lon, lat, cap, racks, usage, 
            extra_distance, requests, sched_factor): 
        """
        usage should be the number of registered requests to the rack. This will
        allow for calculation of 'utilization', which will be a ratio of the 
        usage / total rack capacity.
        """
        self._lattitude = lat 
        self._longitude = lon 
        self._pad_name = name
        self._usage = usage 
        self._locale_name = locale 
        self._extra_distance = extra_distance 
        
        self._starting_capacity = cap 
        self._total_capacity = cap 
        self._total_racks = racks 

        self._racks_db = {} 
        
        self._requests = requests.copy() 
        self._sched_factor = sched_factor 

        # Set later by the CampusLayout class 
        self._nearest_distance = 0.0

        logging.debug("Initiating Pad '{}' at ({}, {}) with {} racks and {} capacity".format(
            name, lon, lat, racks, cap)) 

        # technically a max. 
        if racks <= 0: 
            min_rack_cap = 0

        else:
            min_rack_cap = math.ceil(cap / racks) 

        self._each_rack_cap = min_rack_cap 

        avail_cap = cap 
        for x in range(racks): 
            # name new rack
            rack_name = '{}/{}'.format(name, x) 
            if avail_cap >= min_rack_cap:
                rack_cap = min_rack_cap 
                avail_cap -= rack_cap 

            else: 
                rack_cap = avail_cap 
                avail_cap = 0 

            if rack_cap >= 1:
                self._racks_db[str(x)] = Rack(rack_name, rack_cap) 
    
    
    def get_capacity(self): 
        return self._total_capacity 


    def get_name(self): 
        return self._pad_name 

    
    def get_locale(self): 
        return self._locale_name 


    def get_extra_distance(self): 
        return self._extra_distance 


    def _get_utilization(self): 
        """
        utilization is the pad's usage over its total capacity. Returns None if 
        there is no capacity

        low capacity and high usage will yield high numbers, which are "bad" 
        because the pad is being over utilized. 

        high capacity and low usage will yield low numbers, which are also 
        "bad" because the pad is under utilized. 
        """
        total_cap = self._total_capacity 
        if total_cap <= 0: 
            return None 

        else: 
            return self._usage / total_cap 
    
    
    def get_utilization(self):  
        """
        Create a new unit to grade these on called the efficency rating. Basing 
        this off of the CampusLayout class' function to decide whether a new 
        rack needs to be purchased. 

        effeciency rating (er) should be a general rating of the usage, the 
        capacity and the distance traveled.  
        """
        old_cap = self._total_capacity
        
        use_factor = self._usage / self._sched_factor 

        util = (use_factor - old_cap) * self.get_nearest_distance() 
        logging.info("{}: utilization={}, usage={}, capacity={}, dist={}".format(
            self.get_name(), util, self._usage, self.get_capacity(), 
            self.get_nearest_distance()))
        
        return util 

    
    def _set_nearest_dist(self, nearest_dist): 
        self._nearest_distance = nearest_dist 

    
    def get_nearest_distance(self): 
        return self._nearest_distance 


    def remove_rack(self): 
        """
        Removes a single rack from this Pad and returns that Rack object. 
        """
        for rack_num in list(self._racks_db.keys()):
            rack = self._racks_db.get(rack_num)
            if rack is None: 
                continue 

            rack_cap = rack.get_capacity() 

            self._total_capacity -= rack_cap
            self._total_racks -= 1 

            self._racks_db[rack_num] = None 
            logging.info("Removing Rack '{}' with {} capacity from '{}'".format(
                rack.get_name(), rack_cap, self.get_name())) 
        
            return rack 

        return -1 

    def add_rack(self, rack, max_size=100000): 
        fin_rack_num = -1 
        logging.info("Adding Rack '{}' with {} capacity to '{}'".format(
            rack.get_name(), rack.get_capacity(), self.get_name())) 
        for _xvar in range(max_size):  
            rack_num = str(_xvar) 
            if self._racks_db.get(rack_num) is None: 
                fin_rack_num = _xvar 
                break 

        fin_rack_num = str(fin_rack_num) 
        self._racks_db[fin_rack_num] = rack 
        logging.debug("Old {}: Capacity: {}, Racks: {}".format(
            self.get_name(), self._total_capacity, self._total_racks))

        self._total_racks += 1 
        rack_cap = rack.get_capacity() 
        self._total_capacity += rack_cap 
        logging.debug("New {}: Capacity: {}, Racks: {}".format(
            self.get_name(), self._total_capacity, self._total_racks))


    def get_coordinates(self): 
        return (self._longitude, self._lattitude)


    def get_info_d(self): 
        rack_count = self._total_racks 
        total_cap = self._total_capacity 
        d = {
                'cap': total_cap, 
                'lat': self._lattitude, 
                'lon': self._longitude, 
                'racks': rack_count
            }
        return d 


class CampusLayout: 
    def __init__(self, info, report_dat, sched_factor=7): 
        """
        info should be a dict of information in the style of a comp_dat
        Exactly like a Campus class in montesim.py

        report_dat is a dict of information generated from another function, 
        which will include all locales, racks, capacities, requests, etc. 
        """
        logging.debug("Creating CampusLayout") 
        
        self._sf = sched_factor 
        self._info_d = info.copy() 
        self._report_dat = report_dat.copy() 

        self._building_names = list(info['build_names'])
        self._locales_names = self._building_names + ['campus', ]

        self._locales_db = {'campus': info['campus'].copy()} 
        self._all_coords = [] 
        for b in self._building_names: 
            self._locales_db[b] = info['locs'][b].copy() 
        
        self._pads = {}
        for l in self._locales_names: 
            rack_count = 0 
            avail_pads = self._report_dat[l]['rack_info']
            pad_data = self._report_dat[l]['loc_info'] 

            for p in avail_pads: 
                pad_name = 'l-{} p-{}'.format(l, rack_count) 

                lon = p['lon'] 
                lat = p['lat']
                req = p['requests'] 

                self._all_coords.append((p['lon'], p['lat'])) 
                
                cap = p['cap'] 
                racks = p['racks'] 
                usage = p['usage'] 
                ex_dist = pad_data['ex_dist'] 

                rack_count += 1
                self._pads[pad_name] = Pad(l, pad_name, lon, lat, cap, racks, 
                        usage, ex_dist, req, sched_factor)

        self._set_all_pad_dists()         
        logging.debug("Finished CampusLayout")

    
    def _set_all_pad_dists(self): 
        for pad_name in list(self._pads.keys()):
            pad = self._pads[pad_name] 
            cc = pad.get_coordinates() 

            min_dist = None 
            for nc in self._all_coords: 
                if cc[0] == nc[0] and cc[1] == nc[1]: 
                    continue
                
                cdist = montesim.get_coord_distance(cc, nc) 
                if min_dist is None: 
                    min_dist = cdist 

                elif min_dist > cdist: 
                    min_dist = cdist 

            pad._set_nearest_dist(min_dist) 


    def get_worst_utilization(self, get_lowest=True, ban_list=[]): 
        """
        Retrieves the pad name with the lowest utilization as long as get_lowest 
        is set to True. Otherwise, retrieves the pad with the highest. 
        """
        worst_pad = None 
        worst_util = None 
        for pad_name in list(self._pads.keys()): 
            if pad_name in ban_list: 
                continue

            pad = self._pads[pad_name] 
            util = pad.get_utilization() 
            if util is None: 
               util = pad._usage 
            
            if worst_pad is None: 
                worst_pad = pad.get_name() 
                worst_util = util 

            elif get_lowest is True: 
                if util < worst_util: 
                    worst_pad = pad.get_name() 
                    worst_util = util 

            else: 
                if util > worst_util: 
                    worst_pad = pad.get_name() 
                    worst_util = util 

        return worst_pad 


    def get_extra_distance(self, most_extra=True, ban_list=[]): 
        p = None 
        d = None 
        for pad_name in list(self._pads.keys()): 
            if pad_name in ban_list: 
                continue 
            pad = self._pads[pad_name] 
            nd = pad.get_extra_distance() 
            if p is None: 
                p = pad.get_name() 
                d = nd 

            elif d < nd and most_extra is True: 
                p = pad.get_name() 
                d = nd 

            elif d > nd and most_extra is False: 
                p = pad.get_name() 
                d = nd 

        return p 


    def _move_rack(self, take_from_pad, move_to_pad, order=0):
        logging.debug("Moving racks from '{}' to '{}'".format(
            take_from_pad, move_to_pad))
        tfp = self._pads.get(take_from_pad) 
        mtp = self._pads.get(move_to_pad) 
        if tfp is None or mtp is None: 
            return -1 

        r = tfp.remove_rack()
        if r == -1: 
            logging.warn("Pad '{}' returns -1 from remove_rack".format(take_from_pad)) 
            return None 
        
        sc = tfp.get_coordinates() 
        ec = mtp.get_coordinates() 
        sum_line = {
                'rack_cap': r.get_capacity(), 
                'move_order': order, 
                'start_locale': tfp.get_locale(), 
                'start_coords': {'lon': sc[0], 'lat': sc[1]}, 
                'end_locale': mtp.get_locale(), 
                'end_coords': {'lon': ec[0], 'lat': ec[1]}
                }
        cap = r.get_capacity() 

        mtp.add_rack(r) 
        #return cap 
        return sum_line 
    

    def _get_no_give_pads(self): 
        ngp = [] 
        for pad_name in list(self._pads.keys()): 
            pad = self._pads[pad_name] 
            if pad._total_capacity <= 0: 
                ngp.append(pad.get_name()) 

        return ngp 


    def flatten_utilization(self, cycles=3, max_tries=10): 
        """
        Takes a rack from the pad with the least utilization score and gives it
        to the pad with the most utilization score. Repeats this (cycles) times
        """
        logging.debug("Flattening utilization {} times".format(cycles)) 
        r = []
        t = 0 
        tries = 0 
        ngp = self._get_no_give_pads() 
        while t < cycles: 
            # Max utilization should be given to 
            max_util_pad = self.get_worst_utilization(get_lowest=False) 
            
            # Min utilization should be taken from 
            min_util_pad = self.get_worst_utilization(get_lowest=True, ban_list=ngp) 

            i = self._move_rack(min_util_pad, max_util_pad, t)
            if i is None:
                tries += 1 
                ngp.append(min_util_pad) 
                if tries > max_tries: 
                    break 
                else:
                    continue 

            else:
                t += 1 
                r.append(i) 

        return r 
    
    
    def flatten_distances(self, cycles=3, max_tries=10): 
        logging.debug("Flattening extra distances {} times".format(cycles)) 
        r = []
        t = 0 
        tries = 0 
        ngp = self._get_no_give_pads()
        nrp = [] 
        while t < cycles: 
            # Most extra distance should be given to. 
            max_dist_pad = self.get_extra_distance(most_extra=True, ban_list=nrp) 

            # Least extra distance should be taken from. 
            min_dist_pad = self.get_extra_distance(most_extra=False, ban_list=ngp) 
            i = self._move_rack(min_dist_pad, max_dist_pad, t) 
            if i is None:
                tries += 1 
                ngp.append(min_dist_pad) 
                if tries > max_tries: 
                    break 
                else:
                    continue 

            else:
                t += 1 
                r.append(i) 
                nrp.append(max_dist_pad) 

        return r 

    
    def new_racks_needed(self, rack_price=825.00, rack_cap=10, speed_val=4828.0, 
            time_val=15.00): 
        """
        Determines if the purchase of new racks would likely be economical, 
        and if so, how many racks should be purchased, and where purchased 
        racks should be placed. 
        """
        cost_per_meter = 1.0 / (speed_val / time_val) 

        for pad_name in list(self._pads.keys()): 
            pad = self._pads[pad_name] 
            base_util = pad.get_utilization() 

            time_frame = 5.0 * 36.0  # Five days per week, 36 weeks per year 

            base_cost = (base_util * cost_per_meter) * time_frame 
            logging.info("Pad {} is costing ${} from non ideal utilization".format(
                pad_name, base_cost))



    def optimize_distribution(self, cycles=3, max_tries=10, outfile=None): 
        logging.info("Optimizing rack distribution in {} cycles".format(cycles))
        fdr = self.flatten_distances(cycles=cycles, max_tries=max_tries) 
        fur = self.flatten_utilization(cycles=cycles, max_tries=max_tries)
        
        if outfile is not None:
            out_dir = os.path.split(outfile) 
            if not os.path.isdir(out_dir[0]): 
                os.mkdir(out_dir[0]) 

            with open(outfile, 'w') as f: 
                n = {'flat_dist': fdr, 'flat_util': fur} 
                yaml.dump(n, f, explicit_start=True) 


    def get_current_info_d(self): 
        pad_names = list(self._pads.keys()) 
        
        build_names = list(self._building_names) 
        locs_d = {} 

        camp_o = self._info_d['campus']['occupancy']
        campus_d = {'rack_pads': [], 
                'occupancy': camp_o}

        total_bike_cap = 0 
        total_occ = camp_o

        for b in build_names:
            o = self._info_d['locs'][b]['occupancy'] 
            total_occ += o 

            bn = {'occupancy': o, 'rack_pads': []} 
            locs_d[b] = bn 
        
        for pn in pad_names: 
            pad = self._pads[pn] 
            pad_locale = pad.get_locale()
            if pad_locale != 'campus': 
                locs_d[pad_locale]['rack_pads'].append(pad.get_info_d()) 

            else: 
                campus_d['rack_pads'].append(pad.get_info_d()) 
            total_bike_cap += pad.get_capacity() 

        d = {
                'campus': campus_d, 
                'total_bike_cap': total_bike_cap, 
                'total_occ': total_occ, 
                'build_names': build_names, 
                'locs': locs_d
                }
        return d


    def get_current_bike_racks_csv(self, outfile): 
        """
        Creates a .csv file for the current arrangement exactly like 
        bike_racks.csv in the info directory 
        """
        pass 


def sl_exec(info, rep_dat, sched_factor=7, cycle_moves=3, outfile=None): 
    #print(info) 
    #print(rep_dat) 
    c = CampusLayout(info, rep_dat, sched_factor) 
    #c.flatten_utilization() 
    c.optimize_distribution(cycles=cycle_moves, outfile=outfile) 
    c.new_racks_needed()  # FIXME: this will need config input.  
    return c.get_current_info_d() 


if __name__ == "__main__":
    _logging_setup() 
    # data/example_report_dat.yml for the CampusLayout report_dat variable 
    # data/example_info.yml for the CampusLayout info variable
    rep_dat_f = 'data/example_report_dat.yml' 
    info_dat_f = 'data/example_info.yml' 
    rdf = open(rep_dat_f, 'r') 
    idf = open(info_dat_f, 'r') 
    
    logging.info("Getting report data from %s", rep_dat_f) 
    logging.info("Getting info data from %s", info_dat_f) 

    rep_dat = yaml.load(rdf) 
    info = yaml.load(idf) 

    c = CampusLayout(info, rep_dat) 
    #print(yaml.dump(c.get_current_info_d())) 
    #time.sleep(20) 
    print(c.flatten_utilization()) 
    print(yaml.dump(c.get_current_info_d())) 
    rdf.close() 
    idf.close() 
