import sys
import logging
import datetime
import time

from system import *
from statistics import *

class Simulation:

    logger = logging.getLogger("sim")

    def __init__(self, mission_time, iterations, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms, force_re, required_re, fs_trace):
        self.mission_time = mission_time
        self.iterations = iterations
        self.raid_type = raid_type
        self.raid_num = raid_num
        self.disk_capacity = disk_capacity
        self.disk_fail_parms = disk_fail_parms
        self.disk_repair_parms = disk_repair_parms
        self.disk_lse_parms = disk_lse_parms
        self.disk_scrubbing_parms = disk_scrubbing_parms

        self.logger.debug("Simulation: iterations = %d" % iterations)

        self.system = None

        # The required relative error
        self.force_re = force_re
        self.required_re = required_re

        self.samples = Samples()

        self.raid_failure_count = 0
        self.sector_error_count = 0

        self.cur_i = 0
        self.more_iterations = 0
        
        if fs_trace is not None:
            self.filesystem = []
            tracefile = open(fs_trace, "r")
            lines = list(tracefile)
            for i in range(len(lines)-1):
                self.filesystem.append(int(lines[i]))
            self.dr = float(lines[-1])
            tracefile.close()
        else:
            self.filesystem = None
            self.dr = 1

        self.start_time = datetime.datetime.now()

    def get_runtime(self):
        delta = datetime.datetime.now() - self.start_time
        d = delta.days
        s = delta.seconds%60
        m = (delta.seconds/60)%60
        h = delta.seconds/60/60
        return (d, h, m, s)

    def run_iterations(self, iterations):
        for self.cur_i in xrange(iterations):

            if self.cur_i % 15000 == 0:
                process = 1.0*self.cur_i/self.iterations
                num = int(process * 100)
                print >> sys.stderr,  "%6.2f%%: [" % (process*100), "\b= "*num, "\b\b>", " "*(100-num), "\b\b]", "%3dd%2dh%2dm%2ds \r"% self.get_runtime(),

            self.system.reset()
        
            result = self.system.run()

            if result[0] == System.RESULT_NOTHING_LOST:
                self.samples.addSample(0)
                self.logger.debug("%dth iteration: nothing lost" % self.cur_i)
            elif result[0] == System.RESULT_RAID_FAILURE:
                self.logger.debug("%dth iteration: %s, %d bytes lost" % (self.cur_i, "RAID Failure", result[1]))
                self.samples.addSample(result[1])
                self.raid_failure_count += 1
            elif result[0] == System.RESULT_SECTORS_LOST:
                self.logger.debug("%dth iterations: %s, %d bytes lost" % (self.cur_i, "Sectors Lost", sum(result[1:])))
                self.samples.addSample(result[1])
                self.sector_error_count += 1
            else:
                sys.exit(2)

        print >> sys.stderr,  "%6.2f%%: [" % (100.0), "\b= "*100, "\b\b>", "\b]", "%3dd%2dh%2dm%2ds"% self.get_runtime() 


    def simulate(self):

        self.system = System(self.mission_time, self.raid_type, self.raid_num, self.disk_capacity, self.disk_fail_parms,
            self.disk_repair_parms, self.disk_lse_parms, self.disk_scrubbing_parms, self.filesystem, self.dr)

        self.more_iterations = self.iterations
        while True:

            self.run_iterations(self.more_iterations)

            self.samples.calcResults("0.90")

            if self.force_re == False or self.samples.byte_re < self.required_re:
                break

            self.more_iterations = (self.samples.byte_re/self.required_re - 1) * self.iterations 
            if self.more_iterations < 10000:
                self.more_iterations = 10000

            print >> sys.stderr, "Since Relative Error %5f > %5f, %d more iterations to meet the requirement." % (self.samples.byte_re, self.required_re, self.more_iterations)

            self.iterations += self.more_iterations

        # finished, return results
        # the format of result:
        return (self.samples, self.raid_failure_count, self.sector_error_count, self.iterations, self.dr)
