#!/usr/bin/env python
# coding=utf8
import sys
import os.path
import random
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from math import pi
import glib
import geopy, geopy.distance
import cairo


GObject.threads_init()
Gdk.threads_init()

from gi.repository import OsmGpsMap as osmgpsmap
print "using library: %s (version %s)" % (osmgpsmap.__file__, osmgpsmap._version)

assert osmgpsmap._version == "1.0"



class CircleLayer(GObject.GObject, osmgpsmap.MapLayer):
    def __init__(self):
        """
        Initialize thz selection layer
        """
        GObject.GObject.__init__(self)
        self.circles = []
        self.rectangles = []
        WIDTH, HEIGHT = 400, 400
        surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        ctx = cairo.Context(surface)
        self.red = 0.0
        self.green = 0.0
        self.blue = 1.0
        self.alpha = 0.8

    def add_circle(self, rds, lat, lon, r, g, b, a):
        """
        Add a circle
        """
        self.red = r
        self.green = g
        self.blue = b
        self.alpha = a
        self.circles.append((rds, lat, lon, r, g, b, a))


    def do_draw(self, gpsmap, ctx):
        """
        draw the circles - seems to work
        """
        for circle in self.circles:
            d = geopy.distance.VincentyDistance(kilometers=circle[0])
            center = geopy.point.Point(circle[1], circle[2])
            np = d.destination(center, 0)
            ep = d.destination(center, 90)
            sp = d.destination(center, 180)
            wp = d.destination(center, 270)
            osm_np = osmgpsmap.MapPoint.new_degrees(np[0], np[1])
            osm_ep = osmgpsmap.MapPoint.new_degrees(ep[0], ep[1])
            osm_sp = osmgpsmap.MapPoint.new_degrees(sp[0], sp[1])
            osm_wp = osmgpsmap.MapPoint.new_degrees(wp[0], wp[1])
            osm_cen = osmgpsmap.MapPoint.new_degrees(circle[1], circle[2])
            
            view_np = gpsmap.convert_geographic_to_screen(osm_np)
            view_ep = gpsmap.convert_geographic_to_screen(osm_ep)
            view_sp = gpsmap.convert_geographic_to_screen(osm_sp)
            view_wp = gpsmap.convert_geographic_to_screen(osm_wp)
            view_cen = gpsmap.convert_geographic_to_screen(osm_cen)

            width = view_ep[0] - view_wp[0]
            height = view_sp[1] - view_np[1]
            ctx.save()
            ctx.translate(view_cen[0], view_cen[1])
            ctx.set_line_width(3.0)
            #ctx.set_source_rgba(0.0, 0.0, 1.0, 0.8)
            ctx.set_source_rgba(self.red, self.green, self.blue, self.alpha)
            ctx.scale(1.0, (height/width))
            ctx.arc(float(0.0), float(0.0), width, 0.0, 2*pi)
            ctx.stroke()
            ctx.restore()


    def do_render(self, gpsmap):
        """
        render the layer
        """
        pass

    def do_busy(self):
        """
        set the map busy
        """
        return False

    def do_button_press(self, gpsmap, gdkeventbutton):
        """
        Someone press a button
        """
        return False

#GObject.type_register(SelectionLayer)




"""
circle_layer = CircleLayer()
osm.layer_add(circle_layer)
circle_layer.add_circle(0.1,51.12,0.27)    #

osm.set_center_and_zoom(51.16, 0.26, 14.5)
osm.layer_add(osmgpsmap.MapOsd(show_crosshair=True))

w = Gtk.Window()
w.connect("destroy", Gtk.main_quit)
w.set_default_size(400,400)
w.add(osm)
w.show_all()

Gtk.main()
"""