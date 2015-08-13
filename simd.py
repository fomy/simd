#!/usr/bin/python
import time
import sys
import logging
import signal
from numpy import random
import getopt

from simulation import *
from statistics import *
from system import *

def usage(arg):
    print arg, ": -h [--help] -l [--log] -m <mission_time> [--mission_time <mission_time>]"
    print "-i <num_iterations> [--iterations <num_iterations>] -r <raid_type> [--raid <raid_type>]"
    print "-n <num_raids> [--raid_num <num_raids>] -c <capacity_factor> [--capacity <capacity_factor>]"
    print "-F <disk_fail_dist> [--disk_fail_dist <disk_fail_dist>]"
    print "-R <disk_repair_dist> [--disk_repair_dist <disk_repair_dist>]"
    print "-L <disk_lse_dist> [--disk_lse_dist <disk_lse_dist>]"
    print "-S <disk_scrubbing_dist> [--disk_scrubbing_dist <disk_scrubbing_dist>]"
    print "-a <required_re> [--accuracy <required_re>]"
    # file system model; 
    print "-t <trace> [--trace <trace_file>]"
    print "-f [--filelevel]"
    print "-d [--dedup]"
    print "-w [--weighted]"
    print ""
    print "Detail:"
    print "mission_time = simulation end time in hours, default is 87600"
    print ""
    print "num_iterations = number of simulation runs, default is 10000"
    print ""
    print "raid_type = the raid configuration , 14_2_mds by default"
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
    print "required_re = the required relative error, disable by default"
    print ""
    print "Samples:"
    print arg, "-i 10000 -r \"mds_5_1\" -a 0.05"

    sys.exit(2)

def get_parms():
    logging.basicConfig(level = getattr(logging, "WARNING"))
    # 87600 hours, for 10 years
    mission_time = 87600
    # more iterations, more accurate estimate
    iterations = 10000L
    # the data/parity configuration
    # such as mds_7_1
    raid_type = "mds_14_2"
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

    # This indicates the simulation will not end until reach a required relative error
    force_re = False
    required_re = 0.05

    # file system trace
    fs_trace = None
    filelevel = False
    dedup = False
    weighted = False

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "hl:m:i:r:n:c:p:F:R:L:S:a:t:fdw", ["help", "log", "mission_time", 
                                                                             "iterations",
                                                                             "raid", "raid_num", 
                                                                             "capacity", 
                                                                             "parameters", 
                                                                             "disk_fail_dist",
                                                                             "disk_repair_dist",
                                                                             "disk_lse_dist",
                                                                             "disk_scrubbing_dist",
                                                                             "accuracy",
                                                                             "trace",
                                                                             "filelevel"
                                                                             "dedup",
                                                                             "weighted",
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
        elif o in ("-a", "--accuracy"):
            force_re = True
            required_re = float(a)
        elif o in ("-t", "--trace"):
            fs_trace = a
        elif o in ("-f", "--filelevel"):
            filelevel = True
        elif o in ("-d", "--dedup"):
            dedup = True
        elif o in ("-w", "--weighted"):
            weighted = True

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
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms, force_re, required_re, 
            fs_trace, filelevel, dedup, weighted)

def print_result(model, raid_failure_samples, lse_samples, systems_with_data_loss, 
        systems_with_raid_failures, systems_with_lse, iterations, raid_type, raid_num, disk_capacity, df):

    (type, d, p) = raid_type.split("_");
    data_fragments = int(d)

    total_capacity = data_fragments * disk_capacity * raid_num * 512/1024/1024/1024/1024 * df

    localtime = time.asctime(time.localtime(time.time()))
    print "**************************************"
    print "System (%s): %.2fTB data, D/F = %.4f, %d of %s RAID, %ld iterations" % (localtime, total_capacity, df, raid_num, raid_type, iterations)
    print "Filelevel =", model.filelevel, ", Dedup =", model.dedup, ", Weighted =", model.weighted
    print "Summary: %d of systems with data loss events (%d by raid failures, %d by lse)" % (systems_with_data_loss, systems_with_raid_failures, systems_with_lse)

    prob_result = (raid_failure_samples.prob_mean, 100*raid_failure_samples.prob_re, raid_failure_samples.prob_mean - raid_failure_samples.prob_ci, 
            raid_failure_samples.prob_mean + raid_failure_samples.prob_ci, raid_failure_samples.prob_dev)
    value_result = (raid_failure_samples.value_mean, 100*raid_failure_samples.value_re, raid_failure_samples.value_mean - raid_failure_samples.value_ci, 
            raid_failure_samples.value_mean + raid_failure_samples.value_ci, raid_failure_samples.value_dev)

    print "******** RAID Failure Part ***********"
    print "Probability of RAID Failures: %e +/- %f Percent , CI (%e,%e), StdDev: %e" % prob_result
    if model.filelevel == False:
        print "Fraction of Blocks/Chunks Lost in the Failed Disk: %e +/- %f Percent, CI (%e,%e), StdDev: %e" % value_result
    elif model.weighted == False:
        print "Fraction of Files Lost: %e +/- %f Percent, CI (%e,%e), StdDev: %e" % value_result
    else:
        print "Fraction of Files Lost Weighted by Bytes: %e +/- %f Percent, CI (%e,%e), StdDev: %e" % value_result

    prob_result = (lse_samples.prob_mean, 100*lse_samples.prob_re, lse_samples.prob_mean - lse_samples.prob_ci, 
            lse_samples.prob_mean + lse_samples.prob_ci, lse_samples.prob_dev)
    value_result = (lse_samples.value_mean, 100*lse_samples.value_re, lse_samples.value_mean - lse_samples.value_ci, 
            lse_samples.value_mean + lse_samples.value_ci, lse_samples.value_dev)

    print "************* LSE Part ***************"
    print "Probability of LSEs: %e +/- %f Percent , CI (%e,%e), StdDev: %e" % prob_result

    NOMDL = value_result[0]/total_capacity
    if model.filelevel == False:
        if model.weighted == False:
            print "# of Blocks/Chunks Lost: %e +/- %f Percent, CI (%f,%f), StdDev: %e" % value_result
            print "NOMDL (Normalized Magnitude of Data Loss): %e chunks per TB" % NOMDL
        else:
            print "Bytes of Blocks/Chunks Lost: %e +/- %f Percent, CI (%f,%f), StdDev: %e" % value_result
            print "NOMDL (Normalized Magnitude of Data Loss): %e bytes per TB" % NOMDL
    else:
        if model.weighted == False:
            print "# of Corrupted Files: %e +/- %f Percent, CI (%f,%f), StdDev: %e" % value_result
            print "NOMDL (Normalized Magnitude of Data Loss): %e files per TB" % NOMDL
        else:
            print "Size of Corrupted Files: %e +/- %f Percent, CI (%f,%f), StdDev: %e" % value_result
            print "NOMDL (Normalized Magnitude of Data Loss): %e bytes per TB" % NOMDL
    print "**************************************"

def do_it():

    parms = get_parms()
    simulation = Simulation(*parms)

    (model, raid_failure_samples, lse_samples, systems_with_data_loss, 
            systems_with_raid_failures, systems_with_lse, iterations, df) = simulation.simulate()
    
    raid_type = parms[2]
    raid_num = parms[3]
    disk_capacity = parms[4]

    print_result(model, raid_failure_samples, lse_samples, systems_with_data_loss, 
            systems_with_raid_failures, systems_with_lse, iterations, raid_type, raid_num, disk_capacity, df)

def sig_quit(sig, frame):

    # backtrace to get the simulation object
    object = frame.f_locals.get("self", None)
    while not isinstance(object, Simulation):
        frame = frame.f_back
        object = frame.f_locals.get("self", None)

    print >>sys.stderr, "\nThe simulation is interrupted!"

    object.raid_failure_samples.calcResults("0.95")
    object.lse_samples.calcResults("0.95")

    iterations = object.iterations - object.more_iterations + object.cur_i
    print_result(object.system.dedup_model, object.raid_failure_samples, object.lse_samples, object.systems_with_data_loss, 
            object.systems_with_raid_failures, object.systems_with_lse, 
            iterations, object.raid_type, object.raid_num, object.disk_capacity, object.system.get_df())

    sys.exit(1)

if __name__ == "__main__":
    simulation = None
    signal.signal(signal.SIGINT, sig_quit)
    do_it()


