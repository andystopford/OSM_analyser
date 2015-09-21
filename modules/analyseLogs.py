#!/usr/bin/python
import xml.etree.cElementTree as ET
import sys
import os.path
import shutil
import random
from math import pi
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from decimal import Decimal
from collections import namedtuple
import glib

# Global Variables
point_list = []
location_list = []



def check_logs():

	path = './logs/'	
	for file in os.listdir(path):
		if file.endswith(".gpx"):
			fileName = str(file)
			filePath = path + fileName
			job_dir_sort(fileName, filePath)


def job_dir_sort(fileName, filePath):

	tree = ET.parse(filePath)
	root = tree.getroot()
	
	length = len(root.tag)		#Get rid of XMLNS nonsense
	length -= 3					#
	name_space = root.tag[0:length]	#

	if root[1].tag == str(name_space + 'wpt'):			#Check if the file has been job-tagged
		jobID = root[1][2].text						#grab the ID
		if not os.path.exists('./logs/' + jobID):	#and make a new directory if reqd.
			os.makedirs('./logs/' + jobID)
		shutil.move(filePath, './logs/' + jobID + '/' + fileName)	#Move the file
	print name_space



def get_data(sel_date):

	point_list = []
	pointID = 0
	time = ''
	lat = ''
	lon = ''
	course = ''	
	data_file = ''

	data_file = './logs/' + sel_date + '.gpx'
	
	if os.path.isfile(data_file):
		tree = ET.parse('./logs/' + sel_date + '.gpx')	# Should there be "with open as ..."?
		root = tree.getroot()

		name_space = root.tag[:-3]

		if root[1].tag == name_space + 'wpt':	# Check if the file has been job-tagged
			track = root[2]
			trackSeg = root[2][0]
			jobID = root[1][2].text
		else:
			track = root[1]
			trackSeg = root[1][0]			

		for trackPnt in trackSeg:		
			if trackPnt.tag == name_space + 'trkpt':
				lat = trackPnt.attrib['lat']
				lat = Decimal(lat)
				lat = round(lat, 4)
				lon = trackPnt.attrib['lon']
				lon = Decimal(lon)
				lon = round(lon, 4)

			for item in trackPnt.iter():	# i.e. iterate through children of trackPnts
				if item.tag == name_space + 'time':
					time = item.text 
					time = time[11:16]	# We only want hours and minutes.

				if item.tag == name_space + 'course':
					course = item.text	

			a_point = TrackPoint(pointID, time, lat, lon, course)
			point_list.append(a_point)
			pointID += 1

		#get_locations(jobID)
		#get_times(jobID, point_list)
		return jobID, point_list



def get_locations(jobID):

	""" Uses the jobID recorded in the .gpx file to get pre-selected 
	start and stop points and add an instance of Class Location to 
	the location list. Multiple locations can be added to the list."""
	places = {}
	path = './Data/Localities.xml'
	with open(path, "r") as fo:
		tree = ET.ElementTree(file = path)
        root = tree.getroot()
        for child in root:
        	if child.attrib['id'] == jobID:
        		name = child.attrib['name']
        		sel_job = child
        		for child in sel_job:
        			place = child.attrib['place']
        			lat = child.attrib['lat']
        			lon = child.attrib['lon']
        			coords = (lat, lon)
        			places[place] = coords	# make a dictionary of coord tuples
        		a_location = Location(jobID, name, places)
        		location_list.append(a_location)


def get_times(jobID, point_list, searchRad):	
	startStop_list = []
	#searchRad = 0.007	#This is just decimal degrees
	searchRad = searchRad * 0.0001

	for location in location_list:
		if location.jobID == jobID:
			name = location.name 	# i.e. customer name
			for key in location.places:
				startStop_place = key
				startStop_lat = float(location.places[key][0])
				startStop_lon = float(location.places[key][1])

				for point in point_list:
					ID = point.pointID
					lat = point.lat		
					lon = point.lon
					time = point.time
					course = point.course

					if ((startStop_lat - searchRad) <= lat <= (startStop_lat + searchRad)
						and (startStop_lon - searchRad) <= lon <= (startStop_lon + searchRad)):
						startStop_list.append(point)
						

	startStop_list.sort(key=lambda point: point.pointID)	# works without the key				
	#for item in startStop_list:
	#	print item.pointID, item.time

	start = startStop_list[0].time
	stop = startStop_list[-1].time
	
	start_time = convert_time(start)
	stop_time = convert_time(stop)

	time_working(start_time, stop_time)


def convert_time(time):
	hours = int(time[0:2])
	mins = int(time[3:5])
	return hours, mins

def time_working(start, stop):
	start_hour = start[0]*60
	start_min = start[1]
	stop_hour = stop[0]*60
	stop_min = stop[1]
	time = (stop_hour + stop_min) - (start_hour + start_min)
	hours = time / 60
	mins = time % 60
	print hours, mins


#################################################################################

class TrackPoint:
	def __init__(self, pointID, time, lat, lon, course):	
		self.pointID = pointID
		self.time = time
		self.lat = lat
		self.lon = lon
		self.course = course
	def get_pointID(self):
		return self.pointID
	def get_time(self):
		return self.time
	def get_lat(self):
		return self.lat
	def get_lon(self):
		return self.lon
	def get_course(self):
		return self.course


class Location:

	""" 'name' is for display purposes. 'places' is a dictionary
	of coordinate tuples, indexed by names, e.g 'The Yard' """
	def __init__(self, jobID, name, places):
		self.jobID = jobID
		self.name = name
		self.places = places
	def get_jobID(self):
		return self.jobID
	def get_name(self):
		return self.name
	def get_places(self):
		return self.places
	



#check_logs()
#get_data()
#get_locations("grov")
#get_locations("dan")
#print location_list[0].places

"""
for location in location_list:
	#print item.jobID
	if location.jobID == 'grov':
		name = location.name
		print location.places
		for key in location.places:
			print key
			print location.places[key][0]
			print location.places[key][1]

"""