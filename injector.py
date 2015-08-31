#!/usr/bin/python
import getopt
from system import *
from statistics import *
from simd import *

def inject(eventfile, model):
    total_iterations = 0L

    systems_with_raid_failure = 0
    systems_with_lse = 0
    systems_with_data_loss = 0

    lse_count = 0
    raid_count = 0

    raid_failure_samples = Samples()
    lse_samples = Samples()

    for line in eventfile:
        # I=100000; iteration
        # R=0.2112; Raid Failure
        # S=1; Uncorruptable LSE
        # R=0.2121 S=1; Raid Failure and LSE
        systems_with_data_loss += 1
        for r in line.split():
            result = r.split("=")
            if result[0] is "I":
                iteration = long(result[1])

                lse_samples.addZeros(iteration-lse_count)
                raid_failure_samples.addZeros(iteration-raid_count)

                total_iterations += iteration
                systems_with_data_loss -= 1 

                lse_count = 0
                raid_count = 0

                continue

            if result[0] is "R":
                systems_with_raid_failure += 1
                corrupted_area = float(result[1])

                fraction = model.raid_failure(corrupted_area)

                raid_failure_samples.addSample(fraction)

                raid_count += 1

                #print >>sys.stderr, "R=%f -> %f" % (corrupted_area, fraction),
            elif result[0] is "S":
                systems_with_lse += 1
                lse_num = int(result[1])

                loss = model.sector_error(lse_num)

                lse_samples.addSample(loss)

                lse_count += 1

                #print >>sys.stderr, "S=%d -> %d" % (lse_num, loss),

        #print >>sys.stderr, ""

    #print >>sys.stderr, "I=%d" % total_iterations

    raid_failure_samples.calcResults("0.95")
    lse_samples.calcResults("0.95")

    return (raid_failure_samples, lse_samples, systems_with_data_loss, systems_with_raid_failure,
            systems_with_lse, total_iterations)

if __name__ == "__main__":
    try:
        (opts, args) = getopt.gnu_getopt(sys.argv[1:], "e:fdwt:", ["events", "filelevel", "dedup", "weighted", "trace"]) 
    except:
        sys.exit(1)

    eventfile = None

    filelevel = False
    dedup = False
    weighted = False
    tracefile = None

    for o, a in opts:
        if o in ("-e", "--events"):
            eventfile = open(a, "r")
        elif o in ("-f", "--filelevel"):
            filelevel = True
        elif o in ("-d", "--dedup"):
            dedup = True
        elif o in ("-w", "--weighted"):
            weighted = True
        elif o in ("-t", "--trace"):
            tracefile = a
        else:
            print "invalid option"
            sys.exit(1)

    model = None
    if filelevel == False:
        if dedup == False:
            model = DeduplicationModel_Chunk_NoDedup(weighted)
        else:
            model = DeduplicationModel_Chunk_Dedup(tracefile, weighted)
    else:
        if dedup == False and weighted == False:
            model = DeduplicationModel_File_NoDedup_NotWeighted(tracefile)
        elif dedup == False and weighted == True:
            model = DeduplicationModel_File_NoDedup_Weighted(tracefile)
        elif dedup == True:
            model = DeduplicationModel_File_Dedup(tracefile, weighted)
        else:
            print "invalid model"
            sys.exit(1)

    (raid_failure_samples, lse_samples, systems_with_data_loss, systems_with_raid_failure, systems_with_lse, total_iterations) = inject(eventfile, model)

    print_result(model, raid_failure_samples, lse_samples, systems_with_data_loss, systems_with_raid_failure, systems_with_lse, total_iterations, "mds_14_2", 1, 2*1024*1024*1024, model.df)
    eventfile.close()
