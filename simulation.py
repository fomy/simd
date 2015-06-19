import system
import statistics

class Simulation:
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

        self.system = None

    def simulate(self):
        sample_list = []

        for i in range(self.iterations):
            self.system = System(self.mission_time, self.raid_type, self.raid_num, self.disk_capacity, self.disk_fail_parms,
                self.disk_repair_parms, self.disk_lse_parms, self.disk_scrubbing_parms)

            result = self.system.run()

            if result[0] == System.EVENT_NOTHING_LOST:
                sample_list.append(0)
            elif result[0] == System.EVENT_RAID_FAILURE:
                sample_list.append(result[1])
            elif result[0] == System.EVENT_SECTORS_LOST:
                sample_list.append(sum(result[1:]))
            else:
                sys.exit(2)
        
        prob_result = None
        byte_result = None

        samples = Samples(sample_list)
        byte_result = samples.getResults()

        for i in range(len(sample_list)):
            if sample_list[i] > 0:
                sample_list[i] = 1

        samples = Samples(sample_list)
        prob_result = samples.getResults()

        # finished, return results
        # the format of result:
        # (mean, re, low_ci, high_ci)
        return (prob_result, byte_result) 
