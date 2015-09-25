#!/usr/bin/env python
# coding=utf8
# Must be GtkWindow, not GtkApplicationWindow - change .glade file if nec.

import sys
import os.path
sys.path.append("./modules")
import random
from math import pi
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import glib
import time
from analyseLogs import*
from osmLayers import*
#print str(Gtk.get_major_version()) + "." + str(Gtk.get_minor_version()) + "." + str(Gtk.get_micro_version())

from gi.repository import OsmGpsMap as osmgpsmap
print "using library: %s (version %s)" % (osmgpsmap.__file__, osmgpsmap._version)

assert osmgpsmap._version == "1.0"
SHOW_TRACK = True
assert osmgpsmap._version >= "0.7.0"

#osm = osmgpsmap.Map()




class MainWindow():
    def __init__(self):

        self.osm = osmgpsmap.Map()
        builder = Gtk.Builder()
        builder.add_from_file("mainWindow.glade")
        #builder.connect_signals(Handler())
        self.osm.set_center_and_zoom(51.12, 0.27, 14)
        window = builder.get_object("window1")
        map_frame = builder.get_object("viewport1")
        map_frame.add(self.osm)
        window.show_all()       
        self.osm.layer_add(osmgpsmap.MapOsd(show_dpad=True, show_zoom=True,
            show_crosshair=True))

        self.log_list = []
        self.selected_date = ''
        self.list_store = Gtk.ListStore(str)

        

        # Instanciate classes
        self.dataAnalyser = DataAnalyser()
        

        # Displays
        self.status_bar = builder.get_object("status")
        self.log_view = builder.get_object("log_view")
        self.button_file_chooser = builder.get_object("button_file_chooser")
        self.button_add = builder.get_object('button_add')
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, renderer, text=0)
        self.log_view.append_column(column)
        self.calendar = builder.get_object("calendar1")
        self.slider_radius_start = builder.get_object("slider_radius_start")
        self.slider_radius_start.set_range(10,100)
        self.timeline = builder.get_object("timeline")
        self.timeline.set_range(0, 100)
        self.label_log = builder.get_object("label_log")
        
        self.display_date = builder.get_object("display_date")
        self.display_job = builder.get_object("display_job")
        self.display_hours = builder.get_object("display_hours")
        
        
        ###############################################################
        # Connect signals
        self.osm.connect('button_release_event', self.lat_lon_display)
        self.button_file_chooser.connect('clicked', self.on_file_selected)
        self.button_add.connect('clicked', self.add_location)
        # Calendar
        self.calendar.connect("day_selected", self.select_day)
        self.calendar.connect("prev_month", self.change_range)
        self.calendar.connect("next_month", self.change_range)
        self.calendar.connect("prev_year", self.change_range)
        self.calendar.connect("next_year", self.change_range)

        self.slider_radius_start.connect("change_value", self.get_search_rad_start)

        ################################################################
        self.time_marker_layer()
        self.circle_layer()
        self.mark_day()

    def lat_lon_display(self, osm, text):
        self.status_bar.set_text('Map Centre: latitude %s longitude %s'
            %(self.osm.props.latitude, self.osm.props.longitude))

    ##################################################################
    # Calendar

    def calendar_date_to_string(self):
        year, month, day = self.calendar.get_date()
        mytime = time.mktime((year, month+1, day, 0, 0, 0, 0, 0, -1))
        curr_time = time.strftime("%x", time.localtime(mytime))
        return curr_time


    def select_day(self, widget):
        self.osm.track_remove_all()
        sel_date = self.calendar_date_to_string()
        self.display_date.set_text(sel_date)
        # Setting label text n.b. single quotes:
        #text = "<span font='24' foreground='black'>" + sel_date  + "</span>"
        #self.label_log.set_markup(text)
        sel_date = str('20'+sel_date[6:8]+sel_date[3:5]+sel_date[0:2])        
        self.dataAnalyser.location_list = []
        self.selected_date = sel_date
        self.analyse_get_data(sel_date)


    def add_location(self):
        pass




    def analyse_get_data(self, sel_date):
        data = self.dataAnalyser.get_data(sel_date)
        self.analyse_get_times(data[0], data[1], data[2])    # Start and Stop posns

        #if data != None:
            #jobID = data[0]
            #point_list = data[1]
            #job_name = self.dataAnalyser.get_locations(jobID)
            #search_rad_start = self.slider_radius.get_value()



    def analyse_get_times(self, jobID, point_list, job_name):
        search_rad_start = self.slider_radius_start.get_value()
        timer = self.dataAnalyser.get_times(jobID, point_list, search_rad_start)
        self.draw_points(point_list)

        self.get_work_time(timer[2], timer[3])
        self.display_job.set_text(job_name)

        start_pos = timer[0]
        lat = start_pos[0]
        lon = start_pos[1]
        self.draw_start_rad(search_rad_start, lat, lon)



    def get_work_time(self, start, stop):
        time = self.dataAnalyser.time_working(start, stop)
        self.write_hours(time[0], time[1])


    def write_hours(self, hours, mins):
        self.display_hours.set_text('%s Hrs %s Mins'
            %(hours, mins))

    ################################################################


    def change_range(self, widget):
        self.mark_day()


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

        #year, month, day = self.calendar.get_date()b

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
        self.draw_time_marker()


    def draw_time_marker(self):
        #self.osm.layer_remove(self.time_marker_layer)
        #self.time_layer()
        radius = 0.05
        self.time_layer.add_circle(radius, 51.1392, 0.27, 0.0, 0.5, 0.5, 0.8)




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

    def draw_points(self, osm, point_list):
        self.track_layer = TrackLayer()
        #self.track_layer.add_track(osm, point_list)

        self.osm.layer_add(self.track_layer)
        """

    def get_search_rad_start(self, widget, x, y):
        self.osm.track_remove_all()
        self.analyse_get_data(self.selected_date)



    ################################################################



    ###################################################################
    def on_file_selected(self, button):     
        chooser = Gtk.FileChooserDialog(title = 'Select Logs',
            action = Gtk.FileChooserAction.OPEN,
            buttons = (Gtk.STOCK_OPEN,1, Gtk.STOCK_CANCEL,2))
        filter = Gtk.FileFilter()
        filter.set_name('Logs')
        filter.add_pattern('*.gpx')
        chooser.add_filter(filter)
        filter = Gtk.FileFilter()
        filter.set_name('All Files')
        filter.add_pattern('*')
        chooser.add_filter(filter)
        chooser.set_select_multiple(True)
        chooser.set_current_folder('./logs/')
        
        response = chooser.run()
        if response == 1:
            filenames = chooser.get_filenames()
            for name in filenames:
                length = len(name)
                start = length-12
                name = name[start:length]
                self.log_list.append(name)
            self.fill_log_list()
        chooser.destroy()


    def fill_log_list(self):

        self.list_store.clear()
        for item in self.log_list:
            item = [item]
            self.list_store.append(item)

        self.log_view.set_model(self.list_store)

        #renderer = Gtk.CellRendererText()
        #column = Gtk.TreeViewColumn(None, renderer, text=0)
        #self.log_view.append_column(column)
        




        
if __name__ == "__main__":
    MW = MainWindow()
    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()

    Gtk.main()

    Gdk.threads_leave()



class Handler:
    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def onButtonPressed(self, button):
        print("Hello World!")