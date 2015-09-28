#!/usr/bin/env python
# coding=utf8

######################################################################

#Copyright (C)2015 Andy Stopford                                
#
#This is free software: you can redistribute it and/or modify 
#under the terms of the GNU General Public License
#as published by the Free Software Foundation; version 2.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, see <http://www.gnu.org/licenses/>.

#######################################################################


import sys
import os.path
sys.path.append("./modules")
import random
from math import*#pi, radians
from gi.repository import Gtk, Pango
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import pytz     # For local time adjustment
from datetime import datetime, timedelta
import glib
import time
import xml.etree.cElementTree as ET
from analyseLogs import*
from osmLayers import*
import geopy, geopy.distance
from bisect import bisect_left   # For getting closest numbers in list
#print str(Gtk.get_major_version()) + "." + str(Gtk.get_minor_version()) + "." + str(Gtk.get_micro_version())

from gi.repository import OsmGpsMap as osmgpsmap
print "using library: %s (version %s)" % (osmgpsmap.__file__, osmgpsmap._version)

assert osmgpsmap._version == "1.0"
SHOW_TRACK = True
assert osmgpsmap._version >= "0.7.0"


class MainWindow():
    def __init__(self):

        self.osm = osmgpsmap.Map()
        builder = Gtk.Builder()
        builder.add_from_file("mainWindow.glade")
        self.osm.set_center_and_zoom(51.12, 0.27, 14)
        window = builder.get_object("window1")
        map_frame = builder.get_object("viewport1")
        map_frame.add(self.osm)
        window.show_all()       
        self.osm.layer_add(osmgpsmap.MapOsd(show_dpad=True, show_zoom=True,
            show_crosshair=True))
        self.log_list = []
        self.point_list = []
        self.selected_date = ''
        self.list_store = Gtk.ListStore(str)

        # Displays
        self.status_bar = builder.get_object("status")
        self.button_add = builder.get_object('button_add')
        renderer = Gtk.CellRendererText()
        self.calendar = builder.get_object("calendar1")
        self.timeline = builder.get_object("timeline")
        self.timeline.set_range(0, 100)        
        self.display_date = builder.get_object("display_date")
        self.display_job = builder.get_object("display_job")
        self.display_hours = builder.get_object("display_hours")
        self.display_start = builder.get_object("display_start")
        self.display_finish = builder.get_object("display_finish")
        self.display_hours = builder.get_object("display_hours")
        self.display_time = builder.get_object("display_time")
        self.button_start = builder.get_object("button_mark_start")
        self.button_finish = builder.get_object("button_mark_finish")
        self.button_back = builder.get_object("button_back")
        self.button_forward = builder.get_object("button_forward")
        
        ###############################################################
        # Connect signals
        self.osm.connect('button_release_event', self.lat_lon_display)
        self.button_start.connect('clicked', self.mark_time)
        self.button_finish.connect('clicked', self.mark_time)
        self.button_back.connect('clicked', self.back)
        self.button_forward.connect('clicked', self.forward)

        # Calendar
        self.calendar.connect("day_selected", self.select_day)
        self.calendar.connect("prev_month", self.change_range)
        self.calendar.connect("next_month", self.change_range)
        self.calendar.connect("prev_year", self.change_range)
        self.calendar.connect("next_year", self.change_range)

        self.timeline.connect("change_value", self.get_curr_time)

        self.connect('key_press_event', on_key_press_event)
    ################################################################
    # Initialise 
        self.time_marker_layer()
        self.mark_day()

    def lat_lon_display(self, osm, text):
        self.status_bar.set_text('Map Centre: latitude %s longitude %s'
            %(self.osm.props.latitude, self.osm.props.longitude))


    def on_key_press_event(widget, event):
        keyname = Gtk.gdk.keyval_name(event.keyval)
        print "Key %s (%d) was pressed" % (keyname, event.keyval)


    ##################################################################
    # Calendar
    def mark_day(self):       
        curr_time = self.calendar_date_to_string()
        curr_month = int(curr_time[3:5])
        curr_year = int(curr_time[6:8])
        self.calendar.clear_marks()
        for log_file in os.listdir('logs'):
            if not log_file.startswith('.'): #filter unix hidden files
                day = int(log_file[6:8])
                month = int(log_file[4:6])
                year = int(log_file[2:4]) 
                if month == curr_month and year == curr_year:
                    #print day, month, year 
                    self.calendar.mark_day(day)


    def change_range(self, widget):
        self.mark_day()


    def select_day(self, widget):
        self.osm.track_remove_all()
        sel_date = self.calendar_date_to_string()
        self.display_date.set_text(sel_date)
        sel_date = str('20'+sel_date[6:8]+sel_date[3:5]+sel_date[0:2])        
        self.selected_date = sel_date
        self.get_data(sel_date)


    def calendar_date_to_string(self):
        year, month, day = self.calendar.get_date()
        mytime = time.mktime((year, month+1, day, 0, 0, 0, 0, 0, -1))
        curr_time = time.strftime("%x", time.localtime(mytime))
        return curr_time

    #####################################################################
    # Data

    def get_data(self, sel_date):
        self.point_list = []
        pointID = 0
        time = ''
        lat = ''
        lon = ''
        course = '' 
        data_file = ''
        data_file = './logs/' + sel_date + '.gpx'

        if os.path.isfile(data_file):
            tree = ET.parse('./logs/' + sel_date + '.gpx')  # Should there be "with open as ..."?
            root = tree.getroot()
            name_space = root.tag[:-3]
            if root[1].tag == name_space + 'wpt':   # Check if the file has been job-tagged
                track = root[2]
                trackSeg = root[2][0]
                date = root[1][1].text
                jobID = root[1][2].text
            else:
                track = root[1]
                trackSeg = root[1][0]
                date = root[0].text
            # Find local time offset:
            year = int(date[0:4])
            month = int(date[5:7])
            day = int(date[8:10])
            hour = int(date[11:13])
            mins = int(date[14:16])
            secs = int(date[17:19])
            wet = pytz.timezone('WET')
            date_time = datetime(year, month, day, hour, mins, secs)
            timezone_offset = wet.utcoffset(date_time)
            timezone_offset = str(timezone_offset)
            timezone_offset = timezone_offset[0]

            for trackPnt in trackSeg:       
                if trackPnt.tag == name_space + 'trkpt':
                    lat = trackPnt.attrib['lat']
                    lat = Decimal(lat)
                    lat = round(lat, 4)
                    lon = trackPnt.attrib['lon']
                    lon = Decimal(lon)
                    lon = round(lon, 4)

                for item in trackPnt.iter():    # i.e. iterate through children of trackPnts
                    if item.tag == name_space + 'time':
                        time = item.text
                        time = time[11:16]  # We only want hours and minutes.
                        time_TC = TimeConverter(time)    #convert to mins
                        time = (time_TC.get_time_mins()) + int(timezone_offset)
                    if item.tag == name_space + 'course':
                        course = item.text  

                a_point = TrackPoint(pointID, time, lat, lon, course)
                self.point_list.append(a_point)
                pointID += 1

            self.draw_points(self.point_list)
            self.get_locations(jobID)
            self.set_timeline()


    def get_locations(self, jobID):
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
                        places[place] = coords  # make a dictionary of coord tuples
                        a_location = Location(jobID, name, places)
            self.display_job.set_text(name)

    ################################################################
    # Timeline

    def set_timeline(self):
        """ Sets timeline range. """
        start = self.point_list[0].time
        end = self.point_list[-1].time
        time = end - start
        self.timeline.set_range(0, time)


    def get_curr_time(self, widget, x, y): 
        """ Displays timeline slider setting and send list of point 
        times to bisect. """       
        time_list = []
        start = self.point_list[0].time
        time = int(widget.get_value()) + start
        for point in self.point_list:
            point_time = point.time
            point_time -= start
            time_list.append(point_time)
        display_TC = TimeConverter(time) 
        display = display_TC.get_time_hrs_mins()
        display = str(display[0]) + ':' + str(display[1])
        font = Pango.FontDescription('sans 24')
        self.display_time.modify_font(font)
        self.display_time.set_text(display)
        self.bisect(time_list, start)


    def bisect(self, time_list, start):
        """ Compares the timeline slider setting with
        point_list to find the nearest point times before
        and after """
        sel_time = self.timeline.get_value()
        pos = bisect_left(time_list, sel_time)       
        if pos == 0:
            return time_list[0]
        if pos == len(time_list):
            return time_list[-1]
        before = time_list[pos - 1]
        after = time_list[pos]
        self.get_coords(before, after, start)


    def get_coords(self, before, after, start):
        """ Gets coordinates for before/after pair """
        for point in self.point_list:
            if point.time - start == before:
                bef_lat = point.lat
                bef_lon = point.lon
                bef_time = point.time
            if point.time - start == after:
                aft_lat = point.lat
                aft_lon = point.lon
                aft_time = point.time  
        sel_time = self.timeline.get_value()
        leg_len = after - before
        leg_time = sel_time - before
        leg_ratio = leg_time / leg_len
        self.find_posn(bef_lat, bef_lon, aft_lat, aft_lon, leg_ratio)


    def find_posn(self, bef_lat, bef_lon, aft_lat, aft_lon, leg_ratio): 
        distance = geopy.distance.VincentyDistance((bef_lat, bef_lon), 
            (aft_lat, aft_lon)).miles
        distance *= leg_ratio
        bearing = self.bearing(bef_lat, bef_lon, aft_lat, aft_lon)        
        d = geopy.distance.VincentyDistance(miles = distance)
        dest = d.destination(point=(bef_lat, bef_lon), bearing=bearing)
        self.draw_time_marker(dest.latitude, dest.longitude)


    def bearing(self, latitude_1, longitude_1, latitude_2, longitude_2):
        """
       Calculation of direction between two geographical points
       """
        rlat1 = radians(latitude_1)
        rlat2 = radians(latitude_2)
        rlon1 = radians(longitude_1)
        rlon2 = radians(longitude_2)
        drlon = rlon2-rlon1
 
        b = atan2(sin(drlon)*cos(rlat2),cos(rlat1)*sin(rlat2)-
            sin(rlat1)*cos(rlat2)*cos(drlon))
        return (degrees(b) + 360) % 360


    ##################################################################
    # Times
    def mark_time(self, name):
        """ Gets start and finish times when the appropriate
        button is clicked and calculates total hours worked.
        Allows times to be changed and recalculates total.
        """
        if self.display_start.get_text() == '':
            start_time = 0
        else:
            start_time = self.get_displayed_time('Start')

        if self.display_finish.get_text() == '':
            finish_time = 0
        else:
            finish_time = self.get_displayed_time('Finish')

        if name.get_label() == 'Start':
            start_time = self.timeline.get_value()
            TC = TimeConverter(start_time)
            display = TC.get_time_hrs_mins()
            display = str(display[0]) + ':' + str(display[1]) 
            self.display_start.set_text(display)
            self.display_worked(start_time, finish_time)

        else:
            finish_time = self.timeline.get_value()
            TC = TimeConverter(finish_time)
            display = TC.get_time_hrs_mins()
            display = str(display[0]) + ':' + str(display[1])
            self.display_finish.set_text(display)
            self.display_worked(start_time, finish_time)


    def display_worked(self, start_time, finish_time):
        work_time = finish_time - start_time
        work_time_TC = TimeConverter(work_time)
        work_time = work_time_TC.get_time_hrs_mins()
        self.display_hours.set_text('%s Hrs %s Mins'
            %(work_time[0], work_time[1]))   


    def get_displayed_time(self, mode):
        if mode == 'Start':
            time = self.display_start.get_text()
        else:
            time = self.display_finish.get_text()
        TC = TimeConverter(time)
        time = TC.get_time_mins()
        return time

    #################################################################


    def back(self):
        pass


    def forward(self):
        pass


    #################################################################
    # Add Layers
    def circle_layer(self):
        self.circ_layer = CircleLayer()
        self.osm.layer_add(self.circ_layer)

    def draw_start_rad(self, radius, lat, lon):
        self.osm.layer_remove(self.circ_layer)  # Clear existing drawing
        self.circle_layer()
        radius = radius*0.01
        self.circ_layer.add_circle(radius, lat, lon, 0.0, 0.0, 1.0, 0.8)


    def time_marker_layer(self):
        self.time_layer = CircleLayer()
        self.osm.layer_add(self.time_layer)


    def draw_time_marker(self, lat, lon):
        self.osm.layer_remove(self.time_layer)
        self.time_marker_layer()
        radius = 0.05
        self.time_layer.add_circle(radius, lat, lon, 0.0, 0.5, 0.5, 0.8)

    ####################################################################
    # Draw track    
    def draw_points(self, point_list):
        new_track = osmgpsmap.MapTrack()

        for point in point_list:
            ID = point.pointID
            lat = point.lat     
            lon = point.lon
            time = point.time
            course = point.course
            map_point = osmgpsmap.MapPoint.new_degrees(lat, lon)
            new_track.add_point(map_point)
        self.osm.track_add(new_track)
        
    """
    def draw_points(self, point_list, osm):
        self.track_layer = TrackLayer()
        self.track_layer.add_track(point_list, self.osm)

        #self.osm.layer_add(self.track_layer)
    """        


    ################################################################

        
class TimeConverter:
    def __init__(self, time):
        self.time = time        
    def get_time_mins(self):
        hour = int(self.time[0:2])
        mins = int(self.time[3:5])
        hour *= 60
        mins = hour + mins
        return mins
    def get_time_hrs_mins(self):
        hours = int(self.time / 60)
        mins = int(self.time % 60)
        hours = str(hours)
        mins = str(mins)
        hours = hours.zfill(2)  # Add leading zero to single digits
        mins = mins.zfill(2)
        return hours, mins




        
if __name__ == "__main__":
    MW = MainWindow()
    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()

    Gtk.main()

    Gdk.threads_leave()

