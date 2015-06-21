import logging
from mpmath import *

from component import *

class System:
    EVENT_NOTHING_LOST = "Nothing Lost"
    EVENT_RAID_FAILURE = "RAID Failure"
    EVENT_SECTORS_LOST = "Sectors Lost"

    logger = logging.getLogger("sim")

    # A system consists of many RAIDs
    def __init__(self, mission_time, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms):
        self.mission_time = mission_time
        self.raid_num = raid_num
        self.system_time = mpf(0)

        self.logger.debug("System: mission_time = %d, raid_num = %d" % (self.mission_time, self.raid_num))

        self.raids = [Raid(raid_type, disk_capacity, disk_fail_parms,
                disk_repair_parms, disk_lse_parms, disk_scrubbing_parms) for i in range(raid_num)]

    def reset(self):
        self.system_time = mpf(0)
        for raid in self.raids:
            raid.reset()

    def go_to_next_event(self):
        raid_idx = 0
        (disk_idx, event_type, event_time) = self.raids[0].get_next_event()
        for r_idx in range(1, len(self.raids)):
            (d_idx, type, time) = self.raids[r_idx].get_next_event()
            if time < event_time:
                event_time = time
                event_type = type
                disk_idx = d_idx
                raid_idx = r_idx

        # After update, the system state is consistent
        self.system_time = event_time
        self.raids[raid_idx].update_to_event(disk_idx, event_type, event_time)

        return (raid_idx, disk_idx, event_type, event_time)

    # Three possible returns
    # [System.EVENT_NOTHING_LOST]
    # [System.EVENT_RAID_FAILURE, bytes]
    # [System.EVENT_SECTORS_LOST, lost1, lost2, ...]
    def run(self):

        sectors_lost = [System.EVENT_SECTORS_LOST]

        while True:

            (raid_idx, disk_idx, event_type, event_time) = self.go_to_next_event()

            self.logger.debug("raid_idx = %d, disk_idx = %d, event_type = %s, event_time = %d" % (raid_idx, disk_idx, event_type, event_time))

            if event_time > self.mission_time:
                # mission complete
                break

            if event_type == Disk.EVENT_REPAIR:
                continue

            # Check whether the failed disk causes a RAID failure 
            bytes_lost = self.raids[raid_idx].check_failure(self.system_time)
            if  bytes_lost > 0:
                # We return immediately because this event is rare and serious
                # It seems unnecessary to further check LSEs
                # TO-DO: When deduplication model is ready, we need to amplify bytes_lost
                # e.g., bytes_lost * deduplication factor
                return [System.EVENT_RAID_FAILURE, bytes_lost]

            # Check whether a LSE will cause a data loss
            # check_sectors_lost will return the bytes of sector lost
            # We need to further amplify it according to our file system
            lse = self.raids[raid_idx].check_sectors_lost(self.system_time)
            if lse > 0:
                sectors_lost.append(lse)

        # The mission concludes
        if len(sectors_lost) > 1:
            # TO-DO: Waiting for deduplication model
            return sectors_lost

        return [System.EVENT_NOTHING_LOST]
