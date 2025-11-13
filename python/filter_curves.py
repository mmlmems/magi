# Code to filter LAMP data and calulate times to positive (TTPs)
#
# Will remove noise due to bubbles and spurious measurement errors

import numpy as np
from scipy.signal import butter, filtfilt, sosfiltfilt
import matplotlib.pyplot as plt
import pandas as pd

import config   # Cross-module global variables for all Python codes
from config import log_function_call

@log_function_call
def get_ttp(t,y):
    # Calculate slope at midpoint and project back to baseline to find TTP
    npoints = 2    # number of points before and after midpoint for linear fit
    idx = next((i for (i, val) in enumerate(y) if val > 0.5), None)   # idx of 1st value >0.5
    ttp = -0.001   # set initial value slightly less than zero
    if idx is not None:
        if idx > npoints+1 and idx < len(y)-npoints:
            # linear curve fit:
            t_ = t[idx-npoints:idx+npoints]
            y_ = y[idx-npoints:idx+npoints]
            m,b = np.polyfit(t_, y_, 1)
            ttp = -b/m     # define ttp as the x-axis intercept
    return ttp

@log_function_call
def filter(filename, filter_factor=10.0, cut_time=0.0, threshold=0):
    y_filtered = []
    ttp = []
    with open(filename) as f:
        df = pd.read_csv(f, header=None)
        t = df.iloc[:, 0].tolist()
        t = [(val-t[0])/60.0 for val in t]       # Start at t=0 and convert sec -> min
        cut_num = int(cut_time/t[-1] * len(t))   # number of initial data points to drop
        
        t = t[cut_num:]                          # Remove initial data points
        #t = [float(val-t[0]) for val in t]       # start time axis at t=0
    
        cols = df.columns[1:]
    
        # Set up Butterworth low-pass filter parameters:
        T = t[-1]                # sample Period (min)
        n = len(t)               # total number of samples
        fs = n/T                 # sample rate (cycles/min)
        f_nyquist = fs/2.0       # Nyquist frequency
        Wn = f_nyquist/filter_factor    # Low pass cutoff (cycles/min)
        if Wn >= f_nyquist:      # Wn < f_nyquist required
            Wn = 0.999*f_nyquist
        order = 6          # filter order       
        print(f'filter parameters: n={n}, T={T}, fs={fs}, f_nyquist={f_nyquist}, Wn={Wn}', flush=True)

        # Find TTP for each well:
        num_wells = len(config.well_config) * len(config.well_config[0])  # rows * cols
        for idx in range(1,num_wells+1):
            y = df.iloc[:,idx].tolist()
            y = y[cut_num:]          # Remove initial data points
            y = [float(val) for val in y]
    
            # Remove spurious dropped data:
            for i,val in enumerate(y):
                if val < 2 and i>0:
                    y[i] = y[i-1]

            # Implement the Butterworth low-pass filter:
            #
            # Pre-SOS filter:
            # b, a = butter(order, Wn, btype='low', analog=False, fs=fs)
            # yf = filtfilt(b, a, y)   # filtered data
            #
            # SOS filter is a better option:
            sos = butter(order, Wn, btype='low', analog=False, fs=fs, output='sos')
            yf = sosfiltfilt(sos, y)   # filtered data
            # print(yf, flush=True)

            # shift curves to min value:
            #y_shifted = [x-min(yf) for x in y]
            yf_shifted = [x-min(yf) for x in yf]
    
            # normalize to max value:
            #y_norm = [x/max(yf_shifted) for x in y_shifted]
            yf_norm = [x/max(yf_shifted) for x in yf_shifted]

            # If original data is below the given threshold value (noise background),
            # set all normed values to zero:
            if max(y) < threshold:
                yf_norm = [0 for _ in yf_norm]

            yf_dict = [{'x':t[i], 'y':yf_norm[i]} for i in range(len(t))]
            y_filtered.append(yf_dict)

            ttp.append(get_ttp(t,yf_norm))
            
    return({'ttp': ttp, 'y_filt': y_filtered})



