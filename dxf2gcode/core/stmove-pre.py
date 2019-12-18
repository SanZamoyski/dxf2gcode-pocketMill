# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2008-2015
#    Christian Kohlöffel
#    Vinzenz Schulz
#    Jean-Paul Schouwstra
#
#   This file is part of DXF2GCODE.
#
#   DXF2GCODE is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DXF2GCODE is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with DXF2GCODE.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################

from __future__ import absolute_import
from __future__ import division

from math import sin, cos, pi, sqrt
from copy import deepcopy

#for dumps
from inspect import getmembers
from pprint import pprint

import dxf2gcode.globals.globals as g

from dxf2gcode.core.linegeo import LineGeo
from dxf2gcode.core.arcgeo import ArcGeo
from dxf2gcode.core.point import Point
from dxf2gcode.core.intersect import Intersect
from dxf2gcode.core.shape import Geos
from dxf2gcode.core.shape import Shape
from dxf2gcode.core.shapeoffset import *

import logging
logger = logging.getLogger('core.stmove')


class StMove(object):
    """
    This Function generates the StartMove for each shape. It
    also performs the Plotting and Export of this moves. It is linked
    to the shape of its parent
    """
    # only need default arguments here because of the change of usage with super in QGraphicsLineItem
    def __init__(self, shape=None):
        if shape is None:
            return

        self.shape = shape

        self.start, self.angle = self.shape.get_start_end_points(True, True)
        self.end = self.start

        self.make_start_moves()

    def append(self, geo):
        # we don't want to additional scale / rotate the stmove geo
        # so no geo.make_abs_geo(self.shape.parentEntity)
        geo.make_abs_geo()
        self.geos.append(geo)

    def make_start_moves(self):
        """
        This function called to create the start move. It will
        be generated based on the given values for start and angle.
        """
        self.geos = Geos([])

        if g.config.machine_type == 'drag_knife':
            self.make_swivelknife_move()
            return

        # Get the start rad. and the length of the line segment at begin.
        start_rad = self.shape.parentLayer.start_radius

        # Get tool radius based on tool diameter.
        tool_rad = self.shape.parentLayer.getToolRadius()

        # Calculate the starting point with and without compensation.
        start = self.start
        angle = self.angle

        #set the proper direction for the tool path
        if self.shape.cw ==True:
            direction = -1;
        else:
            direction = 1;

        # Pocket Milling - draw toolpath
        if self.shape.Pocket == True:
            
            #TODO if two half-arcs and starts and ends in same place, use:
            
            #for circular pocket
            if False:
                numberofrotations = int((self.shape.geos[0].r - tool_rad)/self.shape.OffsetXY)-1
                if ((self.shape.geos[0].r - tool_rad)/self.shape.OffsetXY)> numberofrotations :
                    numberofrotations += 1
                logger.debug("stmove:make_start_moves:Tool Radius: %f" % (tool_rad))
                logger.debug("stmove:make_start_moves:StepOver XY: %f" % (self.shape.OffsetXY))
                logger.debug("stmove:make_start_moves:Shape Radius: %f" % (self.shape.geos[0].r))
                logger.debug("stmove:make_start_moves:Shape Origin at: %f,%f" % (self.shape.geos[0].O.x, self.shape.geos[0].O.y))
                logger.debug("stmove:make_start_moves:Number of Arcs: %f" % (numberofrotations+1))
                for i in range(0, numberofrotations + 1):
                    st_point = Point(self.shape.geos[0].O.x,self.shape.geos[0].O.y)
                    Ps_point = Point(self.shape.geos[0].O.x +(tool_rad + (i*self.shape.OffsetXY)) ,self.shape.geos[0].O.y)
                    Pe_point = Ps_point
                    if ((Ps_point.x - self.shape.geos[0].O.x + tool_rad) < self.shape.geos[0].r):
                        self.append(ArcGeo(Ps=Ps_point, Pe=Pe_point, O=st_point, r=(tool_rad + (i*self.shape.OffsetXY)), direction=direction))
                    else:
                        Ps_point = Point(self.shape.geos[0].O.x + self.shape.geos[0].r - tool_rad  ,self.shape.geos[0].O.y)
                        Pe_point = Ps_point
                        self.append(ArcGeo(Ps=Ps_point, Pe=Pe_point, O=st_point, r=(Ps_point.x - self.shape.geos[0].O.x), direction=direction))
                    
                    print("B stmove:make_start_moves:Toolpath Arc at: %f,%f" % (Ps_point.x,Ps_point.x))  
                    logger.debug("stmove:make_start_moves:Toolpath Arc at: %f,%f" % (Ps_point.x,Ps_point.x))   
                    
                    if i<numberofrotations:
                        st_point = Point(Ps_point.x,Ps_point.y)
                        if ((Ps_point.x + self.shape.OffsetXY - self.shape.geos[0].O.x + tool_rad) < self.shape.geos[0].r):
                            en_point = Point(Ps_point.x + self.shape.OffsetXY,Ps_point.y)
                        else:
                            en_point = Point(self.shape.geos[0].O.x + self.shape.geos[0].r - tool_rad,Ps_point.y)
                            
                        self.append(LineGeo(st_point,en_point))
                        
            #TODO: if 4 lines, and they are parallel
            #for rectangular pocket
            if False:
                print('D Rectangular pocket: ')
                
                #get Rectangle width and height
                firstgeox = abs(self.shape.geos[0].Ps.x - self.shape.geos[0].Pe.x)
                firstgeoy = abs(self.shape.geos[0].Ps.y - self.shape.geos[0].Pe.y)
                secondgeox = abs(self.shape.geos[1].Ps.x - self.shape.geos[1].Pe.x)
                secondgeoy = abs(self.shape.geos[1].Ps.y - self.shape.geos[1].Pe.y)
                if firstgeox > secondgeox:
                    Pocketx = firstgeox
                    if self.shape.geos[0].Ps.x < self.shape.geos[0].Pe.x:
                        minx = self.shape.geos[0].Ps.x
                    else:
                        minx = self.shape.geos[0].Pe.x
                else:
                    Pocketx = secondgeox
                    if self.shape.geos[1].Ps.x < self.shape.geos[1].Pe.x:
                        minx = self.shape.geos[1].Ps.x
                    else:
                        minx = self.shape.geos[1].Pe.x
                if firstgeoy > secondgeoy:
                    Pockety = firstgeoy
                    if self.shape.geos[0].Ps.y < self.shape.geos[0].Pe.y:
                        miny = self.shape.geos[0].Ps.y
                    else:
                        miny = self.shape.geos[0].Pe.y
                else:
                    Pockety = secondgeoy
                    if self.shape.geos[1].Ps.y < self.shape.geos[1].Pe.y:
                        miny = self.shape.geos[1].Ps.y
                    else:
                        miny = self.shape.geos[1].Pe.y
                Centerpt = Point(Pocketx/2 + minx, Pockety/2 +miny)
                # calc number of rotations
                if Pockety > Pocketx:
                    numberofrotations = int(((Pocketx/2) - tool_rad)/self.shape.OffsetXY)#+1
                    if (((Pocketx/2) - tool_rad)/self.shape.OffsetXY)> int(((Pocketx/2) - tool_rad)/self.shape.OffsetXY)+0.5 :
                        numberofrotations += 1
                else:
                    numberofrotations = int(((Pockety/2) - tool_rad)/self.shape.OffsetXY)#+1
                    if (((Pockety/2) - tool_rad)/self.shape.OffsetXY)> int(((Pockety/2) - tool_rad)/self.shape.OffsetXY)+0.5 :
                        numberofrotations += 1
                logger.debug("stmove:make_start_moves:Shape Center at: %f,%f" % (Centerpt.x, Centerpt.y))  
                print("E stmove:make_start_moves:Shape Center at: %f,%f" % (Centerpt.x, Centerpt.y))        
                for i in range(0, numberofrotations):
                    # for CCW Climb milling
                    if Pockety > Pocketx: 
                        if (Centerpt.y - (Pockety-Pocketx)/2 - (tool_rad + (i*self.shape.OffsetXY)) - tool_rad >= miny):
                            Ps_point1 = Point(Centerpt.x +(tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y + ((Pockety-Pocketx)/2 +(tool_rad + (i*self.shape.OffsetXY))) )
                            Pe_point1 = Point(Centerpt.x -(tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y + ((Pockety-Pocketx)/2 +(tool_rad + (i*self.shape.OffsetXY))) )
                            Ps_point2 = Pe_point1
                            Pe_point2 = Point(Centerpt.x -(tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y - ((Pockety-Pocketx)/2 +(tool_rad + (i*self.shape.OffsetXY))) )
                            Ps_point3 = Pe_point2
                            Pe_point3 = Point(Centerpt.x +(tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y - ((Pockety-Pocketx)/2 +(tool_rad + (i*self.shape.OffsetXY))) )
                            Ps_point4 = Pe_point3
                            Pe_point4 = Ps_point1
                        else:
                            Ps_point1 = Point(Centerpt.x + Pocketx/2 - tool_rad ,Centerpt.y + Pockety/2 - tool_rad )
                            Pe_point1 = Point(Centerpt.x - Pocketx/2 + tool_rad ,Centerpt.y + Pockety/2 - tool_rad )
                            Ps_point2 = Pe_point1
                            Pe_point2 = Point(Centerpt.x - Pocketx/2 + tool_rad ,Centerpt.y - Pockety/2 + tool_rad )
                            Ps_point3 = Pe_point2
                            Pe_point3 = Point(Centerpt.x + Pocketx/2 - tool_rad ,Centerpt.y - Pockety/2 + tool_rad )
                            Ps_point4 = Pe_point3
                            Pe_point4 = Ps_point1
                        logger.debug("stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                        print("F stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                        if direction == 1: # this is CCW
                            self.append(LineGeo(Ps_point1,Pe_point1))
                            self.append(LineGeo(Ps_point2,Pe_point2))
                            self.append(LineGeo(Ps_point3,Pe_point3))
                            self.append(LineGeo(Ps_point4,Pe_point4))
                            print('X Lines added [CCW]: ')
                            print('Point ' + Ps_point1 + 'x' + Pe_point1)
                            print('Point ' + Ps_point2 + 'x' + Pe_point2)
                            print('Point ' + Ps_point3 + 'x' + Pe_point3)
                            print('Point ' + Ps_point4 + 'x' + Pe_point4)
                            
                        else: # this is CW
                            self.append(LineGeo(Pe_point4,Ps_point4))
                            self.append(LineGeo(Pe_point3,Ps_point3))
                            self.append(LineGeo(Pe_point2,Ps_point2))
                            self.append(LineGeo(Pe_point1,Ps_point1))
                            print('Y Lines added [CW]: ')
                            print("Line from: %fx%f to %fx%f" % (Ps_point1.x, Ps_point1.y, Pe_point1.x, Pe_point1.y))
                            print("Line from: %fx%f to %fx%f" % (Ps_point2.x, Ps_point2.y, Pe_point2.x, Pe_point2.y))
                            print("Line from: %fx%f to %fx%f" % (Ps_point3.x, Ps_point3.y, Pe_point3.x, Pe_point3.y))
                            print("Line from: %fx%f to %fx%f" % (Ps_point4.x, Ps_point4.y, Pe_point4.x, Pe_point4.y))
                            
                        if i<numberofrotations-1:
                            if direction == 1: # this is CCW
                                st_point = Point(Ps_point1.x,Ps_point1.y)
                            else: # this is CW
                                st_point = Point(Pe_point4.x,Pe_point4.y)
                            if (Centerpt.y - (Pockety-Pocketx)/2 - (tool_rad + ((i+1)*self.shape.OffsetXY)) - tool_rad >= miny):
                                en_point = Point(Ps_point1.x + self.shape.OffsetXY,Ps_point1.y + self.shape.OffsetXY)
                            else:
                                en_point = Point(Centerpt.x + Pocketx/2 - tool_rad,Centerpt.y + Pockety/2 - tool_rad)
                                 
                            self.append(LineGeo(st_point,en_point))
                    elif Pocketx > Pockety:
                        if (Centerpt.x - (Pocketx-Pockety)/2 - (tool_rad + (i*self.shape.OffsetXY)) - tool_rad >= minx):
                            Ps_point1 = Point(Centerpt.x + ((Pocketx-Pockety)/2 +(tool_rad + (i*self.shape.OffsetXY))) ,Centerpt.y + (tool_rad + (i*self.shape.OffsetXY)) )
                            Pe_point1 = Point(Centerpt.x - ((Pocketx-Pockety)/2 +(tool_rad + (i*self.shape.OffsetXY))) ,Centerpt.y + (tool_rad + (i*self.shape.OffsetXY)) )
                            Ps_point2 = Pe_point1
                            Pe_point2 = Point(Centerpt.x - ((Pocketx-Pockety)/2 +(tool_rad + (i*self.shape.OffsetXY))) ,Centerpt.y - (tool_rad + (i*self.shape.OffsetXY)) )
                            Ps_point3 = Pe_point2
                            Pe_point3 = Point(Centerpt.x + ((Pocketx-Pockety)/2 +(tool_rad + (i*self.shape.OffsetXY))) ,Centerpt.y - (tool_rad + (i*self.shape.OffsetXY)) )
                            Ps_point4 = Pe_point3
                            Pe_point4 = Ps_point1
                        else:
                            Ps_point1 = Point(Centerpt.x + Pocketx/2 - tool_rad ,Centerpt.y + Pockety/2 - tool_rad )
                            Pe_point1 = Point(Centerpt.x - Pocketx/2 + tool_rad ,Centerpt.y + Pockety/2 - tool_rad )
                            Ps_point2 = Pe_point1
                            Pe_point2 = Point(Centerpt.x - Pocketx/2 + tool_rad ,Centerpt.y - Pockety/2 + tool_rad )
                            Ps_point3 = Pe_point2
                            Pe_point3 = Point(Centerpt.x + Pocketx/2 - tool_rad ,Centerpt.y - Pockety/2 + tool_rad )
                            Ps_point4 = Pe_point3
                            Pe_point4 = Ps_point1
                        logger.debug("stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                        print("G stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                        if direction == 1: # this is CCW
                            self.append(LineGeo(Ps_point1,Pe_point1))
                            self.append(LineGeo(Ps_point2,Pe_point2))
                            self.append(LineGeo(Ps_point3,Pe_point3))
                            self.append(LineGeo(Ps_point4,Pe_point4))
                            print('Z Lines added [CCW]: ')
                            print('Point ' + Ps_point1 + 'x' + Pe_point1)
                            print('Point ' + Ps_point2 + 'x' + Pe_point2)
                            print('Point ' + Ps_point3 + 'x' + Pe_point3)
                            print('Point ' + Ps_point4 + 'x' + Pe_point4)
                            
                        else: # this is CW
                            self.append(LineGeo(Pe_point4,Ps_point4))
                            self.append(LineGeo(Pe_point3,Ps_point3))
                            self.append(LineGeo(Pe_point2,Ps_point2))
                            self.append(LineGeo(Pe_point1,Ps_point1))
                            print('Q Lines added [CW]: ')
                            print('Point ' + Ps_point1 + 'x' + Pe_point1)
                            print('Point ' + Ps_point2 + 'x' + Pe_point2)
                            print('Point ' + Ps_point3 + 'x' + Pe_point3)
                            print('Point ' + Ps_point4 + 'x' + Pe_point4)
                            
                        if i<numberofrotations-1:
                            if direction == 1: # this is CCW
                                st_point = Point(Ps_point1.x,Ps_point1.y)
                            else: # this is CW
                                st_point = Point(Pe_point4.x,Pe_point4.y)
                            if (Centerpt.x - (Pocketx-Pockety)/2 - (tool_rad + ((i+1)*self.shape.OffsetXY)) - tool_rad >= minx):
                                en_point = Point(Ps_point1.x + self.shape.OffsetXY,Ps_point1.y + self.shape.OffsetXY)
                            else:
                                en_point = Point(Centerpt.x + Pocketx/2 - tool_rad,Centerpt.y + Pockety/2 - tool_rad)
                                 
                            self.append(LineGeo(st_point,en_point))
                    elif Pocketx == Pockety:
                        if (Centerpt.x - (tool_rad + (i*self.shape.OffsetXY)) - tool_rad >= minx):
                            Ps_point1 = Point(Centerpt.x + (tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y + (tool_rad + (i*self.shape.OffsetXY)) )
                            Pe_point1 = Point(Centerpt.x - (tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y + (tool_rad + (i*self.shape.OffsetXY)) )
                            Ps_point2 = Pe_point1
                            Pe_point2 = Point(Centerpt.x - (tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y - (tool_rad + (i*self.shape.OffsetXY)) )
                            Ps_point3 = Pe_point2
                            Pe_point3 = Point(Centerpt.x + (tool_rad + (i*self.shape.OffsetXY)) ,Centerpt.y - (tool_rad + (i*self.shape.OffsetXY)) )
                            Ps_point4 = Pe_point3
                            Pe_point4 = Ps_point1
                        else:
                            Ps_point1 = Point(Centerpt.x + Pocketx/2 - tool_rad ,Centerpt.y + Pockety/2 - tool_rad )
                            Pe_point1 = Point(Centerpt.x - Pocketx/2 + tool_rad ,Centerpt.y + Pockety/2 - tool_rad )
                            Ps_point2 = Pe_point1
                            Pe_point2 = Point(Centerpt.x - Pocketx/2 + tool_rad ,Centerpt.y - Pockety/2 + tool_rad )
                            Ps_point3 = Pe_point2
                            Pe_point3 = Point(Centerpt.x + Pocketx/2 - tool_rad ,Centerpt.y - Pockety/2 + tool_rad )
                            Ps_point4 = Pe_point3
                            Pe_point4 = Ps_point1
                        logger.debug("stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y)) 
                        print("H stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y)) 
                        if direction == 1: # this is CCW
                            self.append(LineGeo(Ps_point1,Pe_point1))
                            self.append(LineGeo(Ps_point2,Pe_point2))
                            self.append(LineGeo(Ps_point3,Pe_point3))
                            self.append(LineGeo(Ps_point4,Pe_point4))
                            
                            print('V Lines added [CCW]: ')
                            print('Point ' + Ps_point1 + 'x' + Pe_point1)
                            print('Point ' + Ps_point2 + 'x' + Pe_point2)
                            print('Point ' + Ps_point3 + 'x' + Pe_point3)
                            print('Point ' + Ps_point4 + 'x' + Pe_point4)
                            
                        else: # this is CW
                            self.append(LineGeo(Pe_point4,Ps_point4))
                            self.append(LineGeo(Pe_point3,Ps_point3))
                            self.append(LineGeo(Pe_point2,Ps_point2))
                            self.append(LineGeo(Pe_point1,Ps_point1))
                            print('P Lines added [CW]: ')
                            print('Point ' + Ps_point1 + 'x' + Pe_point1)
                            print('Point ' + Ps_point2 + 'x' + Pe_point2)
                            print('Point ' + Ps_point3 + 'x' + Pe_point3)
                            print('Point ' + Ps_point4 + 'x' + Pe_point4)
                            
                        if i<numberofrotations-1:
                            if direction == 1: # this is CCW
                                st_point = Point(Ps_point1.x,Ps_point1.y)
                            else: # this is CW
                                st_point = Point(Pe_point4.x,Pe_point4.y)
                            if (Centerpt.x - (tool_rad + ((i+1)*self.shape.OffsetXY)) - tool_rad >= minx):
                                en_point = Point(Ps_point1.x + self.shape.OffsetXY,Ps_point1.y + self.shape.OffsetXY)
                            else:
                                en_point = Point(Centerpt.x + Pocketx/2 - tool_rad,Centerpt.y + Pockety/2 - tool_rad)
                                 
                            self.append(LineGeo(st_point,en_point))
            
            ### ARC
            """
            Standard Method to initialize the ArcGeo. Not all of the parameters are
            required to fully define a arc. e.g. Ps and Pe may be given or s_ang and
            e_ang
            @param Ps: The Start Point of the arc
            @param Pe: the End Point of the arc
            @param O: The center of the arc
            @param r: The radius of the arc
            @param s_ang: The Start Angle of the arc
            @param e_ang: the End Angle of the arc
            @param direction: The arc direction where 1 is in positive direction
            """
            
            """
            def distance_a_p(self, other):
            Find the distance between a arc and a point
            @param other: the instance of the 2nd geometry element.
            @return: The distance between the two geometries
            """
            
            """
            def PointAng_withinArc(self, Point):
            Check if the angle defined by Point is within the span of the arc.
            @param Point: The Point which angle to be checked
            @return: True or False
            """
            
            """
            def calc_bounding_box(self):
            Calculated the BoundingBox of the geometry and saves it into self.BB
            """
            
            ### LINE
            
            """
            Standard Method to initialize the LineGeo.
            @param Ps: The Start Point of the line
            @param Pe: the End Point of the line
            """
            
            """
            def distance_l_p(self, Point):
            Find the shortest distance between CCLineGeo and Point elements.
            Algorithm acc. to
            http://notejot.com/2008/09/distance-from-Point-to-line-segment-in-2d/
            http://softsurfer.com/Archive/algorithm_0106/algorithm_0106.htm
            @param Point: the Point
            @return: The shortest distance between the Point and Line
            """
            
            """
            def calc_bounding_box(self):
            Calculated the BoundingBox of the geometry and saves it into self.BB
            """
            
            ### Bounding Box
            
            """
            def joinBB(self, other):
            Joins two Bounding Box Classes and returns the new one
            @param other: The 2nd Bounding Box
            @return: Returns the joined Bounding Box Class
            """
            
            """
            def intersectArcGeometry(self, arcGeo, breakShape): from breaks.py
        
            Get the intersections between the finite line and arc.
            Algorithm based on http://vvvv.org/contribution/2d-circle-line-intersections
            """
            
            #print('BB: ' + self.shape.BB)
            print("self.BB: %s" % self.shape.BB)
            
            if self.shape.BB.Ps.x > self.shape.BB.Pe.x:
                arrayXStart = self.shape.BB.Pe.x
                arrayXEnd   = self.shape.BB.Ps.x
            else: 
                arrayXStart = self.shape.BB.Ps.x
                arrayXEnd   = self.shape.BB.Pe.x

            if self.shape.BB.Ps.y > self.shape.BB.Pe.y:
                arrayYStart = self.shape.BB.Ps.y
                arrayYEnd   = self.shape.BB.Pe.y
            else: 
                arrayYStart = self.shape.BB.Pe.y
                arrayYEnd   = self.shape.BB.Ps.y 
                
            #tool_rad
            #self.shape.OffsetXY
            
            print("BBBounds: X%s to X%s, Y%s to Y%s" % (arrayXStart, arrayXEnd, arrayYStart, arrayYEnd))
            
            #create array of points in whole BB area
            BBPointsArray = []
            
            #distances between  map of points to check
            diff = tool_rad*0.9
            
            #how close can be point to shape
            dist = tool_rad + self.shape.OffsetXY
            
            ### fill array with TRUEs
            yi = arrayYStart - diff
            
            print("array y start %s" % (yi))
            
            while yi > arrayYEnd:
                xi = arrayXStart + diff
                while xi < arrayXEnd:
                    xi += diff
                    BBPointsArray.append(True)
                yi -= diff
            ### end of filling array with TRUEs
            
            ### print BB array
            yi = arrayYStart - diff
            xi = arrayXStart + diff
                
            for x in BBPointsArray:
                #print("Point %s x %s is %s" % (xi, yi, x))
                
                if x:
                    print('T', end = ' ')
                else:
                    print(' ', end = ' ')
                    
                xi += diff
                if arrayXEnd <= xi:
                    xi = arrayXStart + diff
                    yi -= diff
                    print();
                if arrayYEnd >= yi:
                    print("End of reading array")

            ### end of printing array
            
            ### check if point is not to close to shape
            
            yi = arrayYStart - diff
            xi = arrayXStart + diff
                
                
            #>>> for i, element in enumerate(x):
            #       if element[1] == 2:
            #       x[i] = [5,5]
            
            #>>> for i, element in enumerate(array):
            #       if element[1] == 2:
            #       array[i] = [5,5]    
            
            BBArrayIndex = 0
            for BBPoint in BBPointsArray:
                #print("Point %s x %s is %s" % (xi, yi, x))
                
                if BBPoint == True:
                    
                    for geo in self.shape.geos.abs_iter():
                        if isinstance(geo, LineGeo):
                            """
                            def distance_l_p(self, Point):
                            Find the shortest distance between CCLineGeo and Point elements.
                            Algorithm acc. to
                            http://notejot.com/2008/09/distance-from-Point-to-line-segment-in-2d/
                            http://softsurfer.com/Archive/algorithm_0106/algorithm_0106.htm
                            @param Point: the Point
                            @return: The shortest distance between the Point and Line
                            """
                            if geo.distance_l_p(Point(xi, yi)) < dist:
                                BBPointsArray[BBArrayIndex] = False
                                BBPoint = False
                                break
                        elif isinstance(geo, ArcGeo):
                            """
                            def distance_a_p(self, other):
                            Find the distance between a arc and a point
                            @param other: the instance of the 2nd geometry element.
                            @return: The distance between the two geometries
                            """
                            if geo.distance_a_p(Point(xi, yi)) < dist:
                                BBPointsArray[BBArrayIndex] = False
                                BBPoint = False
                                break
                    
                
                if BBPoint:
                    print('T', end = ' ')
                else:
                    print(' ', end = ' ')
                    
                xi += diff
                if arrayXEnd <= xi:
                    xi = arrayXStart + diff
                    yi -= diff
                    print();
                if arrayYEnd >= yi:
                    print("End of reading array")
                    
                BBArrayIndex += 1
                    
            ### end of too-close-to-shape
            
            
            
            
            
            ### check if point is inside shape
            
            
            yi = arrayYStart - diff
            xi = arrayXStart + diff
            
            #check where line crosses shape
            #lineToCheck = LineGeo(Point(arrayXStart, yi), Point(arrayXEnd, yi))
            inters = []
            
            #this while loop will prepare points that crosses the shape.
            # it will be used later to check if point lays inside shape.
            # imagine horizontal line from particular point up to the end
            # of BBox containing shape. if the line crosses shape even times
            # we are outside the shape.
            
            while yi > arrayYEnd:
                for interGeo in self.shape.geos.abs_iter():
                    if isinstance(interGeo, LineGeo):   
                        
                        if interGeo.Ps.x == interGeo.Pe.x:
                            #this is vertical line
                            #print("%s is within %s and %s?: " % (yi, interGeo.Ps.y, interGeo.Pe.y))
                            if yi > min(interGeo.Ps.y, interGeo.Pe.y) and yi < max(interGeo.Ps.y, interGeo.Pe.y):
                                #print("Good vertical line: %s x %s" % (interGeo.Pe.x, yi))
                                inters.append(Point(interGeo.Pe.x, yi))
                            #else:
                                #print("Bad vertical line: %s x %s" % (interGeo.Pe.x, yi))
                            continue
                        
                        lineA = (interGeo.Ps.y - interGeo.Pe.y)/(interGeo.Ps.x - interGeo.Pe.x)
                        lineB = interGeo.Ps.y - lineA * interGeo.Ps.x
                        
                        if lineA == 0:
                            #don't care in this case
                            #print("Horizontal!")
                            continue
                        
                        interX = (yi - lineB)/lineA
                        
                        if interX < min(interGeo.Ps.x, interGeo.Pe.x) or interX > max(interGeo.Ps.x, interGeo.Pe.x):
                            #print("%s x %s is not in line" % (interX, yi))
                            continue 
                        
                        #print("%s x %s is ok!" % (interX, yi))
                        inters.append(Point(interX, yi))
                    elif isinstance(interGeo, ArcGeo):
                        """
                        Standard Method to initialize the ArcGeo. Not all of the parameters are
                        required to fully define a arc. e.g. Ps and Pe may be given or s_ang and
                        e_ang
                        @param Ps: The Start Point of the arc
                        @param Pe: the End Point of the arc
                        @param O: The center of the arc
                        @param r: The radius of the arc
                        @param s_ang: The Start Angle of the arc
                        @param e_ang: the End Angle of the arc
                        @param direction: The arc direction where 1 is in positive direction
                        """
                        
                        #if (interGeo.O.y + interGeo.r < yi or interGeo.O.y - interGeo.r > yi):
                        #    #not even intersect whole circle
                        #    continue
                        
                        #arcStart = Point(interGeo.Ps.x - interGeo.O.x, interGeo.Ps.y - interGeo.O.y)
                        #arcEnd = Point(interGeo.Pe.x - interGeo.O.x, interGeo.Pe.y - interGeo.O.y)
                        
                        #https://math.stackexchange.com/questions/376090/calculate-pointsx-y-within-an-arc
                        #x = r * cos A => acos(x/r) = A
                        #y = r * sin A => asin(y/r) = A
                        
                        #x = r*cos(asin(y/r))
                        
                        #based on intersect.py:line_arc_intersect
                        baX = arrayXEnd - arrayXStart
                        baY = 0
                        caX = interGeo.O.x - arrayXStart
                        caY = interGeo.O.y - yi

                        a = baX * baX + baY * baY
                        bBy2 = baX * caX + baY * caY
                        c = caX * caX + caY * caY - interGeo.r * interGeo.r

                        if a == 0:
                            continue

                        pBy2 = bBy2 / a
                        q = c / a

                        disc = pBy2 * pBy2 - q
                        if disc > 0:
                            tmpSqrt = sqrt(disc)
                            abScalingFactor1 = -pBy2 + tmpSqrt
                            abScalingFactor2 = -pBy2 - tmpSqrt

                            p1 = Point(arrayXStart - baX * abScalingFactor1,
                                    yi - baY * abScalingFactor1)
                            p2 = Point(arrayXStart - baX * abScalingFactor2,
                                    yi - baY * abScalingFactor2)
                            
                            #def point_belongs_to_line(point, line):
                            #    linex = sorted([line.Ps.x, line.Pe.x])
                            #    liney = sorted([line.Ps.y, line.Pe.y])
                            #    return (linex[0] - 1e-8 <= point.x <= linex[1] + 1e-8 and
                            #            liney[0] - 1e-8 <= point.y <= liney[1] + 1e-8)
                            
                            #def point_belongs_to_arc(point, arc):
                            #    ang = arc.dif_ang(arc.Ps, point, arc.ext)
                            #    return (arc.ext + 1e-8 >= ang >= -1e-8 if arc.ext > 0 else
                            #            arc.ext - 1e-8 <= ang <= 1e-8)
                            
                            #if Intersect.point_belongs_to_arc(p1, arc) and Intersect.point_belongs_to_line(p1, #line):
                            #    intersections.append(p1)
                            
                            linex = sorted([arrayXStart, arrayXEnd])
                            liney = sorted([yi, yi])
                            
                            ang = interGeo.dif_ang(interGeo.Ps, p1, interGeo.ext)
                            
                            if interGeo.ext > 0:
                                arcOut = interGeo.ext + 1e-8 >= ang >= -1e-8
                            else:
                                arcOut = interGeo.ext - 1e-8 <= ang <= 1e-8
                            
                            if  linex[0] - 1e-8 <= p1.x and p1.x <= linex[1] + 1e-8 and liney[0] - 1e-8 <= p1.y and p1.y <= liney[1] + 1e-8 and arcOut:
                                    #print("Good point! %s" % (p1))
                                    inters.append(p1)
        
                            ang = interGeo.dif_ang(interGeo.Ps, p2, interGeo.ext)
                            
                            if interGeo.ext > 0:
                                arcOut = interGeo.ext + 1e-8 >= ang >= -1e-8
                            else:
                                arcOut = interGeo.ext - 1e-8 <= ang <= 1e-8
                            
                            if  linex[0] - 1e-8 <= p2.x <= linex[1] + 1e-8 and liney[0] - 1e-8 <= p2.y <= liney[1] + 1e-8 and arcOut:
                                    #print("Good point! %s" % (p2))
                                    inters.append(p2)
                                    
                            
                            #if Intersect.point_belongs_to_arc(p2, arc) and Intersect.point_belongs_to_line(p2, #line):
                            #    intersections.append(p2)
                            
                        #continue
                        #end of original arc_intersection
                        
                        #print ("Start: %s, End: %s, Radius: %s" % (arcStart, arcEnd, interGeo.r))
                    
            for i in inters:
                print("%s x %s" % (i.x, i.y))
                
            yi = arrayYStart - diff
            xi = arrayXStart + diff
            
            BBArrayIndex = 0
            for BBPoint in BBPointsArray:
                #print("Point %s x %s is %s" % (xi, yi, x))
                
                count = 0
                
                if BBPoint == True:
                    for pinter in inters:
                        if pinter.y == yi and pinter.x > xi:
                            count += 1
                
                if count%2 == 0:
                    BBPointsArray[BBArrayIndex] = False
                    
                xi += diff
                if arrayXEnd <= xi:
                    xi = arrayXStart + diff
                    yi -= diff
                    
                BBArrayIndex += 1
            
            
            
            yi = arrayYStart - diff
            xi = arrayXStart + diff
                        
            for x in BBPointsArray:
                #print("Point %s x %s is %s" % (xi, yi, x))
                
                #if x == True:
                #    #do stuff here
                    
                if x:
                    print('T', end = ' ')
                else:
                    print(' ', end = ' ')
                    
                xi += diff
                if arrayXEnd <= xi:
                    xi = arrayXStart + diff
                    yi -= diff
                    print();
                if arrayYEnd >= yi:
                    print("End of reading array")
                    
            ### end of not-inside
            
            ### ### ###
            ### Cool! We have now complete array of pionts to mill
            ### but we need to convert it into LINES now...
                    
            BBArrayIndex = 0
            for BBPoint in BBPointsArray:
                
                if BBPoint == True:
                    startPoint = Point(xi, yi)
                    
                xi += diff
                if arrayXEnd <= xi:
                    xi = arrayXStart + diff
                    yi -= diff
                    
                BBArrayIndex += 1        

            #for gg in self.shape.geos.abs_iter():
            #    if isinstance(gg, LineGeo):
            #        print('Line: ')
            #    elif isinstance(gg, ArcGeo):
            #        print(' Arc: ')
            #        #gg.calc_bounding_box()
            #        #print('Bounding box: ' + gg.BB)
            #    #if (isinstance(self.selectedItems[0].geos[0], ArcGeo)
            #    print(gg)
            
            #dummy last line
            self.append(LineGeo(Point(10.1, 11.3), Point(20.1, 21.3)))
                      
        ### drill cutted from here
            
        if self.shape.cut_cor == 40:
            if self.shape.Pocket == False:
                self.append(RapidPos(start))
            
        elif self.shape.cut_cor != 40 and not g.config.vars.Cutter_Compensation["done_by_machine"]:

            toolwidth = self.shape.parentLayer.getToolRadius()
            offtype = "in"  if self.shape.cut_cor == 42 else "out"
            offshape = offShapeClass(parent = self.shape, offset = toolwidth, offtype = offtype)

            if len(offshape.rawoff) > 0:
                start, angle = offshape.rawoff[0].get_start_end_points(True, True)

                self.append(RapidPos(start))
                self.geos += offshape.rawoff

        # Cutting Compensation Left
        elif self.shape.cut_cor == 41:
            # Center of the Starting Radius.
            Oein = start.get_arc_point(angle + pi/2, start_rad + tool_rad)
            # Start Point of the Radius
            Ps_ein = Oein.get_arc_point(angle + pi, start_rad + tool_rad)
            # Start Point of the straight line segment at begin.
            Pg_ein = Ps_ein.get_arc_point(angle + pi/2, start_rad)

            # Get the dive point for the starting contour and append it.
            start_ein = Pg_ein.get_arc_point(angle, tool_rad)
            self.append(RapidPos(start_ein))

            # generate the Start Line and append it including the compensation.
            start_line = LineGeo(start_ein, Ps_ein)
            self.append(start_line)

            # generate the start rad. and append it.
            start_rad = ArcGeo(Ps=Ps_ein, Pe=start, O=Oein,
                               r=start_rad + tool_rad, direction=1)
            self.append(start_rad)

        # Cutting Compensation Right
        elif self.shape.cut_cor == 42:
            # Center of the Starting Radius.
            Oein = start.get_arc_point(angle - pi/2, start_rad + tool_rad)
            # Start Point of the Radius
            Ps_ein = Oein.get_arc_point(angle + pi, start_rad + tool_rad)
            # Start Point of the straight line segment at begin.
            Pg_ein = Ps_ein.get_arc_point(angle - pi/2, start_rad)

            # Get the dive point for the starting contour and append it.
            start_ein = Pg_ein.get_arc_point(angle, tool_rad)
            self.append(RapidPos(start_ein))

            # generate the Start Line and append it including the compensation.
            start_line = LineGeo(start_ein, Ps_ein)
            self.append(start_line)

            # generate the start rad. and append it.
            start_rad = ArcGeo(Ps=Ps_ein, Pe=start, O=Oein,
                               r=start_rad + tool_rad, direction=0)
            self.append(start_rad)

    def make_swivelknife_move(self):
        """
        Set these variables for your tool and material
        @param offset: knife tip distance from tool centerline. The radius of the
        tool is used for this.
        """
        offset = self.shape.parentLayer.getToolRadius()
        drag_angle = self.shape.drag_angle

        startnorm = offset*Point(1, 0)  # TODO make knife direction a config setting
        prvend, prvnorm = Point(), Point()
        first = True

        for geo in self.shape.geos.abs_iter():
            if isinstance(geo, LineGeo):
                geo_b = deepcopy(geo)
                if first:
                    first = False
                    prvend = geo_b.Ps + startnorm
                    prvnorm = startnorm
                norm = offset * (geo_b.Pe - geo_b.Ps).unit_vector()
                geo_b.Ps += norm
                geo_b.Pe += norm
                if not prvnorm == norm:
                    direction = prvnorm.to3D().cross_product(norm.to3D()).z
                    swivel = ArcGeo(Ps=prvend, Pe=geo_b.Ps, r=offset, direction=direction)
                    swivel.drag = drag_angle < abs(swivel.ext)
                    self.append(swivel)
                self.append(geo_b)

                prvend = geo_b.Pe
                prvnorm = norm
            elif isinstance(geo, ArcGeo):
                geo_b = deepcopy(geo)
                if first:
                    first = False
                    prvend = geo_b.Ps + startnorm
                    prvnorm = startnorm
                if geo_b.ext > 0.0:
                    norma = offset*Point(cos(geo_b.s_ang+pi/2), sin(geo_b.s_ang+pi/2))
                    norme = Point(cos(geo_b.e_ang+pi/2), sin(geo_b.e_ang+pi/2))
                else:
                    norma = offset*Point(cos(geo_b.s_ang-pi/2), sin(geo_b.s_ang-pi/2))
                    norme = Point(cos(geo_b.e_ang-pi/2), sin(geo_b.e_ang-pi/2))
                geo_b.Ps += norma
                if norme.x > 0:
                    geo_b.Pe = Point(geo_b.Pe.x+offset/(sqrt(1+(norme.y/norme.x)**2)),
                                     geo_b.Pe.y+(offset*norme.y/norme.x)/(sqrt(1+(norme.y/norme.x)**2)))
                elif norme.x == 0:
                    geo_b.Pe = Point(geo_b.Pe.x,
                                     geo_b.Pe.y)
                else:
                    geo_b.Pe = Point(geo_b.Pe.x-offset/(sqrt(1+(norme.y/norme.x)**2)),
                                     geo_b.Pe.y-(offset*norme.y/norme.x)/(sqrt(1+(norme.y/norme.x)**2)))
                if prvnorm != norma:
                    direction = prvnorm.to3D().cross_product(norma.to3D()).z
                    swivel = ArcGeo(Ps=prvend, Pe=geo_b.Ps, r=offset, direction=direction)
                    swivel.drag = drag_angle < abs(swivel.ext)
                    self.append(swivel)
                prvend = geo_b.Pe
                prvnorm = offset*norme
                if -pi < geo_b.ext < pi:
                    self.append(ArcGeo(Ps=geo_b.Ps, Pe=geo_b.Pe, r=sqrt(geo_b.r**2+offset**2), direction=geo_b.ext))
                else:
                    geo_b = ArcGeo(Ps=geo_b.Ps, Pe=geo_b.Pe, r=sqrt(geo_b.r**2+offset**2), direction=-geo_b.ext)
                    geo_b.ext = -geo_b.ext
                    self.append(geo_b)
            # TODO support different geos, or disable them in the GUI
            # else:
            #     self.append(copy(geo))
        if not prvnorm == startnorm:
            direction = prvnorm.to3D().cross_product(startnorm.to3D()).z
            self.append(ArcGeo(Ps=prvend, Pe=prvend-prvnorm+startnorm, r=offset, direction=direction))

        self.geos.insert(0, RapidPos(self.geos.abs_el(0).Ps))
        self.geos[0].make_abs_geo()


    def make_path(self, drawHorLine, drawVerLine):
        for geo in self.geos.abs_iter():
            drawVerLine(self.shape, geo.get_start_end_points(True))
            geo.make_path(self.shape, drawHorLine)
        if len(self.geos):
            drawVerLine(self.shape, geo.get_start_end_points(False))


class RapidPos(Point):
    def __init__(self, point):
        Point.__init__(self, point.x, point.y)
        self.abs_geo = None

    def get_start_end_points(self, start_point, angles=None):
        if angles is None:
            return self
        elif angles:
            return self, 0
        else:
            return self, Point(0, -1) if start_point else Point(0, -1)

    def make_abs_geo(self, parent=None):
        """
        Generates the absolute geometry based on itself and the parent. This
        is done for rotating and scaling purposes
        """
        self.abs_geo = RapidPos(self.rot_sca_abs(parent=parent))

    def make_path(self, caller, drawHorLine):
        pass

    def Write_GCode(self, PostPro):
        """
        Writes the GCODE for a rapid position.
        @param PostPro: The PostProcessor instance to be used
        @return: Returns the string to be written to a file.
        """
        return PostPro.rap_pos_xy(self)
