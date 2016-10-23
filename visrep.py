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
# This file converts summary data into reports and visualizations for human 
# consumption and decision making. 
# 
###############################################################################
import yaml 
import math 
import time 
import random 
import csv 
import os 
import logging
import hashlib

import matplotlib.pyplot as plt

DEFLOGFILE = 'data/visrep.log' 

def _logging_setup(): 
    logging.basicConfig(format='VISREP:%(levelname)s:%(asctime)s:%(message)s',
            filename=DEFLOGFILE, level=logging.DEBUG)
    logging.info('--- Starting new visrep logging ---')


def _color_and_line(b): 
    line_types = ['--', '-', ':', '-.', '_', '.', 'v', ',', '-_']
    colors = list('rgbcmky') 
    text = bytearray(str(b), 'utf-8') 
    h = int(hashlib.md5(text).hexdigest()[:2], 16)
    l = h % len(line_types) 
    c = len(b) % len(colors) 

    return '{}{}'.format(colors[c], line_types[l]) 


def get_summary_data(data_file, cycle=0, seed=0): 
    dat_dir, dat_file = os.path.split(data_file) 
    dc = {'ex_dist': 0.0, 'demand': 0.0, 'racks': 0, 'usage': 0, 
            'cap': 0, 'seed': seed, 'cycle': cycle} 

    rack_keys = ['demand', 'racks', 'usage', 'cap']
    
    r = [] 
    with open(data_file, 'r') as datfile: 
        ydata = yaml.load(datfile) 
        keys = list(ydata.keys()) 

        loc_count = len(keys) 
        for key in keys: 
            loc_info = ydata[key]['loc_info'] 
            rack_info = ydata[key]['rack_info'] 

            d = dc.copy() 
            d['building'] = key
            d['ex_dist'] = loc_info['ex_dist'] 
            if rack_info is None: 
                continue 

            for rack in rack_info: 
                for k in rack_keys: 
                    d[k] += rack[k] 

            r.append(d) 

    return r 


def visualize_single_cycle(cycle_data, data_dir, min_per=0.01): 
    labels = [] 
    sizes = [] 
    total_val = 0.0 
    
    seed_num = 0 
    cycle_num = 0 
    for i in cycle_data: 
        seed_num = i['seed'] 
        cycle_num = i['cycle'] 
        total_val += i['ex_dist'] 

    for i in cycle_data: 
        if (i['ex_dist'] / total_val) <= min_per: 
            continue 
        labels.append(i['building']) 
        sizes.append(i['ex_dist']) 

    plt.pie(sizes, labels=labels, autopct='%1.1f%%') 
    plt.axis('equal')
    plt.suptitle('Wasted Distance. Cycle {} of seed {}.'.format(
        cycle_num, seed_num))
    plt.annotate('Approx. {} meters'.format(round(total_val, 3)), xy=(-0.9,-0.9))
    plt.show()


def visualize_all(data, out_dir, field='ex_dist'): 
    nd = {} 
    labels = [] 
    seed_num = 0
    for d in data: 
        b = d['building'] 
        seed_num = d['seed'] 
        if b not in labels: 
            labels.append(b) 
            nd[b] = [] 

        nd[b].append(d[field]) 

    for l in labels: 
        nl = _color_and_line(l) 
        plt.plot(nd[l], nl, label=l) 
    
    plt.xlabel('Cycle') 
    plt.ylabel(field) 
    plt.suptitle('Seed {}: {} vs Cycles'.format(seed_num, field))
    #plt.legend(loc=1)
    plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.9), ncol=3)
    
    filename = os.path.join(out_dir, '{}_graph.png'.format(field)) 
    plt.savefig(filename, pad_inches=0.1, bbox_inches='tight', orientation='landscape', 
            figsize=(10.8, 7.2), dpi=100) 
    plt.close('all') 
    #plt.show() 


def inspect_summary_reports(data_dir='data',
        reports_dir='reports', 
        dir_form='seed_{}_cycle_{}'.format, 
        seed_num=481,
        max_cycles=50,
        summary_file='summary_report_dat.yml'): 
    
    full_info = [] 
    for x in range(max_cycles): 
        idir = dir_form(seed_num, x) 
        fp = os.path.join(data_dir, idir, summary_file) 
        if os.path.isfile(fp): 
            part_info = get_summary_data(fp, cycle=x, seed=seed_num)
            #visualize_single_cycle(part_info, fp) 
            # do stuff 
            full_info += part_info
    
    report_loc = os.path.join(reports_dir, 'seed_{}'.format(seed_num)) 
    if not os.path.isdir(report_loc): 
        os.mkdir(report_loc) 

    visualize_all(full_info, report_loc, field='ex_dist') 
    
    csv_loc = os.path.join(report_loc, 'summary.csv') 
    field_names = list(full_info[0].keys())

    with open(csv_loc, 'w') as cf: 
        writer = csv.DictWriter(cf, field_names)
        writer.writeheader() 
        writer.writerows(full_info) 

    
if __name__ == "__main__":
    #_logging_setup() 
    inspect_summary_reports(seed_num=481) 

