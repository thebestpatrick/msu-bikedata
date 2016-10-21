## Synopsis 

This program is intended to be used to optimize the distribution of bike racks on the campus of Montana State University. On a high level, it will use Monte Carlo methods (with predictable, replicable seed values) to determine which existing rack locations (called 'pads') have the most demand, and which are under utilized. It also uses the distances between the pads to minimize the distance traveled in the event of a full pad at the bike rider's optimal location. Once optimization of existing pads has been completed, it will make a judgement as to whether or not the purchase of more racks is economical. 

A simulation begins with a seed value, from which all future pseudo-random values should stem. This allows for easy replicablility and future testing. The program creates a number of theoretical Riders, representing one person riding a bike. Each Rider has a set 'schedule', a list of buildings that they wish to go to. This schedule is generated from the list of buildings and their occupancies (if building B has an occupancy of 500 out of a total possible occupancy of 1000, half of all schedule entries will be B). 

Each Rider in turn attempts to navigate to the desired building, choosing as ideal the linearly nearest pad and making a reservation request. If the ideal pad is full, the request is denied, and the Rider instead navigates to the pad nearest the ideal. This extra travel distance is stored for later optimization. 

Once each Rider has navigated through their entire schedule, an optimization algorithm is run to maximize the utility of each pad by moving racks around. This algorithm seeks to move racks from under utilized areas to high demand areas, while also balancing the travel distance between pads. After optimization is complete, another round of simulation is run on the new rack arrangement using *the same seed value* as the first simulation. This process repeats for a set number of times, then the final data is processed, analyzed, and a summary report created. 

## Assumptions

1. Each coordinate set indicates an area with bike racks within a reasonable distance from the building entrance. 
2. No pathing implemented yet. Therefore, assuming straight shots from point to point. 
3. All buildings will fill to occupancy limit at approximately the same rate. To indicate an underused building, lower the occupancy limit. 
4. From a starting position, a rider will attempt to go to the next (linearly nearest) pad to store their bike. 
5. If a pad's capacity is exceeded, the next rider will seek out the nearest available pad. This excess travel distance is tracked. 

## Files 

### Input Files 

Located in the *info/* folder within the project root directory

* bike_racks.csv has the location, capacity, type and associated building for each of the bike pads on campus. 
* building_occupancy.csv has the occupancy of each building on campus. 
* building_corners.csv has the layout of each building's exterior. 
* other_entrances.yml has possible pad locations for buildings specified in building_occupancy.csv but having no associated pads in bike_racks.csv 

### Generated Files

Located in the *data/* folder within the project root directory. These files are mostly used internally by the program, and are generally not in a format that can be readily understood by people. 

* comp_dat.yml contains a combined version of the starting conditions as outlined in the input files. This file will be generated if one does not exist, otherwise the existing one will be used. This allows for easy additions and subtractions from the starting conditions. For example, more pads can be added. A copy of this is also put into each of the seed_#_cycle#/ directories, representing the layout at that point. 
* (any).log files are simply log files for the program. They will probably contain information only useful to those who work directly on the code. 
* datalogs.yml is a temporary data file generated by the program to use with the optimation and reports later. 
* goldwater_mont.csv is a potentially useful file to examine and see the steps of logic used by the simulation, but probably not of any real use. 
* summary_report_dat.yml is an internally used file for creating the optimization algorithm 
* moves_report.yml is a listing of all rack movements for creating the optimal configuration output. 

### Human usable Files

These files are useful for reading or modifying to a semi-skilled user. Besides *config.yml*, most should be in the *reports/* directory. 

* config.yml located in the project root is where all changes to the program's behavior can be made. It is a YAML formatted text file with verbose comments to allow for quick tweaks to behavior. 
* summary.csv is an output from the software indicating that the seed # has been completed and that this data is the final summary output of the program. 
* ex_dist.png is a graph of the total extra distance traveled in meters. A useful visualization to show (hopefully) an overall downward trend. 

## Requirements 

This set of software has been designed for and run on a Linux computer, though if requested, it could be quickly adopted to other operating systems. Please note that at this time, no tests have been run on systems other than my own. 

1. Python3.5 (with system libraries: csv, math, time, random, os, logging, hashlib, etc.) 
2. PyYAML
3. matplotlib; specifically the pyplot functionality. 

## License: BSD 2-Clause License

Copyright (c) 2016, Patrick Ingham
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
