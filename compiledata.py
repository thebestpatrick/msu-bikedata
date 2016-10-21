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
# This file is used to convert the input files (bike_racks.csv, 
# buildings_occupancy.csv, other_entrances.csv, etc) into a dictionary of 
# values for use in the rest of the program 
# 
###############################################################################
import csv 
import random 
import yaml 

BUILDING_NAMES = {} 
def _load_building_names(new_values): 
    global BUILDING_NAMES 
    BUILDING_NAMES = new_values.copy() 


def qad_building_translator(n): 
    input_name = str(n).lower() 
    #print('*', '"{}"'.format(input_name))
    build_names = list(BUILDING_NAMES.keys()) 
    for build_name in build_names: 
        if input_name == build_name: 
            return build_name
        
        alternate_names = BUILDING_NAMES.get(build_name) 
        if input_name in alternate_names: 
            return build_name 
    return input_name


other_ent = {} 
def qad_entrances(n): 
    r = other_ent.get(n) 
    if r is None: 
        return [] 

    else: 
        return r 

    
def compile_data(bike_rack_file='info/bike_racks.csv', 
        buildings_file='info/buildings_occupancy.csv', min_occupancy=20, 
        ent_file='info/other_entrances.yml'): 
    all_buildings = [] 
    mas_d = {} 
    
    total_bike_cap = 0 
    with open(ent_file, 'r') as entf: 
        global other_ent 
        other_ent = yaml.load(entf) 

    # The more important file with coordinates
    with open(bike_rack_file, 'r') as br_file: 
        r = csv.DictReader(br_file) 
        for row in r: 
            bname = qad_building_translator(str(row.get('Nearest building')).lower())
            bcap = int(row.get('Capacity'))
            total_bike_cap += bcap 

            # x is degrees lattitude, y is degrees longitude
            #if bname not in br_buildings: 
            if bname not in all_buildings: 
                all_buildings.append(bname) 
                #bcap = int(row.get('Capacity'))
                #total_bike_cap += bcap

                qkp = qad_entrances(bname) 
                kp = qkp + [
                        {
                            'lon': float(row.get('x')), 
                            'lat': float(row.get('y')), 
                            'racks': int(row.get('Number of racks')), 
                            'cap': bcap
                        }, 
                        ]

                mas_d[bname] = {'rack_pads': kp, 'occupancy': 0}

            else:
                mas_d[bname]['rack_pads'].append(
                        {
                            'lon': float(row.get('x')), 
                            'lat': float(row.get('y')), 
                            'racks': int(row.get('Number of racks')), 
                            'cap': int(row.get('Capacity'))
                        }
                    )

    
    total_occ = 0
    with open(buildings_file, 'r') as b_file: 
        r = csv.DictReader(b_file) 
        for row in r: 
            bname = qad_building_translator(str(row.get('Building')).lower())
            cap = int(row.get('Capacity')) 
            total_occ += cap 

            #if bname not in b_buildings: 
            if bname not in all_buildings: 
                all_buildings.append(bname) 

                qkp = qad_entrances(bname) 
                cap = int(row.get('Capacity'))
                #total_bike_cap += cap 
                #total_occ += cap
                mas_d[bname] = {'rack_pads': qkp, 'occupancy': cap} 

            else:
                mas_d[bname]['occupancy'] += cap 
    
    # because the 'campus' location is special 
    all_buildings.remove('campus') 

    fin_d = {
            'locs': {},  # The location data generated above. 
            'total_bike_cap': total_bike_cap, 
            'total_occ': total_occ, 
            'build_names': all_buildings, 
            'campus': mas_d.pop('campus') 
            } 
    for k, v in mas_d.items(): 
        if v['occupancy'] <= min_occupancy: 
            o_occ = v['occupancy'] 
            v['occupancy'] = min_occupancy
            fin_d['total_occ'] += min_occupancy - o_occ 

        fin_d['locs'][k] = v 

    return fin_d


if __name__ == "__main__":
    print(compile_data())
