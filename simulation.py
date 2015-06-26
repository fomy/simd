import sys
import logging
import datetime
import time

from system import *
from statistics import *

class Simulation:

    logger = logging.getLogger("sim")

    def __init__(self, mission_time, iterations, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms):
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

    def simulate(self):
        sample_list = []
        raid_failure_count = 0
        sector_error_count = 0

        self.system = System(self.mission_time, self.raid_type, self.raid_num, self.disk_capacity, self.disk_fail_parms,
            self.disk_repair_parms, self.disk_lse_parms, self.disk_scrubbing_parms)

        start_time = datetime.datetime.now()
        for i in xrange(self.iterations):

            if i % 15000 == 0:
                process = 1.0*i/self.iterations
                num = int(process * 100)
                delta = datetime.datetime.now() - start_time
                d = delta.days
                s = delta.seconds%60
                m = (delta.seconds/60)%60
                h = delta.seconds/60/60
                print >> sys.stderr,  "%6.2f%%: [" % (process*100), "\b= "*num, "\b\b>", " "*(100-num), "\b\b]", "%3dd%2dh%2dm%2ds \r"% (d,h,m,s),

            self.system.reset()
        
            result = self.system.run()

            if result[0] == System.RESULT_NOTHING_LOST:
                #sample_list.append(0)
                self.logger.debug("%dth iteration: nothing lost")
            elif result[0] == System.RESULT_RAID_FAILURE:
                self.logger.debug("%dth iteration: %s, %d bytes lost" % (i, "RAID Failure", result[1]))
                sample_list.append(result[1])
                raid_failure_count += 1
            elif result[0] == System.RESULT_SECTORS_LOST:
                self.logger.debug("%dth iterations: %s, %d bytes lost" % (i, "Sectors Lost", sum(result[1:])))
                sample_list.append(sum(result[1:]))
                sector_error_count += len(result) - 1
            else:
                sys.exit(2)

        print >> sys.stderr,  "%6.2f%%: [" % (100.0), "\b= "*100, "\b\b>", "\b]", "%3dd%2dh%2dm%2ds"% (d,h,m,s)

        prob_result = None
        byte_result = None

        samples = Samples()
        stime = time.clock()
        samples.calcResults("0.90", sample_list, self.iterations)
        t = time.clock() - stime
        print >> sys.stderr, "Result analysis takes %f Sec" % t

        # finished, return results
        # the format of result:
        return (samples, raid_failure_count, sector_error_count)
