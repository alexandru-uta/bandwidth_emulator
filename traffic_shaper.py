import sys
import psutil
import time
import subprocess
from subprocess import Popen, PIPE

# defines the maximum allowed bandwidth, measured in Mbps
MAX_BW = 10500 # default 10 Gbit/s
#defines the min bw allowed
MIN_BW = 1400 # default 1Gbit/s
#defines the monitoring interval, measured in seconds
MONITORING_INTERVAL = 1
# the budget, measured in GBit
BUDGET = 100
# replenishing rate, measured in Gbit per second
REPL_RATE = 0.99

# enforce the traffic as in Google
def emulate_google():
    #enforce bandwidth of MAX_BW and do nothing else
    time.sleep(1)

def get_GBit_sent(t1, t2):
    return 8 * (t2 - t1) / (1000 * 1000 * 1000.0)

def limit_bw(bw_limit):
    # call wondershaper: first to reset, then to enforce
    Popen("echo $SPAS | sudo -S /home/aua400/installed_stuff/wondershaper/wondershaper -c -a ib0", shell=True).communicate() 
    command = "echo $SPAS | sudo -S /home/aua400/installed_stuff/wondershaper/wondershaper -u {} -a ib0".format(int(bw_limit * 1000))
    Popen(command, shell=True).communicate()
    print("bw has been limited to {} Mbps".format(bw_limit))    
    
# determine in how much time we spend the budget
# given our current performance (bw)    
def project_bw(sent_data, time, crnt_bw):
    crnt_effective_bw = sent_data / time
    time_left = TIME_WINDOW - time
    data_left = MAX_TRAFFIC - sent_data
    
    # data is in MBytes, so we need to transform to Mbits
    affordable_bw = (data_left / time_left) * (8)

    print("effective_bw = {}, affordable_bw = {}".format(crnt_effective_bw, affordable_bw))
    
    if crnt_effective_bw > affordable_bw:
        return affordable_bw
    else:
        return crnt_bw

def write_info(traffic, budget, bw):
    print("crnt traffic = {}, crnt budget = {}, crnt bw = {}".format(traffic, budget, bw))

# enforce the traffic as in AWS
def emulate_aws():
    crnt_budget = BUDGET
    # get the initial values
    initial_traffic = psutil.net_io_counters(pernic=True)["ib0"]
    # continuously compute the shaping logic
    crnt_bw = MAX_BW
    prev_bw = crnt_bw
    while True:
        time.sleep(MONITORING_INTERVAL)        
        # add tokens to the budget
        crnt_budget = min(BUDGET, crnt_budget + REPL_RATE)
        if (crnt_bw == MIN_BW) and (crnt_budget > 2):
            limit_bw(MAX_BW)
            crnt_bw = MAX_BW
        # measure what happened in the network
        crnt_traffic = psutil.net_io_counters(pernic=True)["ib0"]
        # check the current traffic
        recent_traffic = get_GBit_sent(initial_traffic.bytes_sent, crnt_traffic.bytes_sent)
        #update
        crnt_budget = max(0, crnt_budget - recent_traffic)
        initial_traffic = crnt_traffic
        #check whether we should limit
        if (crnt_bw == MAX_BW) and (crnt_budget == 0):
            limit_bw(MIN_BW)
            crnt_bw = MIN_BW
        #write data 
        write_info(recent_traffic, crnt_budget, crnt_bw)
        
    

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: traffic_shaper.py [aws, google]")
    else:
        limit_bw(MAX_BW)
        if sys.argv[1] == "aws":
            emulate_aws()
        elif sys.argv[1] == "google":
            emulate_google() 

