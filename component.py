import logging
from stochastic import *
from bm_ops import *

class Disk:

    DISK_STATE_OK = "ok"
    DISK_STATE_FAILED = "failed"

    DISK_EVENT_FAIL = "event disk fail"
    DISK_EVENT_REPAIR = "event disk repair"

    SECTOR_SIZE = 512 # bytes

    logger = logging.getLogger("sim")

    def __init__(self, disk_fail_parms=(1, 461386,0), disk_repair_parms=(1,12,0),
            disk_lse_parms=(0.000108), disk_scrubbing_parms=(3,168.0,6)):

        self.logger.debug("Disk: disk_fail_parms = %s, disk_repair_parms = %s, \
disk_lse_parms = %s, disk_scrubbing_parms = %s" % 
            (str(disk_fail_parms), str(disk_repair_parms), str(disk_lse_parms), str(disk_scrubbing_parms)))

        (shape, scale, location) = disk_fail_parms
        self.disk_fail_dist = Weibull(shape, scale, location);
        (shape, scale, location) = disk_repair_parms
        self.disk_repair_dist = Weibull(shape, scale, location);
        (shape, scale, location) = disk_scrubbing_parms
        self.disk_scrubbing_dist = Weibull(shape, scale, location);

        (rate) = disk_lse_parms
        self.disk_lse_dist = Poisson(rate)

        # When will the disk be repaired
        self.repair_time = 0
        # When the repair starts
        self.repair_start_time = 0 

        self.state = Disk.DISK_STATE_OK
        # When will the disk fail
        self.fail_time = 0

    def reset(self):
        self.state = Disk.DISK_STATE_OK
        self.fail_time = self.disk_fail_dist.draw()
        self.repair_time = 0
        self.repair_start_time = 0 
        return self.fail_time

    def is_failure(self):
        return self.state != Disk.DISK_STATE_OK

    # call it only when disk is failed
    def get_repair_process(self, current_time):
        return (1.0 * current_time - self.repair_start_time)/(self.repair_time - self.repair_start_time)

    def get_scrubbing_time(self):
        return self.disk_scrubbing_dist.draw()

    def generate_sector_errors(self, time):
        return self.disk_lse_dist.draw(time)

    def repair(self):
        self.state = Disk.DISK_STATE_OK

        self.fail_time = self.disk_fail_dist.draw() + self.repair_time
        self.repair_time = 0
        self.repair_start_time = 0
        return self.fail_time

    def fail(self):
        self.state = Disk.DISK_STATE_FAILED

        self.repair_time = self.disk_repair_dist.draw() + self.fail_time
        self.repair_start_time = self.fail_time 
        self.fail_time = 0
        return self.repair_time

    def get_next_event(self):
        if self.state == Disk.DISK_STATE_OK:
            return (Disk.DISK_EVENT_FAIL, self.fail_time)
        return (Disk.DISK_EVENT_REPAIR, self.repair_time)

class Raid:

    logger = logging.getLogger("sim")

    RAID_STATE_OK = "ok"
    RAID_STATE_FAILED = "failed"

    # A RAID consists of many disks
    def __init__(self, raid_type, disk_capacity, disk_fail_parms,
            disk_repair_parms, disk_lse_parms, disk_scrubbing_parms):
        # default is "mds_7_1"
        (self.type, d, p) = raid_type.split("_");
        self.data_fragments = int(d)
        self.parity_fragments = int(p)

        # the capacity in byte is disk_capacity * SECTOR_SIZE
        self.disk_capacity = disk_capacity

        self.logger.debug("RAID: raid_type = %s, data = %d, parity = %d, disk_capacity = %d" % (self.type, self.data_fragments, self.parity_fragments, self.disk_capacity))

        self.disks = [Disk(disk_fail_parms, disk_repair_parms,
            disk_lse_parms, disk_scrubbing_parms) for i in range(self.data_fragments + self.parity_fragments)]

        # the number of failed disks
        # > 0 indicates the RAID is degraded
        self.failed_disk_count = 0
        self.failed_disk_bitmap = 0

        self.critical_region = 0

        self.state = Raid.RAID_STATE_OK
        self.bytes_lost = 0
        self.lse_count = 0

    def reset(self, r_idx, mission_time):
        self.failed_disk_count = 0
        self.failed_disk_bitmap = 0
        self.critical_region = 0
        self.state = Raid.RAID_STATE_OK
        # for RAID failure
        self.bytes_lost = 0
        # for LSE
        self.lse_count = 0

        events = []
        for idx in range(len(self.disks)):
            event_time = self.disks[idx].reset()
            if event_time > mission_time:
                continue

            events.append((event_time, idx, r_idx))
        #events = sorted(events)

        return events

    # the region where data may loss
    def calc_critical_region(self, current_time):
        failed_disk_idx = bm_to_list(self.failed_disk_bitmap)
        self.critical_region = 1.0
        for idx in failed_disk_idx:
            r = 1.0 - self.disks[idx].get_repair_process(current_time)
            if r < self.critical_region:
                self.critical_region = r

    # Return True if the RAID is failure 
    def check_failure(self, current_time):
        if self.failed_disk_count <= self.parity_fragments:
            return False 

        # calculate the bytes lost if the RAID is failure
        # We assume the RAID is well rotated.
        data_fraction = 1.0 * self.data_fragments / (self.data_fragments + self.parity_fragments)

        self.logger.debug("RAID Failure")

        self.state = Raid.RAID_STATE_FAILED
        # We ignore the previously developed LSEs
        self.bytes_lost = self.disk_capacity * Disk.SECTOR_SIZE * self.critical_region * data_fraction

        return True             

    def check_sectors_lost(self, current_time):
        if self.failed_disk_count < self.parity_fragments:
            return False 

        # No longer fault tolerent
        # Any LSE will lead to data loss
        count = 0
        for disk in self.disks:
            if disk.is_failure() == True:
                continue
            # Should we take repair time into account?
            if random.random() < self.critical_region:
                time = disk.get_scrubbing_time()
                count += disk.generate_sector_errors(time)

        if count == 0:
            return False

        self.logger.debug("%d sectors lost" % count)

        #self.bytes_lost += count * Disk.SECTOR_SIZE
        self.lse_count += count
        return True

    def degrade(self, disk_idx):
        repair_time = self.disks[disk_idx].fail();
        self.failed_disk_count += 1
        self.failed_disk_bitmap = bm_insert(self.failed_disk_bitmap, disk_idx)
        return repair_time

    def upgrade(self, disk_idx):
        fail_time = self.disks[disk_idx].repair()
        self.failed_disk_count -= 1
        self.failed_disk_bitmap = bm_rm(self.failed_disk_bitmap, disk_idx)
        self.critical_region = 0
        return fail_time

    def update_to_event(self, event_time, disk_idx):
        event_type = 0
        next_event_time = 0

        if self.disks[disk_idx].is_failure() == True:
            next_event_time = self.upgrade(disk_idx)
            event_type = Disk.DISK_EVENT_REPAIR
        else:
            next_event_time = self.degrade(disk_idx)
            if self.failed_disk_count >= self.parity_fragments:
                self.calc_critical_region(event_time)
            event_type = Disk.DISK_EVENT_FAIL

        return (event_type, next_event_time)

def test():
    d = Disk()
    t = 0.0
    last_t = 0.0

    fail_time = 0
    repair_time = 0

    i = 0

    while t < 1000000000.0:
        i += 1
        (e, t) = d.get_next_event()
        print e,t
        if e == Disk.DISK_EVENT_FAIL:
            d.fail(t)
            fail_time += t - last_t
        elif e == Disk.DISK_EVENT_REPAIR:
            d.repair()
            repair_time += t - last_t
        else:
            exit(2)
        last_t = t
    print i, fail_time, repair_time, fail_time/i*2, repair_time/i*2

if __name__ == "__main__":
    test()
