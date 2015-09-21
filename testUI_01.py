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
import analyseLogs
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
        self.list_store = Gtk.ListStore(str)

        # Displays
        self.status_bar = builder.get_object("entry1")
        self.log_view = builder.get_object("log_view")
        self.button_file_chooser = builder.get_object("button_file_chooser")
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, renderer, text=0)
        self.log_view.append_column(column)
        self.calendar = builder.get_object("calendar1")
        self.slider_radius = builder.get_object("slider_radius")
        self.slider_radius.set_range(1,100)


        ###############################################################
        # Connect signals
        self.osm.connect('button_release_event', self.lat_lon_display)
        self.button_file_chooser.connect('clicked', self.on_file_selected)
        # Calendar
        self.calendar.connect("day_selected", self.select_day)
        self.calendar.connect("prev_month", self.change_range)
        self.calendar.connect("next_month", self.change_range)
        self.calendar.connect("prev_year", self.change_range)
        self.calendar.connect("next_year", self.change_range)

        self.slider_radius.connect("change_value", self.search_rad)

        ################################################################
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
        sel_date = self.calendar_date_to_string()
        sel_date = str('20'+sel_date[6:8]+sel_date[3:5]+sel_date[0:2])
        self.analyse(sel_date)


    def analyse(self, sel_date):
        data = analyseLogs.get_data(sel_date)
        if data != None:
            jobID = data[0]
            point_list = data[1]
            analyseLogs.get_locations(jobID)
            search_rad = self.slider_radius.get_value()
            analyseLogs.get_times(jobID, point_list, search_rad)

    ################################################################
    def search_rad(self, widget, x, y):
        radius = widget.get_value()
        self.select_day(self.calendar)


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
    Gtk.main()



class Handler:
    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def onButtonPressed(self, button):
        print("Hello World!")