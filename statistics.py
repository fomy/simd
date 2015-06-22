#
# A Class that couples samples from a simulation 
# with some statistics functions
#
# Kevin Greenan (kmgreen@cs.ucsc.edu)
#
# Improved by Min Fu (fumin@hust.edu.cn)
from mpmath import *
import random

#
# A Class that incapsulates a set of samples with 
# operations over those samples (i.e. statistics)
#
class Samples:

    #
    # Construct new instance with a list of samples
    #
    # @param samples: a set of samples, most observed in simulation
    #
    def __init__(self, samples):
        self.samples = samples

        self.byte_sum = mpf(0)
        self.prob_sum = mpf(0)
        for sample in samples:
            self.byte_sum += sample
            if sample > 0:
                self.prob_sum += 1

        self.num_samples = len(self.samples)

        # 
        # A static table used to estimate the confidence 
        # interval around a sample mean
        #
        self.conf_lvl_lku = {}
        self.conf_lvl_lku["0.80"] = mpf(1.281)
        self.conf_lvl_lku["0.85"] = mpf(1.440)
        self.conf_lvl_lku["0.90"] = mpf(1.645)
        self.conf_lvl_lku["0.95"] = mpf(1.960)
        self.conf_lvl_lku["0.995"] = mpf(2.801)

        self.byte_mean = None
        self.byte_dev = None
        self.byte_ci = None
        self.byte_re = None

        # used to calculate the probability of data loss
        self.prob_mean = None
        self.prob_dev = None
        self.prob_ci = None
        self.prob_re = None
        
    #
    # Calculate the sample mean based on the samples for this instance
    #
    def calcMean(self):
        self.byte_mean = self.byte_sum / self.num_samples
        self.prob_mean = self.prob_sum / self.num_samples

    #
    # Calculate the standard deviation based on the samples for this instance
    #
    def calcStdDev(self):
        
        if self.byte_dev == None:
            self.calcMean()
            sum_1 = mpf(0)
            sum_2 = mpf(0)
            for sample in self.samples:
                sum_1 += abs(power(sample - self.byte_mean, 2))
                if sample > 0:
                    sum_2 += abs(power(1 - self.prob_mean, 2))
                else:
                    sum_2 += abs(power(0 - self.prob_mean, 2))

    
            self.byte_dev = sqrt((mpf(1)/(self.num_samples-1)) * sum_1)
            self.prob_dev = sqrt((mpf(1)/(self.num_samples-1)) * sum_2)


    #
    # Calculate the confidence interval around the sample mean 
    #
    # @param conf_level: the probability that the mean falls within the interval
    #
    def calcConfInterval(self, conf_level="0.90"):
        
        if conf_level not in self.conf_lvl_lku.keys():
            print "%s not a valid confidence level!" % conf_level
            return None
    
        self.calcStdDev()

        self.byte_ci = abs(self.conf_lvl_lku[conf_level] * (self.byte_dev / sqrt(self.num_samples)))
        self.prob_ci = abs(self.conf_lvl_lku[conf_level] * (self.prob_dev / sqrt(self.num_samples)))

    #
    # Calculate the relative error 
    #
    # self.conf_lvl_lku[conf_level] * sqrt(Var)/sqrt(num_samples) / mean
    #
    def calcRE(self, conf_level="0.90"):
        if self.byte_mean == 0:
            return None
        
        self.calcConfInterval()

        self.byte_re = self.byte_ci / self.byte_mean
        self.prob_re = self.prob_ci / self.prob_mean

    def calcResults(self, conf_level="0.90"):
        self.calcRE(conf_level)
    
#
# Generate samples from a known distribution and verify the statistics
#
def test():
    
    num_samples = 1000
    samples = []
    mean = 0.5
    std_dev = 0.001
    for i in range(num_samples):
        samples.append(random.gauss(mean, std_dev))

    s = Samples(samples)    
        
    print "Mean: %s (%s): " % (s.calcMean(), mean)
    print "Std Dev: %s (%s): " % (s.calcStdDev(), std_dev)
    print "Conf. Interval: (%s, %s)" % s.calcConfInterval("0.995")

    (a,b,c,d) = s.getResults()
    print "Mean: %s (%s): " % (a, mean)
    print "Conf. Interval: (%s, %s)" % (b,c)
    print "Relative Error: (%s)" % d

if __name__ == "__main__":
    test()    



