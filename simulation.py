class Simulation:
    def __init__(self, mission_time, iterations, raid_type, raid_num, disk_capacity, 
            disk_fail_parms, disk_repair_parms, disk_lse_parms, disk_scrubbing_parms):
        self.iterations = iterations
        self.system = None

    def run():
        for i in range(self.iterations):
            self.system = System(mission_time, raid_type, raid_num, disk_capacity, disk_fail_parms,
                disk_repair_parms, disk_lse_parms, disk_scrubbing_parms)
            result = self.system.run()

        # finished, return results


