from mpmath import *
import random

class Weibull:
    def __init__(self, shape, scale, location=0):
        self.shape = mpf(shape)
        self.scale = mpf(scale)
        self.location = mpf(location)

    def draw(self):
        v = random.weibullvariate(self.scale, self.shape)
        if v < self.location:
            return self.location
        return v

class Poisson:
    def __init__(self, rate):
        self.rate = rate

    # Knuth gave a simple algorithm to generate random Poisson-distributed numbers.
    # See https://en.wikipedia.org/wiki/Poisson_distribution
    # The input is the scrubbing time
    def draw(self, time=336):
        L = exp(-time*self.rate)
        k = 0
        p = 1
        while True:
            k = k + 1
            u = random.uniform(0,1)
            p = p * u
            if p <= L:
                break

        return k - 1 

def test():
    #w = Weibull(1, 12, 0)
    w = Weibull(1.2, 461386, 0)
    v = 0
    for i in range(100000):
        v += w.draw()
    print v/100000

if __name__ == "__main__":
    test()
