import logging
from stochastic import *

class Disk:

    STATE_OK = "state ok"
    STATE_FAILED = "state failed"

    EVENT_FAIL = "event disk fail"
    EVENT_REPAIR = "event disk repair"

    SECTOR_SIZE = 512 # bytes

    logger = logging.getLogger("sim")

    def __init__(self, disk_capacity=2147483648, disk_fail_parms=(1, 461386,0), disk_repair_parms=(1,12,0),
            disk_lse_parms=(0.000108), disk_scrubbing_parms=(3,168.0,6)):

        # the capacity in byte is disk_capacity * SECTOR_SIZE
        self.disk_capacity = disk_capacity

        self.logger.debug("Disk: disk_capacity = %d, disk_fail_parms = %s, disk_repair_parms = %s, \
disk_lse_parms = %s, disk_scrubbing_parms = %s" % 
            (disk_capacity, str(disk_fail_parms), str(disk_repair_parms), str(disk_lse_parms), str(disk_scrubbing_parms)))

        (shape, scale, location) = disk_fail_parms
        self.disk_fail_dist = Weibull(shape, scale, location);
        (shape, scale, location) = disk_repair_parms
        self.disk_repair_dist = Weibull(shape, scale, location);
        (shape, scale, location) = disk_scrubbing_parms
        self.disk_scrubbing_dist = Weibull(shape, scale, location);

        (rate) = disk_lse_parms
        self.disk_lse_dist = Poisson(rate)

        # When will the disk be repaired
        self.repair_time = mpf(0)
        # When the repair starts
        self.repair_start_time = mpf(0) 

        self.state = Disk.STATE_OK
        # When will the disk fail
        self.fail_time = self.disk_fail_dist.draw()

    def is_failure(self):
        if self.state == Disk.STATE_OK:
            return False
        return True

    def get_repair_process(self, current_time):
        if self.state == Disk.STATE_OK:
            return mpf(1)
        return (current_time - self.repair_start_time)/(self.repair_time - self.repair_start_time)

    def get_scrubbing_time(self):
        return self.disk_scrubbing_dist.draw()

    def generate_sector_errors(self, time):
        return self.disk_lse_dist.draw(time)

    def repair(self, current_time):
        self.repair_time = mpf(0)
        self.repair_start_time = mpf(0)
        self.state = Disk.STATE_OK
        self.fail_time = self.disk_fail_dist.draw() + current_time

    def fail(self, current_time):
        self.state = Disk.STATE_FAILED
        self.repair_time = self.disk_repair_dist.draw() + current_time
        self.repair_start_time = current_time
        self.fail_time = mpf(0)

    def get_next_event(self):
        if self.state == Disk.STATE_OK:
            return (Disk.EVENT_FAIL, self.fail_time)
        return (Disk.EVENT_REPAIR, self.repair_time)

class Raid:

    logger = logging.getLogger("sim")

    # A RAID consists of many disks
    def __init__(self, raid_type, disk_capacity, disk_fail_parms,
            disk_repair_parms, disk_lse_parms, disk_scrubbing_parms):
        # default is "mds_7_1"
        (self.type, d, p) = raid_type.split("_");
        self.data_fragments = int(d)
        self.parity_fragments = int(p)

        self.logger.debug("RAID: raid_type = %s, data = %d, parity = %d" % (self.type, self.data_fragments, self.parity_fragments))

        self.disks = [Disk(disk_capacity, disk_fail_parms, disk_repair_parms,
            disk_lse_parms, disk_scrubbing_parms) for i in range(self.data_fragments + self.parity_fragments)]

        self.failed_disk_num = 0

        # the number of failed disks
        self.fail_count = 0

    def get_failed_disks(self):
        failed_disks = []
        for disk in self.disks:
            if disk.is_failure() == True:
                failed_disks.append(disk)
        return failed_disks

    # the region where data may loss
    def get_critical_region(self, current_time):
        region = 1.0
        for disk in self.disks:
            if disk.is_failure() == False:
                continue
            r = 1 - disk.get_repair_process(current_time)
            if r < region:
                region = r
        return region

    # Return bytes we lost if the RAID is failure 
    def check_failure(self, current_time):
        if self.fail_count > self.parity_fragments:
            # calculate the bytes lost if the RAID is failure
            # We assume the RAID is well rotated.
            data_fraction = mpf(1) * self.data_fragments / (self.data_fragments + self.parity_fragments)

            self.logger.debug("RAID Failure")

            r = self.get_critical_region(current_time)

            return self.disks[0].disk_capacity * Disk.SECTOR_SIZE * r * data_fraction
        return 0

            
    def check_sectors_lost(self, current_time):
        if(self.fail_count < self.parity_fragments):
            return 0
        # No longer fault tolerent
        # Any LSE will lead to data loss

        critical_region = self.get_critical_region(current_time)

        count = 0
        for disk in self.disks:
            if disk.is_failure() == True:
                continue
            time = disk.get_scrubbing_time()
            # Should we take repair time into account?
            if random.random() < critical_region:
                count += disk.generate_sector_errors(time)

        if count == 0:
            return 0

        self.logger.debug("%d sectors lost" % count)

        return count * Disk.SECTOR_SIZE

    def get_next_event(self):
        disk_idx = 0
        (event_type, event_time) = self.disks[0].get_next_event()
        for idx in range(1, len(self.disks)):
            (type, time) = self.disks[idx].get_next_event()
            if time < event_time:
                event_time = time
                event_type = type
                disk_idx = idx

        return (disk_idx, event_type, event_time)

    def degrade(self, disk_idx, event_time):
        self.disks[disk_idx].fail(event_time);
        self.fail_count += 1

    def upgrade(self, disk_idx, event_time):
        self.disks[disk_idx].repair(event_time)
        self.fail_count -= 1

    def update_to_event(self, disk_idx, event_type, event_time):
        if event_type == Disk.EVENT_FAIL:
            self.degrade(disk_idx, event_time)
        elif event_type == Disk.EVENT_REPAIR:
            self.upgrade(disk_idx, event_time)
        else:
            sys.exit(2)


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
        if e == Disk.EVENT_FAIL:
            d.fail(t)
            fail_time += t - last_t
        elif e == Disk.EVENT_REPAIR:
            d.repair(t)
            repair_time += t - last_t
        else:
            exit(2)
        last_t = t
    print i, fail_time, repair_time, fail_time/i*2, repair_time/i*2

if __name__ == "__main__":
    test()
