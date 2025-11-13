# Multiplexed Array Gene Imager (MAGI)

## Imager Hardware:

* Raspberry Pi Zero 2 W (Python3, Raspberry Pi OS)
* Pi Camera (InnoMaker CAM OV5647, 5MP)

## Installation 

* May need to edit /boot/firmware/config.txt before OS installation to enable camera by adding the following lines:
   `start_x=1       # Enable the camera firmware
   gpu_mem=128      # Allocate GPU memory
   dtoverlay=ov5647 # Define camera module sensor`


* Copy all Python code files to `~/magi` on the Pi

* Copy `setup.sh` to the Pi and execute the script to install required Python modules, set up ram disk, synchronize system time, and modify crontab to start the MAGI server at boot:
   `sudo ./setup.sh`

## MAGI Operation:

With the Pi running, open the MAGI client application, or open `magi.html` on the client computer

# Code Summary:

## Pi:

* `magi_server.py`
	- handle Javascript client <--> Python server communication
	- manage PID control of heater
	- access `imager.py` to send data to client
* `imager.py`
	- get & process data from the camera
* `filter_curves.py`
	- filter noise and evaluate time-to-positive values

## Client:

* `magi.html`
	- client user interface
* `css/style.css`
	- style sheet for plot.html
* `js/canvasjs.min.js`
	- Javascript code for plotting (js folder must be in same directory as `magi.html` if running from a browser)
* `fonts/OpenSans.ttf`
	- Truetype font for image annotations
