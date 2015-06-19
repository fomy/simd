import mpmath
import random

class Weibull:
    def __init__(self, shape, scale, location):
        self.shape = mpf(shape)
        self.scale = mpf(scale)
        self.location = mpf(location)

    def draw(self):
        return random.weibullvariate(self.scale, self.shape) + self.location

class Poisson:
    def __init__(self, rate):
        self.rate = rate

    # Knuth gave a simple algorithm to generate random Poisson-distributed numbers.
    # See https://en.wikipedia.org/wiki/Poisson_distribution
    # The input is the scrubbing time
    def draw(self, time=336):
        L = mpmath.exp(-time*self.rate)
        k = 0
        p = 1
        while True:
            k = k + 1
            u = random.uniform(0,1)
            p = p * u
            if p <= L:
                break

        return k - 1 


