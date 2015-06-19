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

        self.sample_sum = mpf(0)
        for sample in samples:
            self.sample_sum += sample

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

        self.sample_mean = None
        self.std_dev = None
        self.conf_interval = None
        
    #
    # Calculate the sample mean based on the samples for this instance
    #
    def calcMean(self):
        
        if self.sample_mean == None:
            self.sample_mean = self.sample_sum / self.num_samples

        return self.sample_mean

    #
    # Calculate the standard deviation based on the samples for this instance
    #
    def calcStdDev(self):
        
        if self.std_dev == None:
            mean = self.calcMean()
            sum = mpf(0)
            for sample in self.samples:
                sum += abs(power(sample - mean, 2))
    
            self.std_dev = sqrt((mpf(1)/(self.num_samples-1)) * sum)

        return self.std_dev

    #
    # Calculate the relative error 
    #
    # self.conf_lvl_lku[conf_level] * sqrt(Var)/sqrt(num_samples) / mean
    #
    def calcRE(self, conf_level="0.90"):
        
        return (self.conf_lvl_lku[conf_level] * (self.calcStdDev() / sqrt(self.num_samples))) / self.calcMean()

    #
    # Calculate the confidence interval around the sample mean 
    #
    # @param conf_level: the probability that the mean falls within the interval
    #
    def calcConfInterval(self, conf_level="0.90"):
        
        if conf_level not in self.conf_lvl_lku.keys():
            print "%s not a valid confidence level!" % conf_level
            return None
    
        half_width = abs(self.conf_lvl_lku[conf_level] * (self.calcStdDev() / sqrt(self.num_samples)))

        lower = abs(self.sample_mean - half_width)
        upper = self.sample_mean + half_width

        return (lower, upper)

    def getResults(self, conf_level="0.90"):
        (lower, upper) = self.calcConfInterval()
        return (self.calcMean(), 100*self.calcRE(), lower, upper, self.calcStdDev())

    
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



