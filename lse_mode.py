from numpy import random
from mpmath import exp
from mpmath import mpf

mp.prec += 75

class LSEModel:
    def __init__(self, total_num_sectors=2147483648):
        # For a 1TB disk, the number of sectors is 1TB/512Byte = 2*1024*1024*1024
        self.total_num_sectors = total_num_sectors

        # data from [Elerath2009]
        # We just take a constant rate for all kinds of disk drives
        # But the rate may be related to the capacity
        self.lse_rate = mpf(1.08)/10000

    # Since we assume an exponential distribution for LSEs,
    # the number of LSE in a time period follows a poisson distribution.
    # Knuth gave a simple algorithm to generate random Poisson-distributed numbers.
    # See https://en.wikipedia.org/wiki/Poisson_distribution
    # The input is the scrubbing time
    def number_of_lse(self, time=336):
        # L = e^(-0.06048) = 0.96436...
        # 3.5% for at least one LSE
        L = mpmath.exp(-time*self.lse_rate)
        k = 0
        p = 1
        while True:
            k = k + 1
            u = random.uniform(0,1)
            p = p * u
            if p <= L:
                break
            
        # We have k-1 LSEs at this moment
        return k - 1 


if __name__ == "__main__":
    lse_model = LSEModel()
