import os
import sys

# -------------------------------------
# Cross-module Python global variables
# -------------------------------------

well_config = []
roi_upper_left = (0,0)   # cordinates for upper left corner of upper left ROI
roi_width = 0            # box size
roi_height = 0 
roi_spacing_x = 0        # spacing between ROI centers
roi_spacing_y = 0        
ROIs = []                # list of upper left corners for all ROIs

# File information:
magi_directory = os.environ['HOME'] + '/magi'
font_directory = magi_directory + '/fonts'
data_directory = '/path/to/ramdisk'
card_filename = ""
logfile = magi_directory + "/magi_server.log"

gene_names = []       # list of all unique gene target names
gene_colors = []      # list of colors for each unique target

# GPIO pins:
PWM_PIN = 19			# Heater PWM
FAN_PIN = 26			# Case fan power
STATUS_LED_PIN = 4		# System status LED
IMAGER_LED_PIN = 13		# Fluorescence LED

# PID parameters:
PWM_BASE_FREQ = 5
Kp = 12.376
Ki = 0.991
Kd = 0

# PID setpoint pre-filter parameters:
a_val = 0.999949127
b_val = 0.000050873

b_bias = 0.82           # Temperature interpolation paramneter

# -------------------------------------
# Global Decorators
# -------------------------------------

# Decorator to log the name of the function being called:
def log_function_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling function: {func.__name__}", flush=True)
        sys.stdout.flush()
        return func(*args, **kwargs)
    return wrapper
