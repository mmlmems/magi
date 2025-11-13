import time
from picamera2 import Picamera2
import numpy as np
import csv
import json
import os
import sys
import filter_curves
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO

import config   # Cross-module global variables for all Python codes
from config import log_function_call

import signal

GPIO.setmode(GPIO.BCM)
GPIO.setup(config.IMAGER_LED_PIN, GPIO.OUT, initial=GPIO.LOW) 

# Image size:
w = 640         # min of 64, max of 2592 for 5MP camera
h = int(3*w/4)  # native 4:3 aspect ratio
res = (w,h)  

cam = Picamera2() 

# Create a flat list of ROI dicts from well_config 2D array:
@log_function_call
def setup_ROIs():
    config.ROIs = []
    rows = len(config.well_config)
    for r in range(rows):
        cols = config.well_cols = len(config.well_config[0])
        for c in range(cols):
            config.ROIs.append( {
                "target": str(config.well_config[r][c]),
                "x": config.roi_upper_left[0] + config.roi_spacing_x * c,
                "y": config.roi_upper_left[1] + config.roi_spacing_y * r
                } )
    print(config.ROIs, flush=True)
    sys.stdout.flush()


def hex_to_rgb(h):   # convert "#rrggbb" to [R,G,B]
    return [int(h[i:i+2], 16) for i in (1, 3, 5)]

@log_function_call
def annotate_image(img, add_roi=False):      # Add timestamp and ROIs to image
    try:
        img = img.convert('RGBA')   # convert captured image to support an alpha channel
        img_tmp = Image.new('RGBA', img.size, (255, 255, 255, 0))  # create new image with ROIs only
        draw = ImageDraw.Draw(img_tmp)
        # add timestamp:
        font = ImageFont.truetype(config.font_directory + "/" + "OpenSans.ttf", 12) 
        draw.text((10,10), config.card_filename, font=font)  
        month = time.strftime('%b')
        day = time.strftime('%d')
        year = time.strftime('%Y')
        draw.text((10,20), f'{month} {day} {year} @ {time.strftime("%H:%M:%S")}', font=font)
        # draw.text((10,20), time.strftime("%Y%m%d_%H:%M:%S"), font=font)
        # add ROIs:
        if add_roi:
            for roi in config.ROIs:
                roi_lower_right = (roi['x'] + config.roi_width, roi['y'] + config.roi_height)
                idx = config.gene_names.index(roi['target'])      # find index in gene_names matching current ROI targe
                fill_color = hex_to_rgb(config.gene_colors[idx])  # convert "#rrggbb" to [R,G,B]
                fill_color.append(64)                               # Add alpha channel for transparency
                draw.rectangle([(roi['x'],roi['y']), roi_lower_right], outline='#ffffff', fill=tuple(fill_color))   # Draw ROI
                font = ImageFont.truetype(config.font_directory + "/" + "OpenSans.ttf", 9)         # Add well target text
                text_position = (roi['x'] + config.roi_width + 1, roi['y'])
                draw.text(text_position, roi['target'],'#ffffff',font=font)
        img_new = Image.alpha_composite(img, img_tmp)  # composite captured & ROI images
        img = None
        img_tmp = None
        return(img_new)
    except Exception as e:
        print('Exception in annotate_image():', flush=True)
        print(f'{type(e)}: {e}', flush=True)

@log_function_call
def adjust_settings(exposure_time_ms, analogue_gain, color_gains):
    global cam
    try:
        cam.set_controls({
            "AeEnable": False,                 # auto update of gain & exposure settings
            "AwbEnable": False,                # auto white balance
            "ExposureTime": int(exposure_time_ms*1e3),   # units of microseconds
            "AnalogueGain": float(analogue_gain),   # range [0,6.0] ?
            "ColourGains": color_gains              # (red,blue) gains, range [0,32.0]
        })
        time.sleep(3)   # time to stabilize settings
        print('adjust_settings() done', flush=True)
        return('adjust_settings() done')
    except Exception as e:
        print(f'error in adjust_settings(): {e}', flush=True)

@log_function_call
def setup_camera(exposure_time_ms=50, analogue_gain=0.5, color_gains=(1.2,1.0)):    # Set up camera
    global cam
    cam_config = cam.create_still_configuration(main={"size": res})
    cam.configure(cam_config)
    adjust_settings(exposure_time_ms, analogue_gain, color_gains)
    print('Picamera2 setup complete', flush=True)
    os.makedirs(config.data_directory, exist_ok=True)

def roi_avg(image, roi):   # Return average pixel values in ROI
    r,b,g = 0,0,0
    px = roi['x']
    py = roi['y']
    for x in range(int(px),int(px+config.roi_width)):
        for y in range(int(py),int(py+config.roi_height)):
            xy = (x,y)
            r += image.getpixel(xy)[0]
            g += image.getpixel(xy)[1]
            b += image.getpixel(xy)[2]
    pixels = config.roi_width * config.roi_height;
    r = int(100*r/pixels);
    g = int(100*g/pixels);
    b = int(100*b/pixels);
    return((r,g,b))

# TimeoutException class, signal handler function, and decorator
# to capture timeouts during image capture.
#
# Implemented to handle apparent hardware error: "Zero sequence expected 
# for first frame (got 1)" but did not fix this problem since it
# seems the camera needs to be restarted (i.e. the Pi must be rebooted)
# after encountering this error.
#
# Timeout handling has been left here in case other possible imager
# errors may also lead to image capture timeouts...
class TimeoutException(Exception):
    pass
# signal handler function:
def timeout_handler(signum, frame):       
    raise TimeoutException("Function execution exceeded the timeout limit.")
# decorator to apply signal handler:
def add_timeout(func, timeout_sec=30):
    def wrapper(*args, **kwargs):
        global cam
        # Set the signal handler for the timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_sec)  # Set the timeout
        try:
            result = func(*args, **kwargs)
            return result
        except TimeoutException:
            """
            print('timeout exception, re-initializing the camera', flush=True)
            cam.close()
            cam = Picamera2() 
            setup_camera()
            """
            return(None)
        finally:
            signal.alarm(0)  # Cancel the alarm            
    return wrapper

# Capture a single image with timeout handling: 
@add_timeout
def capture_single_image():
    return(cam.capture_image("main"))       # capture PIL image

# Extract fluorescence measurements from ROIs in image:
@log_function_call
def get_image_data():
    try:
        cam.start()
        GPIO.output(config.IMAGER_LED_PIN, GPIO.HIGH)    # Turn on LED
        image = None   # start with None to enter loop
        while image is None:
            # If image capture fails, capture_single_image() + add_timeout()
            # decoration restarts the camera and returns None, forcing
            # another image to be captured:
            image = capture_single_image()               # capture PIL image
        cam.stop()
        GPIO.output(config.IMAGER_LED_PIN, GPIO.LOW)     # Turn off LED
        # Get average pixel value for each ROI:
        roi_avgs = []
        for roi in config.ROIs: 
            roi_avgs.append(roi_avg(image, roi)[1])  # green channel
        # Add timestamp & ROI averages to temp data file:
        timestamp = [int(time.time())]        # 1st entry is the time stamp
        with open(config.data_directory + '/temp_data.csv', 'a') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerow(timestamp + roi_avgs)
        image = None
        return(roi_avgs)
    except Exception as e:
        print(f'Exception in get_image_data(): {e}', flush=True)
        return(f'Exception in get_image_data(): {e}')

# Return a PIL image with time stamp (add colored ROI boxes if add_ROIs true):
@log_function_call
def get_image(add_ROIs):
    try:
        cam.start()
        GPIO.output(config.IMAGER_LED_PIN, GPIO.HIGH)
        image = capture_single_image()     # capture PIL image
        cam.stop()
        GPIO.output(config.IMAGER_LED_PIN, GPIO.LOW)
        image = annotate_image(image, add_ROIs)
        buffer = BytesIO()                 # create a buffer to hold the image
        image.save(buffer, format="PNG")   # Convert image to PNG
        png_image = buffer.getvalue()
        png_base64 = base64.b64encode(png_image).decode('utf-8')  # Encode as base64
        image = None
        png_image = None
        return(f"data:image/png;base64,{png_base64}")
    except Exception as e:
        print(f'Exception in get_image(): {e}', flush=True)
        return(f'Exception in get_image(): {e}')

@log_function_call
def end_imaging():
    # move temp data contents to time-stamped file:
    output_filename = time.strftime("%Y%m%d_%Hh%Mm%Ss")
    os.rename(config.data_directory + '/temp_data.csv', config.data_directory + '/' + output_filename + '.csv')
    print(f'end_imaging() called, output_filename={output_filename}', flush=True)
    sys.stdout.flush()
    return(output_filename)

@log_function_call
def analyze_data(filename, filter_factor, cut_time, threshold):
    # filter() returns: {'ttp': ttp, 'y_filt': y_filtered}
    # where ttp is a list of TTP values for each well, and
    # y_filtered is a list of data with format:
    #   [ [{x: t1, y: val1}, {x: t2, y: val2}, ...]  <- well 1
    #     [{x: t1, y: val1}, {x: t2, y: val2}, ...]  <- well 2
    #      ... ]                                     <- etc
    results = filter_curves.filter(
        config.data_directory + '/' + filename + '.csv', 
        float(filter_factor), 
        float(cut_time), 
        int(threshold) ) 
    # Save filtered data to csv file:
    y_filt = results['y_filt']
    time_min = [entry['x'] for entry in y_filt[0]]  # time value, 1st well (same for all wells)
    columns = []
    for well in y_filt:
        columns.append([entry['y'] for entry in well])
    with open(config.data_directory + '/' + filename + '_filt.csv', 'a') as f:
        #fieldnames = ["time (min)", "fluorescence"]
        writer = csv.writer(f)
        headers = ['time (min)'] + [f'well {i}' for i in range(len(columns))]
        writer.writerow(headers)
        for i, t in enumerate(time_min):
            row = [t] + [values[i] for values in columns]
            writer.writerow(row)
    # Return original dictionary:
    return(results)

