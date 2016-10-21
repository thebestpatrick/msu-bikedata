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
# This file is used to process the primary reports into data usable by the 
# optimization functions. 
# 
###############################################################################
import yaml 
import math 
import time 
import random 
import csv 
import os 

def _produce_report_averages(d): 
    n_d = {} 
    for k, v in d.items(): 
        rc = v['row_count'] 
        if rc < 1: 
            continue 
        avg_dist = v['ex_dist'] / rc 
        ideal_ratio = v['ideal_spot'] / rc 
        right_build_ratio = v['right_building'] / rc  
        n_d[k] = {
                'avg_dist': avg_dist, 
                'ideal': ideal_ratio, 
                'build': right_build_ratio 
                }

    return n_d 


def _merge_to_report_d(racks_d, i2): 
    rlocale_list = list(racks_d.keys())
    ilocale_list = list(i2.keys()) 
    tlocale_list = rlocale_list + ilocale_list 

    flocales = [] 
    for i in tlocale_list: 
        if i in flocales: 
            continue 
        flocales.append(i) 
    
    fd = {}

    for f in flocales: 
        rdd = racks_d.get(f)
        idd = i2.get(f)
        fd[f] = {
                'loc_info': idd, 
                'rack_info': rdd
                }
    return fd 


def process_reports(datalogs_loc, montecsv_loc, data_dir): 
    datalogs_f = open(datalogs_loc, 'r') 
    montecsv_f = open(montecsv_loc, 'r') 
    
    datalogs = yaml.load_all(datalogs_f) 
    locales_l = [] 
    racks_d = {} 
    for doc in datalogs:
        for b in doc['campus data']['locales']: 
            bn = b['building'] 
            if bn not in locales_l:
                locales_l.append(bn) 
            
            racks_d[bn] = [] 
            for rack in b['rack pads']:
                treq = rack['requests']['total'] 

                if treq >= 1:
                    demand = rack['requests']['unsat'] / treq 

                else: 
                    demand = 0.0
                
                usage = treq
                nd = {
                        'cap': rack['cap'], 
                        'racks': rack['racks'], 
                        'lat': rack['lat'], 
                        'lon': rack['lon'],
                        'demand': demand, 
                        'usage': usage, 
                        'requests': rack['requests'].copy(), 
                    }
                racks_d[bn].append(nd)

    dreader = csv.DictReader(montecsv_f) 
    ii = {
            'row_count': 0, 
            'ex_dist': 0.0, 
            'ideal_spot': 0, 
            'right_building': 0, 
            'appears': 0
        }
    i = {} 
    for b in locales_l: 
        i[b] = ii.copy() 
    
    i['overall'] = ii.copy() 
    for row in dreader:
        i['overall']['row_count'] += 1 
        i['overall']['ex_dist'] += float(row['extra_distance'])
        
        dbn = row['dest_build'] 
        i[dbn]['row_count'] += 1 
        i[dbn]['ex_dist'] += float(row['extra_distance']) 
        if dbn == row['end_build']: 
            i['overall']['right_building'] += 1 
            i[dbn]['right_building'] += 1 
            i[dbn]['appears'] += 1 

            ec = (row['end_lon'], row['end_lat']) 
            ic = (row['best_lon'], row['best_lat']) 
            if ic[0] == ec[0] and ic[1] == ec[1]: 
                i['overall']['ideal_spot'] += 1 
                i[dbn]['ideal_spot'] += 1 
        
        else: 
            i[dbn]['appears'] += 1 
            i[row['end_build']]['appears'] += 1 

    with open('{}/summary_report_dat.yml'.format(data_dir), 'w') as erdf: 
        yaml.dump(_merge_to_report_d(racks_d, i), erdf, explicit_start=True)

    datalogs_f.close() 
    montecsv_f.close() 
    new_racks = _merge_to_report_d(racks_d, i) 

    return new_racks 

    

