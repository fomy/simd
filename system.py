import logging
from collections import deque
from mpmath import *

from component import *

class System:
    RESULT_NOTHING_LOST = "Nothing Lost"
    RESULT_RAID_FAILURE = "RAID Failure"
    RESULT_SECTORS_LOST = "Sectors Lost"

    logger = logging.getLogger("sim")

    # A system consists of many RAIDs
    def __init__(self, mission_time, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms):
        self.mission_time = mission_time
        self.raid_num = raid_num

        self.logger.debug("System: mission_time = %d, raid_num = %d" % (self.mission_time, self.raid_num))

        self.event_queue = None

        self.raids = [Raid(raid_type, disk_capacity, disk_fail_parms,
                disk_repair_parms, disk_lse_parms, disk_scrubbing_parms) for i in range(raid_num)]

    def reset(self):
        self.event_queue = []
        for r_idx in range(len(self.raids)):
            self.event_queue.extend(self.raids[r_idx].reset(r_idx, self.mission_time))

        self.event_queue = sorted(self.event_queue, reverse=True)

    def go_to_next_event(self):
        if len(self.event_queue) == 0:
            return None

        (event_time, disk_idx, raid_idx) = self.event_queue.pop()

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
    # [System.RESULT_NOTHING_LOST]
    # [System.RESULT_RAID_FAILURE, bytes]
    # [System.RESULT_SECTORS_LOST, lost1, lost2, ...]
    def run(self):

        sectors_lost = [System.RESULT_SECTORS_LOST]

        while True:

            e = self.go_to_next_event()
            if e == None:
                break

            (event_type, event_time, raid_idx) = e

            if event_type == Disk.DISK_EVENT_REPAIR:
                continue

            # Check whether the failed disk causes a RAID failure 
            bytes_lost = self.raids[raid_idx].check_failure(event_time)
            if  bytes_lost > 0:
                # We return immediately because this event is rare and serious
                # It seems unnecessary to further check LSEs
                # TO-DO: When deduplication model is ready, we need to amplify bytes_lost
                # e.g., bytes_lost * deduplication factor
                return [System.RESULT_RAID_FAILURE, bytes_lost]

            # Check whether a LSE will cause a data loss
            # check_sectors_lost will return the bytes of sector lost
            # We need to further amplify it according to our file system
            lse = self.raids[raid_idx].check_sectors_lost(event_time)
            if lse > 0:
                sectors_lost.append(lse)

        # The mission concludes
        if len(sectors_lost) > 1:
            # TO-DO: Waiting for deduplication model
            return sectors_lost

        return [System.RESULT_NOTHING_LOST]
