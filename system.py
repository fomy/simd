import sys
import logging
import itertools
from collections import deque
import random
from component import *

class DeduplicationModel:

    def __init__(self, trace, filelevel, dedup, weighted):
        self.trace = trace
        self.filelevel = filelevel 
        self.dedup = dedup
        self.weighted = weighted
        self.df = 1.0
        

    def raid_failure(self, corrupted_area):
        return None

    def sector_error(self, lse_count):
        return None

class DeduplicationModel_Chunk_NoDedup(DeduplicationModel):
    def __init__(self, weighted):
        self.filelevel = False
        self.dedup = False

        self.filesystem = None
        self.weighted = weighted
        self.df = 1.0

    # percent of corrupted blocks
    def raid_failure(self, corrupted_area):
        return corrupted_area

    # the size of corrupted 8KB blocks 
    def sector_error(self, lse_count):
        # multiply with file system block
        if self.weighted:
            return lse_count * 8192
        else:
            return lse_count

# reference count / chunk size * reference count
# reference count / chunk size * reference count
# ...
# D/F
# 0% progress
# 1% progress
# ...
# 100% progress
class DeduplicationModel_Chunk_Dedup(DeduplicationModel):
    def __init__(self, trace, weighted):
        self.filelevel = False
        self.dedup = True

        self.weighted = weighted 
        self.trace = trace
        tracefile = open(self.trace, "r")
        if self.weighted:
            assert(list(itertools.islice(tracefile, 1))[0] == "CHUNK:DEDUP:WEIGHTED\n")
        else:
            assert(list(itertools.islice(tracefile, 1))[0] == "CHUNK:DEDUP:NOT WEIGHTED\n")

        self.filesystem = [float(i) for i in itertools.islice(tracefile, 1, None)]
        self.df = self.filesystem[-102]
        self.lse_range = len(self.filesystem) - 102
        tracefile.close()

    # percent of corrupted logical chunks
    def raid_failure(self, corrupted_area):
        result = 1.0 - self.filesystem[-1-int((corrupted_area+0.005)*100)]
        assert(result<=1 and result>=0)
        return result

    # the size of corrupted logical chunks
    def sector_error(self, lse_count):
        lost = 0;
        for i in xrange(lse_count):
             lost += self.filesystem[random.randrange(self.lse_range)]

        assert(lost>=0)
        return lost 

# 0% progress
# 1% progress
# ...
# 100% progress
class DeduplicationModel_File_NoDedup_NotWeighted(DeduplicationModel):
    def __init__(self, trace):
        self.filelevel = True
        self.dedup = False
        self.weighted = False

        self.trace = trace
        tracefile = open(self.trace, "r")

        assert(list(itertools.islice(tracefile, 1))[0] == "FILE:NO DEDUP:NOT WEIGHTED\n")

        # Totally 101 items for RAID failures
        self.filesystem = [float(i) for i in itertools.islice(tracefile, 1, None)]
        self.df = 1.0

    # percent of corrupted files
    def raid_failure(self, corrupted_area):
        result = 1.0 - self.filesystem[-1-int((corrupted_area+0.005)*100)]
        assert(result>=0 and result<=1)
        return result

    # number of corrupted files
    def sector_error(self, lse_count):
        return lse_count 

# file size for chunk 1 
# file size for chunk 2 
# ...
# 0% progress
# 1% progress
# ...
# 100% progress
class DeduplicationModel_File_NoDedup_Weighted(DeduplicationModel):
    def __init__(self, trace):
        self.filelevel = True
        self.dedup = False
        self.weighted = True

        self.trace = trace
        tracefile = open(self.trace, "r")

        assert(list(itertools.islice(tracefile, 1))[0] == "FILE:NO DEDUP:WEIGHTED\n")

        self.filesystem = [float(i) for i in itertools.islice(tracefile, 1, None)]
        self.df = 1.0
        self.lse_range = len(self.filesystem) - 101

    # percent of corrupted files in size
    def raid_failure(self, corrupted_area):
        result = 1.0 - self.filesystem[-1-int((corrupted_area+0.005)*100)]
        assert(result <= 1 and result >= 0)
        return result 

    # size of corrupted files
    def sector_error(self, lse_count):
        bytes_lost = 0;
        for i in xrange(lse_count):
             bytes_lost += self.filesystem[random.randrange(self.lse_range)]

        assert(bytes_lost>=0)
        return bytes_lost

# referred file size (MODE C)/count (MODE B) for chunk 1 
# referred file size/count for chunk 2 
# ...
# D/F
# 0% progress
# 1% progress
# ...
# 100% progress
class DeduplicationModel_File_Dedup(DeduplicationModel):
    def __init__(self, trace, weighted):
        self.filelevel = True
        self.dedup = True
        self.weighted = weighted
        self.trace = trace
        tracefile = open(self.trace, "r")

        if self.weighted:
            assert(list(itertools.islice(tracefile, 1))[0] == "FILE:DEDUP:WEIGHTED\n")
        else:
            assert(list(itertools.islice(tracefile, 1))[0] == "FILE:DEDUP:NOT WEIGHTED\n")

        # The last 101 items are for RAID failures
        self.filesystem = [float(i) for i in itertools.islice(tracefile, 1, None)]
        self.df = self.filesystem[-102]
        self.lse_range = len(self.filesystem) - 102

    # percent of corrupted files in number or size
    def raid_failure(self, corrupted_area):
        result = 1.0 - self.filesystem[-1-int((corrupted_area+0.005)*100)] 
        assert(result >= 0 and result <= 1)
        return result

    # number or size of corrupted files
    def sector_error(self, lse_count):
        corrupted_files = 0
        for i in xrange(lse_count):
             corrupted_files += self.filesystem[random.randrange(self.lse_range)]

        assert(corrupted_files>=0)
        return corrupted_files

class System:
    #RESULT_NOTHING_LOST = 0 #"Nothing Lost"
    #RESULT_RAID_FAILURE = 1 #"RAID Failure"
    #RESULT_SECTORS_LOST = 2 #"Sectors Lost"

    logger = logging.getLogger("sim")

    # A system consists of many RAIDs
    def __init__(self, mission_time, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms, trace, filelevel, dedup, weighted):
        self.mission_time = mission_time
        self.raid_num = raid_num
        self.avail_raids = raid_num

        self.logger.debug("System: mission_time = %d, raid_num = %d" % (self.mission_time, self.raid_num))

        self.event_queue = None

        self.raids = [Raid(raid_type, disk_capacity, disk_fail_parms,
                disk_repair_parms, disk_lse_parms, disk_scrubbing_parms) for i in range(raid_num)]

        if filelevel == False:
            if dedup == False:
                self.dedup_model = DeduplicationModel_Chunk_NoDedup(weighted)
            else:
                self.dedup_model = DeduplicationModel_Chunk_Dedup(trace, weighted)
        else:
            if dedup == False and weighted == False:
                self.dedup_model = DeduplicationModel_File_NoDedup_NotWeighted(trace);
            elif dedup == False and weighted == True:
                self.dedup_model = DeduplicationModel_File_NoDedup_Weighted(trace);
            elif dedup == True:
                self.dedup_model = DeduplicationModel_File_Dedup(trace, weighted)

    def reset(self):
        self.event_queue = []
        for r_idx in range(len(self.raids)):
            self.event_queue.extend(self.raids[r_idx].reset(r_idx, self.mission_time))

        self.event_queue = sorted(self.event_queue, reverse=True)

    def calc_bytes_lost(self):
        results = [0, 0]
        for raid in self.raids:
            if(raid.state == Raid.RAID_STATE_FAILED):
                # Not support multiple RAIDs in this model
                results[0] = self.dedup_model.raid_failure(raid.corrupted_area)

            results[1] += self.dedup_model.sector_error(raid.lse_count)

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

    def get_df(self):
        return self.dedup_model.df
