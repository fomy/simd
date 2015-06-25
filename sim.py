import time
import sys
import logging
from mpmath import *
from numpy import random
import getopt

from simulation import *
from statistics import *

def usage(arg):
    print arg, ": -h [--help] -l [--log] -m <mission_time> [--mission_time <mission_time>]"
    print "-i <num_iterations> [--iterations <num_iterations>] -r <raid_type> [--raid <raid_type>]"
    print "-n <num_raids> [--raid_num <num_raids>] -c <capacity_factor> [--capacity <capacity_factor>]"
    print "-F <disk_fail_dist> [--disk_fail_dist <disk_fail_dist>]"
    print "-R <disk_repair_dist> [--disk_repair_dist <disk_repair_dist>]"
    print "-L <disk_lse_dist> [--disk_lse_dist <disk_lse_dist>]"
    print "-S <disk_scrubbing_dist> [--disk_scrubbing_dist <disk_scrubbing_dist>]"
    print ""
    print "Detail:"
    print "mission_time = simulation end time in hours, default is 87600"
    print ""
    print "num_iterations = number of simulation runs, default is 10000"
    print ""
    print "raid_type = the raid configuration , 7_1_mds by default"
    print ""
    print "num_raids = number of raids in the system, defaut is 1"
    print ""
    print "capacity_factor = the disk capacity factor, defaut is 1 (2*1024*1024*1024 sectors (1TB)),"
    print ""
    print "disk_fail_dist = \"(shape = 1.2, scale = 461386 by default)\" OR"
    print "                      \"(scale)\" OR"
    print "                      \"(shape, scale)\" OR"
    print "                      \"(shape, scale, location)\""
    print "disk_repair_dist = \"(shape = 2.0, scale = 12, location = 6 by default)\" OR"
    print "                      \"(scale)\" OR"
    print "                      \"(shape, scale)\" OR"
    print "                      \"(shape, scale, location)\""
    print "disk_scrubbing_dist = \"(shape = 3.0, scale = 168, location = 6 by default)\" OR"
    print "                      \"(scale)\" OR"
    print "                      \"(shape, scale)\" OR"
    print "                      \"(shape, scale, location)\""
    print "                      shape = shape parameter of a Weibull (1 for Exponential)"
    print "                      scale = scale parameter of a Weibull"
    print "                      location = location parameter of a Weibull"
    print "disk_lse_dist = \"(rate = 1.08/10000 by default)\""
    print ""
    print "Samples:"
    print arg, "-m 10000 -n 1 -i 25 -F \"(1.12, 461386)\" -R \"(2.0, 20.0)\""

    sys.exit(2)

def get_parms():
    logging.basicConfig(level = getattr(logging, "WARNING"))
    # 87600 hours, for 10 years
    mission_time = 87600
    # more iterations, more accurate estimate
    iterations = 10000L
    # the data/parity configuration
    # such as mds_7_1
    raid_type = "mds_7_1"
    # the number of raid
    raid_num = 1
    # the number of sectors in each disk
    # 512 bytes for each sector
    # So the default is 1TB
    disk_capacity = 2*1024*1024*1024L
    capacity_factor = 1.0

    parms = "Elerath2014A"
    disk_fail_parms = None 
    disk_repair_parms = None
    disk_lse_parms = None
    disk_scrubbing_parms = None

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "hl:m:i:r:n:c:p:F:R:L:S:", ["help", "log", "mission_time", 
                                                                             "iterations",
                                                                             "raid", "raid_num", 
                                                                             "capacity", 
                                                                             "parameters", 
                                                                             "disk_fail_dist",
                                                                             "disk_repair_dist",
                                                                             "disk_lse_dist",
                                                                             "disk_scrubbing_dist",
                                                                             ])
    except:
        usage(sys.argv[0])
        print "getopts excepted"
        sys.exit(1)

    for o, a in opts:
        if o in ("-h", "--help"):
            print usage(sys.argv[0])
            sys.exit(0)
        if o in ("-l", "--log"):
            logger = logging.getLogger("sim")
            logger.setLevel(getattr(logging, a.upper()))
        if o in ("-F", "--disk_fail_dist"):
            if len(eval(a)) == 1:
                disk_fail_parms = (1, eval(a), 0)

            elif len(eval(a)) == 2:
                (shape, scale) = eval(a)
                disk_fail_parms = (shape, scale, 0)

            elif len(eval(a)) == 3:
                (shape, scale, location) = eval(a)
                disk_fail_parms = (shape, scale, location)

            else:
                bad_opt = o + " : " + a
                break
        
        elif o in ("-R", "--disk_repair_dist"):
            if len(eval(a)) == 1:
                disk_repair_parms = (1, eval(a), 0)

            elif len(eval(a)) == 2:
                (shape, scale) = eval(a)
                disk_repair_parms = (shape, scale, 0)

            elif len(eval(a)) == 3:
                (shape, scale, location) = eval(a)
                disk_repair_parms = (shape, scale, location)

            else:
                bad_opt = o + " : " + a
                break

        elif o in ("-L", "--disk_lse_dist"):
            if len(eval(a)) == 1: # the lse rate 
                disk_lse_parms = eval(a)
            else:
                bad_opt = o + " : num args must be 1"
                break

        elif o in ("-m", "--mission_time"):
            mission_time = float(a) 

        elif o in ("-i", "--iterations"):
            iterations = long(a) 

        elif o in ("-r", "--raid"):
            raid_type = a 

        elif o in ("-n", "--raid_num"):
            raid_num = int(a) 
                 
        elif o in ("-c", "--capacity"):
            capacity_factor = float(a)
        elif o in ("-p", "--parameters"):
            parms = a

    # TO-DO: We should verify these numbers
    # We assume larger disks will have longer repair and scrubbing time
    disk_capacity *= capacity_factor

    # The following parameters may change with disk capacity
    # For failure, restore, and scrubbing, the parameters are (shape, scale, location)

    if disk_fail_parms != None and disk_repair_parms != None and disk_lse_parms != None and disk_scrubbing_dist != None:
            parms = None

    if parms == "Elerath2009":
        # data from [Elerath2009]
        disk_fail_parms = (1.2, 461386.0, 0)
        disk_repair_parms = (2.0, 12.0 * capacity_factor, 6.0 * capacity_factor)
        disk_lse_parms = (1.08/10000) 
        disk_scrubbing_parms = (3, 168 * capacity_factor, 6 * capacity_factor)
    elif parms == "Elerath2014A":
        #data from [Elerath2014], SATA Disk A
        disk_fail_parms = (1.13, 302016.0, 0)
        disk_repair_parms = (1.65, 22.7 * capacity_factor, 0)
        disk_lse_parms = (1.0/12325) 
        disk_scrubbing_parms = (1, 186 * capacity_factor, 0)
    elif parms == "Elerath2014B":
        #data from [Elerath2014], SATA Disk B
        disk_fail_parms = (0.576, 4833522.0, 0)
        disk_repair_parms = (1.15, 20.25 * capacity_factor, 0)
        disk_lse_parms = (1.0/42857) 
        disk_scrubbing_parms = (0.97, 160 * capacity_factor, 0)
    else:
        if parms != None:
            usage(sys.argv[0])
            print "Invaid parms"
            exit(2)

    return (mission_time, iterations, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms)             

def do_it():

    logger = logging.getLogger("sim")

    (mission_time, iterations, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms) = get_parms()

    logger.debug("Parameters: mission time = %d, iterations = %ld, raid_type = %s, raid_num = %d, \
disk_capacity = %d, disk_fail_parms = %s, disk_repair_parms = %s, \
disk_lse_parms = %s, disk_scrubbing_parms = %s" % 
            (mission_time, iterations, raid_type, raid_num, disk_capacity, 
            str(disk_fail_parms), str(disk_repair_parms), str(disk_lse_parms), str(disk_scrubbing_parms)))

    simulation = Simulation(mission_time, iterations, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms)

    (samples, raid_failure_count, sector_error_count) = simulation.simulate()

    
    (type, d, p) = raid_type.split("_");
    data_fragments = int(d)

    total_capacity = data_fragments * disk_capacity * raid_num * 512/1024/1024/1024/1024

    prob_result = (samples.prob_mean, 100*samples.prob_re, samples.prob_mean - samples.prob_ci, 
            samples.prob_mean + samples.prob_ci, samples.prob_dev)
    byte_result = (samples.byte_mean, 100*samples.byte_re, samples.byte_mean - samples.byte_ci, 
            samples.byte_mean + samples.byte_ci, samples.byte_dev)
    data_loss_event = raid_failure_count + sector_error_count

    localtime = time.asctime(time.localtime(time.time()))
    print "*******************"
    print "System-%s: %dTB data, %d of %s RAID, %ld iterations" % (localtime, total_capacity, raid_num, raid_type, iterations)
    print "*******************"
    print "Summary: %d data loss events (%d by raid failures, %d by lse)" % (data_loss_event, raid_failure_count, sector_error_count)
    print "*******************"
    print "Estimated reliability: %e +/- %f Percent , CI (%e,%e), StdDev: %e" % prob_result
    print "*******************"
    print "Average bytes lost: %.5f +/- %f Percent, CI (%f,%f), StdDev: %f" % byte_result
    print "*******************"

if __name__ == "__main__":
    do_it()


