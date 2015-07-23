import logging
from collections import deque
import random
from mpmath import *

from component import *

class System:
    #RESULT_NOTHING_LOST = 0 # "Nothing Lost"
    #RESULT_RAID_FAILURE = 1 #"RAID Failure"
    #RESULT_SECTORS_LOST = 2 #"Sectors Lost"

    logger = logging.getLogger("sim")


    # A system consists of many RAIDs
    def __init__(self, mission_time, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms, filesystem, dr):
        self.mission_time = mission_time
        self.raid_num = raid_num
        self.avail_raids = raid_num

        self.logger.debug("System: mission_time = %d, raid_num = %d" % (self.mission_time, self.raid_num))

        self.event_queue = None

        self.raids = [Raid(raid_type, disk_capacity, disk_fail_parms,
                disk_repair_parms, disk_lse_parms, disk_scrubbing_parms) for i in range(raid_num)]

        self.filesystem = filesystem
        self.dr = dr
        if filesystem is not None:
            self.chunknum = len(filesystem)

    def reset(self):
        self.event_queue = []
        for r_idx in range(len(self.raids)):
            self.event_queue.extend(self.raids[r_idx].reset(r_idx, self.mission_time))

        self.event_queue = sorted(self.event_queue, reverse=True)


    def calc_bytes_lost(self):
        results = [0, 0]
        for raid in self.raids:
            if(raid.state == Raid.RAID_STATE_FAILED):
                if self.filesystem is not None:
                    raid.bytes_lost *= self.dr
                results[0] += raid.bytes_lost

            for i in xrange(raid.lse_count):
                if self.filesystem is not None:
                    results[1] += self.filesystem[random.randrange(self.chunknum)]
                else:
                    results[1] += Disk.SECTOR_SIZE

        return results

    def go_to_next_event(self):

        while True:
            if len(self.event_queue) == 0:
                return None
            (event_time, disk_idx, raid_idx) = self.event_queue.pop()
            if self.raids[raid_idx].state == Raid.RAID_STATE_OK:
                break

        # After update, the system state is consistent
        (event_type, next_event_time) = self.raids[raid_idx].update_to_event(event_time, disk_idx)
        if next_event_time <= self.mission_time:
            self.event_queue.append((next_event_time, disk_idx, raid_idx))
            size = len(self.event_queue)
            if size >= 2 and self.event_queue[size - 1] > self.event_queue[size - 2]:
                self.event_queue = sorted(self.event_queue, reverse=True)
                #print event_type, self.event_queue

        self.logger.debug("raid_idx = %d, disk_idx = %d, event_type = %s, event_time = %d" % (raid_idx, disk_idx, event_type, event_time))
        return (event_type, event_time, raid_idx)

    # Three possible returns
    # [System.RESULT_NOTHING_LOST, 0]
    # [System.RESULT_RAID_FAILURE, bytes]
    # [System.RESULT_SECTORS_LOST, bytes]
    def run(self):

        while True:

            e = self.go_to_next_event()
            if e == None:
                break

            (event_type, event_time, raid_idx) = e

            if event_type == Disk.DISK_EVENT_REPAIR:
                continue

            # Check whether the failed disk causes a RAID failure 
            if self.raids[raid_idx].check_failure(event_time) == True:
                # TO-DO: When deduplication model is ready, we need to amplify bytes_lost
                # e.g., bytes_lost * deduplication factor
                self.avail_raids -= 1
                if self.avail_raids == 0:
                    break

                continue

            # Check whether a LSE will cause a data loss
            # check_sectors_lost will return the bytes of sector lost
            # We need to further amplify it according to our file system
            self.raids[raid_idx].check_sectors_lost(event_time)

        # The mission concludes or all RAIDs fail
        return self.calc_bytes_lost()
