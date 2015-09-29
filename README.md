# SIM
high-fidelity reliability Simulator IMproved for Deduplication (SIMD)

This is a simulator for evaluating RAID reliability,
similar to High-Fideltiy Reliability Simulator (see [Greenan's HFRS](http://www.kaymgee.com/Kevin_Greenan/Software.html)).

Given a system mission time (such as 10 years), SIMD will report the probability of data loss during the system lifespan, as well as the average bytes lost. 
The accuracy depends on the iteration number and the RAID configuration.
More reliable the RAID is, more iterations are required to observse enough data loss events for higher accuracy.

