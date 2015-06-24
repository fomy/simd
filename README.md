# SIM
high-fidelity reliability Simulator IMproved (SIM)

This is a simulator for evaluating RAID reliability.
SIM is similar to High-Fideltiy Reliability Simulator (see [Greenan's HFRS](http://www.kaymgee.com/Kevin_Greenan/Software.html)), but 10x faster.
SIM also has a more accurate Latent Sector Error model.

Given a system mission time (such as 10 years), SIM will report the probability of data loss during the system lifespan, as well as the average bytes lost. 
The accuracy depends on the iteration number and the RAID configuration.
More reliability the RAID is, more iterations are required to observse enough data loss events for higher accuracy.

