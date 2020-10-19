#!/usr/bin/env python3
import unicornhat as unicorn
import requests
import json
import math
import configparser
import time
import logging
import systemd_stopper
from logging.handlers import TimedRotatingFileHandler
from PIL import Image
from threading import Thread

cycle_state = 0;

def main():
	stopper = systemd_stopper.install()
	init_log()
	logging.info("Starting")
	
	while(stopper.run):
		config = init_config()
		init_unicorn(config)
	
		if config.get('System', 'mode') == "jenkins":
			mode_jenkins(config,stopper)
		elif config.get('System', 'mode') == "image":
			mode_image(config)
		elif config.get('System', 'mode') == "image_cycle":
			mode_image_cycle(config)
		elif config.get('System', 'mode') == "animation":
			mode_animation(config,config.get('Animation', 'paths'));			
	logging.info("Stopping")	

def mode_jenkins(config,stopper):
	try:
		data = getData(config.get('Jenkins', 'request_url'))
	except:
		logging.info("Got Exception when downloading, will try again")
		time.sleep(5)
		return
	
	lights = calulate_lights(data,config.get('Jenkins', 'use_percentages')=="True")
	global thread_running
	
	if config.get('Jenkins', 'use_animation_red') == "True" and lights[1] > int(config.get('Jenkins', 'animation_limit')):
		if not thread_running:
			logging.info("Start animation red")
			thread = Thread(target = threaded_animation, args = (config,stopper,config.get('Jenkins', 'red_paths')))
			thread.start()
	elif config.get('Jenkins', 'use_animation_blue') == "True" and lights[1] == 0:
		if not thread_running:
			logging.info("Start animation blue")
			thread = Thread(target = threaded_animation, args = (config,stopper,config.get('Jenkins', 'blue_paths')))
			thread.start()
	
	else:
		if thread_running:
			thread_running = False;
			logging.info("Stop Animations")
		set_lights(lights)
	time.sleep(int(config.get('Jenkins', 'refresh_interval')))

def mode_image(config):
	img = read_image(config.get('Image', 'path'));
	set_lights_image(img)
	time.sleep(int(config.get('Image', 'refresh_interval')))
	
def mode_image_cycle(config):
	global cycle_state
	images = config.get('Image', 'paths').split(",");
	cycle_state = cycle_state % len(images)
	img = read_image(images[cycle_state])
	logging.info("Setting lights for image")
	set_lights_image(img)
	cycle_state = (cycle_state +1) % len(images)
	time.sleep(int(config.get('Image', 'refresh_interval')))

def mode_animation(config,path):
	global cycle_state
	images = path.split(",");
	cycle_state = cycle_state % len(images)
	img = read_image(images[cycle_state])
	set_lights_image(img)
	cycle_state = (cycle_state +1) % len(images)
	time.sleep(float(config.get('Animation', 'refresh_interval_ms'))/1000)

def init_config():
	config = configparser.ConfigParser()
	config.read('/home/pi/lights.ini')
	return config

def init_log():
	handler = TimedRotatingFileHandler("/home/pi/lights.log",when="D",interval=1,backupCount=5)
	logging.basicConfig(format='%(asctime)s %(message)s',level=logging.INFO,handlers=[handler])
	

	
def init_unicorn(config):
	unicorn.set_layout(unicorn.PHAT)
	unicorn.brightness(float(config.get('Lights', 'brightness')))

def getData(url):
	logging.info("Fetching %s",url)
	try:
		request = requests.get(url,timeout=1)
		data = json.loads(request.text)
		return data
	except:
		raise

			

def calulate_lights(data,pct):
	counter_blue = 0
	counter_red = 0
	for i in data["jobs"]:
		if  i["color"] == "blue":
			counter_blue +=1
		elif i["color"] == "red":
			counter_red +=1
	
	if pct:
		pct_blue = counter_blue/(counter_blue+counter_red)
		pct_red  = counter_red/(counter_blue+counter_red)

		if pct_blue > 0.5:
			lights_blue = int(math.floor(32*pct_blue))
		else:
			lights_blue = int(math.ceil(32*pct_blue))

		lights_red = 32- lights_blue
		return (lights_blue,lights_red)
	else:
		return (counter_blue,counter_red)
	
def set_lights(lights):
	logging.info("Setting %d red light and %d green lights",lights[1],lights[0])

	red_lights = lights[1]

	for y in reversed(range(4)):
		for x in reversed(range(8)):
			if (red_lights > 0):
				unicorn.set_pixel(x, y, 255, 0, 0)
				red_lights -=1
			else:
				unicorn.set_pixel(x, y, 0, 255, 0)
	unicorn.show()
			
def read_image(fname):
	im = Image.open(fname, "r")
	pixels = list(im.getdata())
	return pixels
    	
def set_lights_image(pixels):

	for y in reversed(range(4)):
		for x in reversed(range(8)):
			pixel = pixels.pop(0)	
			unicorn.set_pixel(x, y, int(pixel[0]), int(pixel[1]), int(pixel[2]))
			
	unicorn.show()
	
thread_running=False;
def threaded_animation(config,stopper,path):
	global thread_running;
	thread_running = True
	while thread_running and stopper.run:
		mode_animation(config,path);


if __name__ == '__main__':
    main()




