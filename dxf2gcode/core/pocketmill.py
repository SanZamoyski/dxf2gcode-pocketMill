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
logger = logging.getLogger('core.pocketmill')

class InterPoint(object):
    def __init__(self, x=0, y=0, i=0, mill = False):
        self.x = x
        self.y = y
        self.i = i
        self.mill = mill
        self.p = Point(x, y)
        
    def __str__ (self):
        return 'X ->%6.3f  Y ->%6.3f (%s) is %s' % (self.x, self.y, self.i, self.mill)
    
    def setMill(self, mill=False):
        self.mill = mill
        ### end of not-inside
        
class BBArray(object):
    def __init__(self, bbStartPoint, bbEndPoint, diff):
        self.array = []
        self.any = False
        
        #Start point - top, right
        
        if bbStartPoint.x > bbEndPoint.x:
            self.xStart = bbEndPoint.x
            self.xEnd   = bbStartPoint.x
        else: 
            self.xStart = bbStartPoint.x
            self.xEnd   = bbEndPoint.x

        if bbStartPoint.y > bbEndPoint.y:
            self.yStart = bbStartPoint.y
            self.yEnd   = bbEndPoint.y
        else: 
            self.yStart = bbEndPoint.y
            self.yEnd   = bbStartPoint.y
            
        self.diff = diff
            
    def create(self):
        arrayIndex = 0 
        yi = self.yStart - self.diff
            
        while yi > self.yEnd:
            xi = self.xStart + self.diff
            while xi < self.xEnd:
                self.append(InterPoint(xi, yi, arrayIndex, True))
                xi += self.diff
                arrayIndex += 1
            yi -= self.diff
            
    def checkIfAny(self):
        any = False
        
        for point in self.array:
            if point.mill == True:
                any = True
                break

        return any
        
    def append(self, newPoint):
        self.array.append(newPoint)

    def findTopRight(self):
        #this will be always outside BBox of Shape
        topRight = InterPoint(self.xStart - 1, self.yEnd - 1, 0, False)
        #max y
        for point in self.array:
            if point.y > topRight.y:
                topRight = point
                
        for point in self.array:
            if point.y == topRight.y and point.x > topRight.x:
                topRight = point
        
        return topRight

    def findDownLeft(self):
        #this will be always outside BBox of Shape
        downLeft = InterPoint(self.xEnd + 1, self.yStart + 1, 0, False)
        
        #min y
        for point in self.array:
            if point.mill == True and point.y < downLeft.y:
                downLeft = point
                
        for point in self.array:
            if point.mill == True and point.y == downLeft.y and point.x < downLeft.x:
                downLeft = point
                
        return downLeft
    
    def print(self):
        yi = self.array[0].y
        for BBPoint in self.array:
                
            if BBPoint.y != yi:
                yi = BBPoint.y 
                print()
                
            if BBPoint.mill:
                print('T', end = ' ')
            else:
                print(' ', end = ' ')
                    
        print()
        
    def removeLine(self, line):
        for BBPoint in self.array:
            if BBPoint.y == line.Ps.y and line.Pe.x >= BBPoint.x and BBPoint.x >= line.Ps.x:
                BBPoint.setMill(False)
                
    def findHorizontalWithPoint(self, point, ltr = 1):
        #values outside the box
        closestFalseLeft = self.xStart - 1
        closestFalseRight = self.xEnd + 1
        
        closestTrueLeft = point.x
        closestTrueRight = point.x
        
        #go left and right and find closest Falses
        for aPoint in self.array:
            if aPoint.mill == False and aPoint.y == point.y:
                if aPoint.x < point.x and closestFalseLeft < aPoint.x:
                    closestFalseLeft = aPoint.x
                    
                if aPoint.x > point.x and closestFalseRight > aPoint.x:
                    closestFalseRight = aPoint.x
        
        print("False x'ses: %s and %s" % (closestFalseLeft, closestFalseRight))
        
        #now find closest True's to those points
        for aPoint in self.array:
            if aPoint.mill == True and aPoint.y == point.y:
                #looking for most-left (smallest x) True
                #before (bigger than) closestFalseLeft
                #smaller than point
                if aPoint.x < point.x and aPoint.x > closestFalseLeft and aPoint.x < closestTrueLeft:
                    closestTrueLeft = aPoint.x
                    
                if aPoint.x > point.x and aPoint.x < closestFalseRight and aPoint.x > closestTrueRight:
                    closestTrueRight = aPoint.x
        
        print("True x'ses: %s and %s" % (closestTrueLeft, closestTrueRight))
        
        if ltr == 1:
            return LineGeo(Point(closestTrueLeft, point.y), Point(closestTrueRight, point.y))
        else:
            return LineGeo(Point(closestTrueRight, point.y), Point(closestTrueLeft, point.y))
        
    
    def findClosestTopLeft(self, point):
        #always outside BBox
        newy = self.yStart + 1 
        newx = point.x
        
        #find closest y (not necessery True)
        fy = False
        for BBPoint in self.array:
            if BBPoint.y > point.y and BBPoint.y < newy:
                newy = BBPoint.y
                fy = True
        
        if fy == False:
            #should never happen
            print("YYY")
            return None
        
        #find in array closest x to left, but with y = newy
        # this time it has to be true
        fx = False
        for BBPoint in self.array:
            if BBPoint.mill == True and BBPoint.y == newy and BBPoint.x <= point.x:
                if newx <= BBPoint.x:
                    newx = BBPoint.x
                    fx = True
        
        #if not found?
        if fx == False:
            print("XXX")
            return None
                
        return Point(newx, newy)
            
class PocketMill(object):
    def __init__(self, stmove=None):
        self.stmove = stmove
        
        # Get tool radius based on tool diameter.
        self.tool_rad = self.stmove.shape.parentLayer.getToolRadius()
        
        self.bbarray = 0
        
        self.arrayYStart = 0
        self.arrayYEnd = 0
        self.arrayXStart = 0
        self.arrayXEnd = 0
        
        self.diff = 0
        
        self.dist = 0
        
        self.inters = []
                
    def removeNearShape(self):
        for BBPoint in self.bbarray.array:
            #check only points that are meant to be milled
            if BBPoint.mill == True:
                #check if this point is not too close to any geo in shape
                for geo in self.stmove.shape.geos.abs_iter():
                    if isinstance(geo, LineGeo):
                        if geo.distance_l_p(BBPoint.p) < self.dist:
                            BBPoint.setMill(False)
                            break
                    elif isinstance(geo, ArcGeo):
                        if geo.distance_a_p(BBPoint.p) < self.dist:
                            BBPoint.setMill(False)
                            break
                        
    def removeOutOfShape(self):
        for BBPoint in self.bbarray.array:
            count = 0
            
            if BBPoint.mill == True:
                for pinter in self.inters:
                    if pinter.y == BBPoint.y and pinter.x > BBPoint.x:
                        count += 1
            
            if count%2 == 0:
                BBPoint.setMill(False)
            
    def createInterList(self):
        yi = self.bbarray.yStart - self.diff
        #this while loop will prepare points that crosses the shape.
        # it will be used later to check if point lays inside shape.
        # imagine horizontal line from particular point up to the end
        # of BBox containing shape. if the line crosses shape even times
        # we are outside the shape.
        
        while yi > self.bbarray.yEnd:
            for interGeo in self.stmove.shape.geos.abs_iter():
                if isinstance(interGeo, LineGeo):   
                    if interGeo.Ps.x == interGeo.Pe.x:
                        #this is vertical line
                        #check if obvius intersection lays on finite line
                        if yi > min(interGeo.Ps.y, interGeo.Pe.y) and yi < max(interGeo.Ps.y, interGeo.Pe.y):
                            self.inters.append(Point(interGeo.Pe.x, yi))
                        continue
                    
                    #calculate line coords
                    lineA = (interGeo.Ps.y - interGeo.Pe.y)/(interGeo.Ps.x - interGeo.Pe.x)
                    lineB = interGeo.Ps.y - lineA * interGeo.Ps.x
                    
                    if lineA == 0:
                        #TODO: check if shape like this:
                        #  \____
                        #       \
                        # won't cause problem...
                        #
                        #print("Horizontal!")
                        continue
                    
                    #TODO: joints will propably cause problems
                    
                    interX = (yi - lineB)/lineA
                    
                    #check if intersection does belong to line
                    if interX < min(interGeo.Ps.x, interGeo.Pe.x) or interX > max(interGeo.Ps.x, interGeo.Pe.x):
                        continue 
                    
                    self.inters.append(Point(interX, yi))
                    
                elif isinstance(interGeo, ArcGeo):
                    #based on intersect.py:line_arc_intersect
                    baX = self.bbarray.xEnd - self.bbarray.xStart
                    baY = 0
                    caX = interGeo.O.x - self.bbarray.xStart
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

                        p1 = Point(self.bbarray.xStart - baX * abScalingFactor1,
                                yi - baY * abScalingFactor1)
                        p2 = Point(self.bbarray.xStart - baX * abScalingFactor2,
                                yi - baY * abScalingFactor2)
                        
                        linex = sorted([self.bbarray.xStart, self.bbarray.xEnd])
                        liney = sorted([yi, yi])
                        
                        ang = interGeo.dif_ang(interGeo.Ps, p1, interGeo.ext)
                        
                        if interGeo.ext > 0:
                            arcOut = interGeo.ext + 1e-8 >= ang >= -1e-8
                        else:
                            arcOut = interGeo.ext - 1e-8 <= ang <= 1e-8
                        
                        if  linex[0] - 1e-8 <= p1.x and p1.x <= linex[1] + 1e-8 and liney[0] - 1e-8 <= p1.y and p1.y <= liney[1] + 1e-8 and arcOut:
                                #print("Good point! %s" % (p1))
                                self.inters.append(p1)
                                
                        ang = interGeo.dif_ang(interGeo.Ps, p2, interGeo.ext)
                        
                        if interGeo.ext > 0:
                            arcOut = interGeo.ext + 1e-8 >= ang >= -1e-8
                        else:
                            arcOut = interGeo.ext - 1e-8 <= ang <= 1e-8
                        
                        if  linex[0] - 1e-8 <= p2.x <= linex[1] + 1e-8 and liney[0] - 1e-8 <= p2.y <= liney[1] + 1e-8 and arcOut:
                                #print("Good point! %s" % (p2))
                                self.inters.append(p2)
                                
            yi -= self.diff
            #print("End of finding intersections")
        
    def createLines(self):
        if False:
            print("beans shape")
            #TODO:
            #   ____
            #  (____)
        elif False:
            #TODO if two half-arcs and starts and ends in same place, use:
            #for circular pocket
            
            numberofrotations = int((self.stmove.shape.geos[0].r - self.tool_rad)/self.stmove.shape.OffsetXY)-1
            if ((self.stmove.shape.geos[0].r - self.tool_rad)/self.stmove.shape.OffsetXY)> numberofrotations :
                numberofrotations += 1
            logger.debug("stmove:make_start_moves:Tool Radius: %f" % (self.tool_rad))
            logger.debug("stmove:make_start_moves:StepOver XY: %f" % (self.stmove.shape.OffsetXY))
            logger.debug("stmove:make_start_moves:Shape Radius: %f" % (self.stmove.shape.geos[0].r))
            logger.debug("stmove:make_start_moves:Shape Origin at: %f,%f" % (self.stmove.shape.geos[0].O.x, self.stmove.shape.geos[0].O.y))
            logger.debug("stmove:make_start_moves:Number of Arcs: %f" % (numberofrotations+1))
            for i in range(0, numberofrotations + 1):
                st_point = Point(self.stmove.shape.geos[0].O.x,self.stmove.shape.geos[0].O.y)
                Ps_point = Point(self.stmove.shape.geos[0].O.x +(self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,self.stmove.shape.geos[0].O.y)
                Pe_point = Ps_point
                if ((Ps_point.x - self.stmove.shape.geos[0].O.x + self.tool_rad) < self.stmove.shape.geos[0].r):
                    self.stmove.append(ArcGeo(Ps=Ps_point, Pe=Pe_point, O=st_point, r=(self.tool_rad + (i*self.stmove.shape.OffsetXY)), direction=direction))
                else:
                    Ps_point = Point(self.stmove.shape.geos[0].O.x + self.stmove.shape.geos[0].r - self.tool_rad  ,self.stmove.shape.geos[0].O.y)
                    Pe_point = Ps_point
                    self.stmove.append(ArcGeo(Ps=Ps_point, Pe=Pe_point, O=st_point, r=(Ps_point.x - self.stmove.shape.geos[0].O.x), direction=direction))
                
                print("B stmove:make_start_moves:Toolpath Arc at: %f,%f" % (Ps_point.x,Ps_point.x))  
                logger.debug("stmove:make_start_moves:Toolpath Arc at: %f,%f" % (Ps_point.x,Ps_point.x))   
                
                if i<numberofrotations:
                    st_point = Point(Ps_point.x,Ps_point.y)
                    if ((Ps_point.x + self.stmove.shape.OffsetXY - self.stmove.shape.geos[0].O.x + self.tool_rad) < self.stmove.shape.geos[0].r):
                        en_point = Point(Ps_point.x + self.stmove.shape.OffsetXY,Ps_point.y)
                    else:
                        en_point = Point(self.stmove.shape.geos[0].O.x + self.stmove.shape.geos[0].r - self.tool_rad,Ps_point.y)
                        
                    self.stmove.append(LineGeo(st_point,en_point))
                        
        elif False:
            #TODO: if 4 lines, and they are parallel
            #for rectangular pocket
            
            print('D Rectangular pocket: ')
            
            #get Rectangle width and height
            firstgeox = abs(self.stmove.shape.geos[0].Ps.x - self.stmove.shape.geos[0].Pe.x)
            firstgeoy = abs(self.stmove.shape.geos[0].Ps.y - self.stmove.shape.geos[0].Pe.y)
            secondgeox = abs(self.stmove.shape.geos[1].Ps.x - self.stmove.shape.geos[1].Pe.x)
            secondgeoy = abs(self.stmove.shape.geos[1].Ps.y - self.stmove.shape.geos[1].Pe.y)
            if firstgeox > secondgeox:
                Pocketx = firstgeox
                if self.stmove.shape.geos[0].Ps.x < self.stmove.shape.geos[0].Pe.x:
                    minx = self.stmove.shape.geos[0].Ps.x
                else:
                    minx = self.stmove.shape.geos[0].Pe.x
            else:
                Pocketx = secondgeox
                if self.stmove.shape.geos[1].Ps.x < self.stmove.shape.geos[1].Pe.x:
                    minx = self.stmove.shape.geos[1].Ps.x
                else:
                    minx = self.stmove.shape.geos[1].Pe.x
            if firstgeoy > secondgeoy:
                Pockety = firstgeoy
                if self.stmove.shape.geos[0].Ps.y < self.stmove.shape.geos[0].Pe.y:
                    miny = self.stmove.shape.geos[0].Ps.y
                else:
                    miny = self.stmove.shape.geos[0].Pe.y
            else:
                Pockety = secondgeoy
                if self.stmove.shape.geos[1].Ps.y < self.stmove.shape.geos[1].Pe.y:
                    miny = self.stmove.shape.geos[1].Ps.y
                else:
                    miny = self.stmove.shape.geos[1].Pe.y
            Centerpt = Point(Pocketx/2 + minx, Pockety/2 +miny)
            # calc number of rotations
            if Pockety > Pocketx:
                numberofrotations = int(((Pocketx/2) - self.tool_rad)/self.stmove.shape.OffsetXY)#+1
                if (((Pocketx/2) - self.tool_rad)/self.stmove.shape.OffsetXY)> int(((Pocketx/2) - self.tool_rad)/self.stmove.shape.OffsetXY)+0.5 :
                    numberofrotations += 1
            else:
                numberofrotations = int(((Pockety/2) - self.tool_rad)/self.stmove.shape.OffsetXY)#+1
                if (((Pockety/2) - self.tool_rad)/self.stmove.shape.OffsetXY)> int(((Pockety/2) - self.tool_rad)/self.stmove.shape.OffsetXY)+0.5 :
                    numberofrotations += 1
            logger.debug("stmove:make_start_moves:Shape Center at: %f,%f" % (Centerpt.x, Centerpt.y))  
            print("E stmove:make_start_moves:Shape Center at: %f,%f" % (Centerpt.x, Centerpt.y))        
            for i in range(0, numberofrotations):
                # for CCW Climb milling
                if Pockety > Pocketx: 
                    if (Centerpt.y - (Pockety-Pocketx)/2 - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) - self.tool_rad >= miny):
                        Ps_point1 = Point(Centerpt.x +(self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y + ((Pockety-Pocketx)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) )
                        Pe_point1 = Point(Centerpt.x -(self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y + ((Pockety-Pocketx)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x -(self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y - ((Pockety-Pocketx)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x +(self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y - ((Pockety-Pocketx)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) )
                        Ps_point4 = Pe_point3
                        Pe_point4 = Ps_point1
                    else:
                        Ps_point1 = Point(Centerpt.x + Pocketx/2 - self.tool_rad ,Centerpt.y + Pockety/2 - self.tool_rad )
                        Pe_point1 = Point(Centerpt.x - Pocketx/2 + self.tool_rad ,Centerpt.y + Pockety/2 - self.tool_rad )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - Pocketx/2 + self.tool_rad ,Centerpt.y - Pockety/2 + self.tool_rad )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + Pocketx/2 - self.tool_rad ,Centerpt.y - Pockety/2 + self.tool_rad )
                        Ps_point4 = Pe_point3
                        Pe_point4 = Ps_point1
                    logger.debug("stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                    print("F stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                    if direction == 1: # this is CCW
                        self.stmove.append(LineGeo(Ps_point1,Pe_point1))
                        self.stmove.append(LineGeo(Ps_point2,Pe_point2))
                        self.stmove.append(LineGeo(Ps_point3,Pe_point3))
                        self.stmove.append(LineGeo(Ps_point4,Pe_point4))
                        print('X Lines added [CCW]: ')
                        print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    else: # this is CW
                        self.stmove.append(LineGeo(Pe_point4,Ps_point4))
                        self.stmove.append(LineGeo(Pe_point3,Ps_point3))
                        self.stmove.append(LineGeo(Pe_point2,Ps_point2))
                        self.stmove.append(LineGeo(Pe_point1,Ps_point1))
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
                        if (Centerpt.y - (Pockety-Pocketx)/2 - (self.tool_rad + ((i+1)*self.stmove.shape.OffsetXY)) - self.tool_rad >= miny):
                            en_point = Point(Ps_point1.x + self.stmove.shape.OffsetXY,Ps_point1.y + self.stmove.shape.OffsetXY)
                        else:
                            en_point = Point(Centerpt.x + Pocketx/2 - self.tool_rad,Centerpt.y + Pockety/2 - self.tool_rad)
                                
                        self.stmove.append(LineGeo(st_point,en_point))
                elif Pocketx > Pockety:
                    if (Centerpt.x - (Pocketx-Pockety)/2 - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) - self.tool_rad >= minx):
                        Ps_point1 = Point(Centerpt.x + ((Pocketx-Pockety)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) ,Centerpt.y + (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Pe_point1 = Point(Centerpt.x - ((Pocketx-Pockety)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) ,Centerpt.y + (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - ((Pocketx-Pockety)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) ,Centerpt.y - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + ((Pocketx-Pockety)/2 +(self.tool_rad + (i*self.stmove.shape.OffsetXY))) ,Centerpt.y - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Ps_point4 = Pe_point3
                        Pe_point4 = Ps_point1
                    else:
                        Ps_point1 = Point(Centerpt.x + Pocketx/2 - self.tool_rad ,Centerpt.y + Pockety/2 - self.tool_rad )
                        Pe_point1 = Point(Centerpt.x - Pocketx/2 + self.tool_rad ,Centerpt.y + Pockety/2 - self.tool_rad )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - Pocketx/2 + self.tool_rad ,Centerpt.y - Pockety/2 + self.tool_rad )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + Pocketx/2 - self.tool_rad ,Centerpt.y - Pockety/2 + self.tool_rad )
                        Ps_point4 = Pe_point3
                        Pe_point4 = Ps_point1
                    logger.debug("stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                    print("G stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                    if direction == 1: # this is CCW
                        self.stmove.append(LineGeo(Ps_point1,Pe_point1))
                        self.stmove.append(LineGeo(Ps_point2,Pe_point2))
                        self.stmove.append(LineGeo(Ps_point3,Pe_point3))
                        self.stmove.append(LineGeo(Ps_point4,Pe_point4))
                        print('Z Lines added [CCW]: ')
                        print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    else: # this is CW
                        self.stmove.append(LineGeo(Pe_point4,Ps_point4))
                        self.stmove.append(LineGeo(Pe_point3,Ps_point3))
                        self.stmove.append(LineGeo(Pe_point2,Ps_point2))
                        self.stmove.append(LineGeo(Pe_point1,Ps_point1))
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
                        if (Centerpt.x - (Pocketx-Pockety)/2 - (self.tool_rad + ((i+1)*self.stmove.shape.OffsetXY)) - self.tool_rad >= minx):
                            en_point = Point(Ps_point1.x + self.stmove.shape.OffsetXY,Ps_point1.y + self.stmove.shape.OffsetXY)
                        else:
                            en_point = Point(Centerpt.x + Pocketx/2 - self.tool_rad,Centerpt.y + Pockety/2 - self.tool_rad)
                                
                        self.stmove.append(LineGeo(st_point,en_point))
                elif Pocketx == Pockety:
                    if (Centerpt.x - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) - self.tool_rad >= minx):
                        Ps_point1 = Point(Centerpt.x + (self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y + (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Pe_point1 = Point(Centerpt.x - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y + (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + (self.tool_rad + (i*self.stmove.shape.OffsetXY)) ,Centerpt.y - (self.tool_rad + (i*self.stmove.shape.OffsetXY)) )
                        Ps_point4 = Pe_point3
                        Pe_point4 = Ps_point1
                    else:
                        Ps_point1 = Point(Centerpt.x + Pocketx/2 - self.tool_rad ,Centerpt.y + Pockety/2 - self.tool_rad )
                        Pe_point1 = Point(Centerpt.x - Pocketx/2 + self.tool_rad ,Centerpt.y + Pockety/2 - self.tool_rad )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - Pocketx/2 + self.tool_rad ,Centerpt.y - Pockety/2 + self.tool_rad )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + Pocketx/2 - self.tool_rad ,Centerpt.y - Pockety/2 + self.tool_rad )
                        Ps_point4 = Pe_point3
                        Pe_point4 = Ps_point1
                    logger.debug("stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y)) 
                    print("H stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y)) 
                    if direction == 1: # this is CCW
                        self.stmove.append(LineGeo(Ps_point1,Pe_point1))
                        self.stmove.append(LineGeo(Ps_point2,Pe_point2))
                        self.stmove.append(LineGeo(Ps_point3,Pe_point3))
                        self.stmove.append(LineGeo(Ps_point4,Pe_point4))
                        
                        print('V Lines added [CCW]: ')
                        print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    else: # this is CW
                        self.stmove.append(LineGeo(Pe_point4,Ps_point4))
                        self.stmove.append(LineGeo(Pe_point3,Ps_point3))
                        self.stmove.append(LineGeo(Pe_point2,Ps_point2))
                        self.stmove.append(LineGeo(Pe_point1,Ps_point1))
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
                        if (Centerpt.x - (self.tool_rad + ((i+1)*self.stmove.shape.OffsetXY)) - self.tool_rad >= minx):
                            en_point = Point(Ps_point1.x + self.stmove.shape.OffsetXY,Ps_point1.y + self.stmove.shape.OffsetXY)
                        else:
                            en_point = Point(Centerpt.x + Pocketx/2 - self.tool_rad,Centerpt.y + Pockety/2 - self.tool_rad)
                                
                        self.stmove.append(LineGeo(st_point,en_point))
            
            #TODO
            
        elif True:
            #distances between  map of points to check
            #TODO: different distances in X (smaller) and Y
            self.diff = self.tool_rad*0.9
            
            #print('BB: ' + self.stmove.shape.BB)
            print("self.stmove.BB: %s" % self.stmove.shape.BB)
            
            self.bbarray = BBArray(self.stmove.shape.BB.Ps, self.stmove.shape.BB.Pe, self.diff)
                            
            #self.tool_rad
            #self.stmove.shape.OffsetXY
            
            print("BBBounds: X%s to X%s, Y%s to Y%s" % (self.bbarray.xStart, self.bbarray.xEnd, self.bbarray.yStart, self.bbarray.yEnd))
            
            #how close can be point to shape
            self.dist = self.tool_rad + self.stmove.shape.OffsetXY
            
            ### fill array with TRUEs
            self.bbarray.create()
            ### end of filling array with TRUEs
            
            print("Empty array: ")
            self.bbarray.print()
            print("End of empty array.")
            
            ### check if point is not to close to shape
            self.removeNearShape()
            
            print("Array without Shape: ")
            self.bbarray.print()
            print("Array without Shape END.")
         
            #imagine parallel, horizontal lines (distance of self.diff)
            # this function will find all intersections of those lines
            # with shape.
            self.createInterList()
            
            self.removeOutOfShape()
            
            print("Final array:")
            self.bbarray.print()
            print("End of final array.")
                                
            ### ### ###
            ### Cool! We have now complete array of pionts to mill
            ### but we need to convert it into LINES now...
                    
            #while True:
            #    #this will be always outside BBox of Shape
            #    startPoint = Point(self.bbarray.xStart - 1, self.bbarray.yEnd - 1)
            #    
            #    #BBArrayIndex = 0
            #    for BBPoint in self.bbarray.array:
            #        
            #        if BBPoint.mill == True:
            #            if startPoint.y < yi:
            #                startPoint = Point(xi, yi)
            #            #elif startPoint.y == yi and startPoint.x < xi
            #            #    startPoint = Point(xi, yi)
            #            
            #        xi += self.diff
            #        if self.bbarray.xEnd <= xi:
            #            xi = self.bbarray.xStart + self.diff
            #            yi -= self.diff
            #            
            #        #BBArrayIndex += 1  
            #        
            #    break
            
            #for gg in self.stmove.shape.geos.abs_iter():
            #    if isinstance(gg, LineGeo):
            #        print('Line: ')
            #    elif isinstance(gg, ArcGeo):
            #        print(' Arc: ')
            #        #gg.calc_bounding_box()
            #        #print('Bounding box: ' + gg.BB)
            #    #if (isinstance(self.stmove.selectedItems[0].geos[0], ArcGeo)
            #    print(gg)
            
            #if there are none milling points end function
            #if self.bbarray.checkIfAny() == False:
            #    return
            
            #start from left-bottom
            currentPoint = self.bbarray.findDownLeft()
            
            line = self.bbarray.findHorizontalWithPoint(currentPoint, 1)
            print("Left to right line: %s." % (line))
            
            #go to right
            self.stmove.append(line)
            self.bbarray.removeLine(line)
            
            currentPoint = line.Pe
            goToPoint = self.bbarray.findClosestTopLeft(currentPoint)
            
            print("Go from %s to %s." % (currentPoint, goToPoint))
            
            if goToPoint == None:
                print("NONE?!")
                #break
                
            #if not sraight over "end-point", go back under this point 
            if currentPoint.x != goToPoint.x:
                self.stmove.append(LineGeo(currentPoint, Point(goToPoint.x, currentPoint.y)))
                currentPoint = Point(goToPoint.x, currentPoint.y)
            
            #go to start point of next line
            self.stmove.append(LineGeo(currentPoint, Point(currentPoint.x, goToPoint.y)))
            currentPoint = Point(currentPoint.x, goToPoint.y)
            self.stmove.append(LineGeo(currentPoint, goToPoint))
            
            line = self.bbarray.findHorizontalWithPoint(currentPoint, 0)
            print("Right to left line: %s. " % (line))
            self.stmove.append(line)
            self.bbarray.removeLine(line)
            
            
            #TODO: ltr and rtl on findHorizontalWithPoint
            
            
            
            
            print("Removed line.")
            self.bbarray.print()
            #ipoint = InterPoint(x=0, y=0, i=0, mill = False)
            #print("%s" % (ipoint))
