# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2008-2015
#    Christian Kohlöffel
#    Vinzenz Schulz
#    Jean-Paul Schouwstra
#   
#   Copyright (C) 2019-2020 
#    San Zamoyski for this file
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
#from inspect import getmembers
#from pprint import pprint

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

import time

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
        self.overUpRight = Point(self.xStart + 1, self.xStart + 1)
        self.overDownLeft = Point(self.xEnd - 1, self.xEnd - 1)
        self.overDistance = self.overUpRight.distance(self.overDownLeft)
        
        self.divY = 1
        self.divX = 4
            
    def create(self):
        arrayIndex = 0 
        yi = self.yStart - self.diff / self.divY
            
        while yi > self.yEnd:
            xi = self.xStart + self.diff/self.divX
            while xi < self.xEnd:
                self.append(InterPoint(xi, yi, arrayIndex, True))
                xi += self.diff/self.divX
                arrayIndex += 1
            yi -= self.diff / self.divY
            
    def checkIfAny(self):
        any = False
        
        for point in self.array:
            if point.mill == True:
                any = True
                break

        return any
        
    def append(self, newPoint):
        self.array.append(newPoint)

    #TODO: create one function that returns four extreme points and
    # than (in main) check what is closest to "current" and then decide
    # where to start.
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
        #This will stop work if array will be not in order
        yi = self.array[0].y
        print("%8.2f" % (yi) , end = "\t")
        
        for BBPoint in self.array:
                
            if BBPoint.y != yi:
                yi = BBPoint.y 
                print()
                print("%8.2f" % (yi) , end = "\t")
                
            if BBPoint.mill:
                print('T', end = ' ')
            else:
                print(' ', end = ' ')
                    
        print()
        
    def removeLine(self, line):
        if line.Ps.x > line.Pe.x:
            line = LineGeo(line.Pe, line.Ps)
        
        for BBPoint in self.array:
            if BBPoint.y == line.Ps.y and line.Pe.x >= BBPoint.x and BBPoint.x >= line.Ps.x:
                BBPoint.setMill(False)
                
    def findHorizontalWithPoint(self, point):
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
        
        #print("False x'ses: %s and %s" % (closestFalseLeft, closestFalseRight))
        
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
        
        #print("True x'ses: %s and %s" % (closestTrueLeft, closestTrueRight))
        
        #if ltr == True:
        #    return LineGeo(Point(closestTrueLeft, point.y), Point(closestTrueRight, point.y))
        #else:
        #    return LineGeo(Point(closestTrueRight, point.y), Point(closestTrueLeft, point.y))
        
        if point.distance(Point(closestTrueLeft, point.y)) < point.distance(Point(closestTrueRight, point.y)):
            return LineGeo(Point(closestTrueLeft, point.y), Point(closestTrueRight, point.y))
        else:
            return LineGeo(Point(closestTrueRight, point.y), Point(closestTrueLeft, point.y))
        
    
    #TODO: create function findClosestTopLine which returns two points
    # then check what is closer (in main function) and decide about direction
    # etc.
    def findClosestLine(self, point):
        newPoint = self.overUpRight #doesnt matter
        distance = newPoint.distance(self.overDownLeft)
        new = False
                
        for BBPoint in self.array:
            if BBPoint.mill == False:
                #if this point is not for mill, go next
                continue
            
            #if top == True and BBPoint.y > point.y:
            #    if newPoint.y > BBPoint.y:
            #        continue
            #    
            #elif top == False and BBPoint.y < point.y:
            #    if newPoint.y > BBPoint.y:
            #        continue
            
            if point.distance(BBPoint.p) > distance:
                continue
            
            #if it is under when has to be or top ihas to be
            # remember as new point
            distance = point.distance(BBPoint.p)
            newPoint = BBPoint
            new = True
                    
        if new is True:
            #find line with this point
            return self.findHorizontalWithPoint(newPoint)
        
    def findNextLine(self, line, preferTop):
        bottomY = self.yEnd - 1
        topY    = self.yStart + 1
        currentY = line.Ps.y
        currentX = line.Pe.x
        
        #find closest top and bottom Y
        for BBPoint in self.array:
            #We do not check if it is set to mill, since
            # we want to eliminate lines that are too far
            #if BBPoint.y == currentY and BBPoint.mill == True:
            #    topY = currentY
            #    bottomY = currentY
            #    break
            if topY > BBPoint.y and currentY < BBPoint.y:
                topY = BBPoint.y
            if bottomY < BBPoint.y and currentY > BBPoint.y:
                bottomY = BBPoint.y
                
        print("topY: %s, bottomY: %s." % (topY, bottomY))
        
        if line.Ps.x < line.Pe.x:
            xRangeStart = line.Ps.x
            xRangeEnd   = line.Pe.x
        else:
            xRangeStart = line.Pe.x
            xRangeEnd   = line.Ps.x
        
        xListTop = []
        xListBottom = []
        
        #create two lists of X'es in "good" range
        for BBPoint in self.array:
            if BBPoint.mill == True and xRangeStart <= BBPoint.x <= xRangeEnd:
                if BBPoint.y == topY:
                    xListTop.append(BBPoint.x)
                elif BBPoint.y == bottomY:
                    xListBottom.append(BBPoint.x)
                    
        #if (top or bot_len == 0) and top_len > 0
        #if (!top or top_len == 0) and bot_len > 0
        
        if (preferTop == True or len(xListBottom) == 0) and len(xListTop) > 0:
            if abs(currentX - min(xListTop)) > abs(currentX - max(xListTop)):
                #return Line(Point(max(xListTop), topY), Point(min(xListTop), topY))
                return self.findHorizontalWithPoint(Point(max(xListTop), topY)), False
            else:
                return self.findHorizontalWithPoint(Point(min(xListTop), topY)), False
        elif (preferTop == False or len(xListTop) == 0) and len(xListBottom) > 0:
            if abs(currentX - min(xListBottom)) > abs(currentX - max(xListBottom)):
                #return Line(Point(max(xListTop), topY), Point(min(xListTop), topY))
                return self.findHorizontalWithPoint(Point(max(xListBottom), bottomY)), True
            else:
                return self.findHorizontalWithPoint(Point(min(xListBottom), bottomY)), True
        else:
            print("preferTop is %s, bottom len: %s, top len: %s." % (preferTop, len(xListBottom), len(xListTop)))
            return None, preferTop
                
        
    def findClosestEnd(self, point):
        bottomY    = self.yStart + 1
        topY = self.yEnd - 1
        
        for BBPoint in self.array:
            if BBPoint.mill == True:
                if BBPoint.y > topY:
                    topY = BBPoint.y
                if BBPoint.y < bottomY:
                    bottomY = BBPoint.y
        
        topLeftX     = self.xEnd - 1 
        topRightX    = self.xStart + 1
        bottomLeftX  = self.xEnd - 1
        bottomRightX = self.xStart + 1
        
        for BBPoint in self.array:
            if BBPoint.mill == True:
                if BBPoint.y == topY:
                    if BBPoint.x < topLeftX:
                        topLeftX = BBPoint.x
                    if BBPoint.x > topRightX:
                        topRightX = BBPoint.x
                if BBPoint.y == bottomY:
                    if BBPoint.x < bottomLeftX:
                        bottomLeftX = BBPoint.x
                    if BBPoint.x > bottomRightX:
                        bottomRightX = BBPoint.x
                        
        points = [
            Point(topLeftX, topY),
            Point(topRightX, topY),
            Point(bottomLeftX, bottomY),
            Point(bottomRightX, bottomY)]
        
        distance = self.overDistance
        closestPoint = None
        
        for p in points:
            #print("Extreme: %s." % (p))
            if point.distance(p) < distance:
                distance = point.distance(p)
                closestPoint = p
                
        return closestPoint        
    
    def findClosestTopLeft(self, point):
        #always outside BBox
        newy = self.yStart + 1 
        newx = self.xStart - 1
        
        #find closest y (not necessery True)
        fy = False
        for BBPoint in self.array:
            if BBPoint.y > point.y and BBPoint.y < newy:
                newy = BBPoint.y
                fy = True
        
        if fy == False:
            #should never happen
            #print("YYY")
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
            #print("XXX")
            return None
                
        return Point(newx, newy)
    
    def findClosestTopRight(self, point):
        #always outside BBox
        newy = self.yStart + 1 
        newx = self.xEnd + 1
        
        #find closest y (not necessery True)
        fy = False
        for BBPoint in self.array:
            if BBPoint.y > point.y and BBPoint.y < newy:
                newy = BBPoint.y
                fy = True
        
        if fy == False:
            #should never happen
            return None
        #else:
        #    print("Y: %s" % (newy))
        
        #find in array closest x to left, but with y = newy
        # this time it has to be true
        fx = False
        for BBPoint in self.array:
            if BBPoint.mill == True and BBPoint.y == newy and BBPoint.x >= point.x:
                if newx >= BBPoint.x:
                    newx = BBPoint.x
                    fx = True
        
        #if not found?
        if fx == False:
        #    print("XXX")
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
        yi = self.bbarray.yStart - self.diff/self.bbarray.divY
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
                                
            yi -= self.diff/self.bbarray.divY
            #print("End of finding intersections")
        
    def createLines(self):
        
        circle = 0
        horizontalRectangle = 0
        
        geosNum = len(self.stmove.shape.geos)
        print("Number of geos: %s" % (geosNum))
        
        #set the proper direction for the tool path
        if self.stmove.shape.cw ==True:
            direction = -1;
        else:
            direction = 1;
            
        print("Starting point is: %s" % (self.stmove.start))
        
        if geosNum == 2:
            if self.stmove.shape.geos[0].r == self.stmove.shape.geos[1].r and self.stmove.shape.geos[0].Ps == self.stmove.shape.geos[1].Pe and self.stmove.shape.geos[0].Pe == self.stmove.shape.geos[1].Ps:
                    #print("Circle")
                    #TODO: tweak? 
                    circleOff = 0.9 * self.tool_rad #self.stmove.shape.OffsetXY
                    #direction = 1
                    circle = 1
                    
        if geosNum == 4:
            hLines = 0
            vLines = 0
            linesNum = 0
            
            for gLine in self.stmove.shape.geos:
                if isinstance(gLine, LineGeo) and gLine.Ps.x == gLine.Pe.x:
                    vLines += 1
                if isinstance(gLine, LineGeo) and gLine.Ps.y == gLine.Pe.y:
                    hLines += 1
                    
            if hLines == 2 and vLines == 2:
                horizontalRectangle = 1
                
            #rad varsus rad*2^(1/2) is 0,707106781
            hRectangleOff = 0.7 * self.tool_rad #self.stmove.shape.OffsetXY
                
            #print("Rectangle? V:%s, H:%s" % (vLines, hLines))
                
        currentPoint = self.stmove.start
            
        if False:
            print("beans shape")
            #TODO:
            #   ____
            #  (____)
        elif circle == 1:            
            numberofrotations = int((self.stmove.shape.geos[0].r - self.tool_rad)/circleOff)-1
            if ((self.stmove.shape.geos[0].r - self.tool_rad)/circleOff)> numberofrotations :
                numberofrotations += 1
            logger.debug("stmove:make_start_moves:Tool Radius: %f" % (self.tool_rad))
            logger.debug("stmove:make_start_moves:StepOver XY: %f" % (circleOff))
            logger.debug("stmove:make_start_moves:Shape Radius: %f" % (self.stmove.shape.geos[0].r))
            logger.debug("stmove:make_start_moves:Shape Origin at: %f,%f" % (self.stmove.shape.geos[0].O.x, self.stmove.shape.geos[0].O.y))
            logger.debug("stmove:make_start_moves:Number of Arcs: %f" % (numberofrotations+1))
            for i in range(0, numberofrotations + 1):
                st_point = Point(self.stmove.shape.geos[0].O.x,self.stmove.shape.geos[0].O.y)
                Ps_point = Point(self.stmove.shape.geos[0].O.x +(self.tool_rad + (i*circleOff)) ,self.stmove.shape.geos[0].O.y)
                Pe_point = Ps_point
                if ((Ps_point.x - self.stmove.shape.geos[0].O.x + self.tool_rad) < self.stmove.shape.geos[0].r):
                    self.stmove.append(ArcGeo(Ps=Ps_point, Pe=Pe_point, O=st_point, r=(self.tool_rad + (i*circleOff)), direction=direction))
                else:
                    Ps_point = Point(self.stmove.shape.geos[0].O.x + self.stmove.shape.geos[0].r - self.tool_rad  ,self.stmove.shape.geos[0].O.y)
                    Pe_point = Ps_point
                    self.stmove.append(ArcGeo(Ps=Ps_point, Pe=Pe_point, O=st_point, r=(Ps_point.x - self.stmove.shape.geos[0].O.x), direction=direction))
                
                logger.debug("stmove:make_start_moves:Toolpath Arc at: %f,%f" % (Ps_point.x,Ps_point.x))   
                
                if i<numberofrotations:
                    st_point = Point(Ps_point.x,Ps_point.y)
                    if ((Ps_point.x + circleOff - self.stmove.shape.geos[0].O.x + self.tool_rad) < self.stmove.shape.geos[0].r):
                        en_point = Point(Ps_point.x + circleOff,Ps_point.y)
                    else:
                        en_point = Point(self.stmove.shape.geos[0].O.x + self.stmove.shape.geos[0].r - self.tool_rad,Ps_point.y)
                        
                    self.stmove.append(LineGeo(st_point,en_point))
                        
        elif horizontalRectangle == 1:
            #TODO: if 4 lines, and they are parallel
            #for rectangular pocket
            
            #print('D Rectangular pocket: ')
            
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
                numberofrotations = int(((Pocketx/2) - self.tool_rad)/hRectangleOff)#+1
                if (((Pocketx/2) - self.tool_rad)/hRectangleOff)> int(((Pocketx/2) - self.tool_rad)/hRectangleOff)+0.5 :
                    numberofrotations += 1
            else:
                numberofrotations = int(((Pockety/2) - self.tool_rad)/hRectangleOff)#+1
                if (((Pockety/2) - self.tool_rad)/hRectangleOff)> int(((Pockety/2) - self.tool_rad)/hRectangleOff)+0.5 :
                    numberofrotations += 1
            logger.debug("stmove:make_start_moves:Shape Center at: %f,%f" % (Centerpt.x, Centerpt.y))  
            #print("E stmove:make_start_moves:Shape Center at: %f,%f" % (Centerpt.x, Centerpt.y))        
            for i in range(0, numberofrotations):
                # for CCW Climb milling
                if Pockety > Pocketx: 
                    if (Centerpt.y - (Pockety-Pocketx)/2 - (self.tool_rad + (i*hRectangleOff)) - self.tool_rad >= miny):
                        Ps_point1 = Point(Centerpt.x +(self.tool_rad + (i*hRectangleOff)) ,Centerpt.y + ((Pockety-Pocketx)/2 +(self.tool_rad + (i*hRectangleOff))) )
                        Pe_point1 = Point(Centerpt.x -(self.tool_rad + (i*hRectangleOff)) ,Centerpt.y + ((Pockety-Pocketx)/2 +(self.tool_rad + (i*hRectangleOff))) )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x -(self.tool_rad + (i*hRectangleOff)) ,Centerpt.y - ((Pockety-Pocketx)/2 +(self.tool_rad + (i*hRectangleOff))) )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x +(self.tool_rad + (i*hRectangleOff)) ,Centerpt.y - ((Pockety-Pocketx)/2 +(self.tool_rad + (i*hRectangleOff))) )
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
                    #print("F stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                    if direction == 1: # this is CCW
                        if i == 0:
                            self.stmove.append(LineGeo(currentPoint, Ps_point1))
                        
                        self.stmove.append(LineGeo(Ps_point1,Pe_point1))
                        self.stmove.append(LineGeo(Ps_point2,Pe_point2))
                        self.stmove.append(LineGeo(Ps_point3,Pe_point3))
                        self.stmove.append(LineGeo(Ps_point4,Pe_point4))
                        #print('X Lines added [CCW]: ')
                        #print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        #print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        #print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        #print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    else: # this is CW
                        if i == 0:
                            self.stmove.append(LineGeo(currentPoint, Pe_point4))
                            
                        self.stmove.append(LineGeo(Pe_point4,Ps_point4))
                        self.stmove.append(LineGeo(Pe_point3,Ps_point3))
                        self.stmove.append(LineGeo(Pe_point2,Ps_point2))
                        self.stmove.append(LineGeo(Pe_point1,Ps_point1))
                        #print('Y Lines added [CW]: ')
                        print("Line from: %fx%f to %fx%f" % (Ps_point4.x, Ps_point4.y, Pe_point4.x, Pe_point4.y))
                        print("Line from: %fx%f to %fx%f" % (Ps_point3.x, Ps_point3.y, Pe_point3.x, Pe_point3.y))
                        print("Line from: %fx%f to %fx%f" % (Ps_point2.x, Ps_point2.y, Pe_point2.x, Pe_point2.y))
                        print("Line from: %fx%f to %fx%f" % (Ps_point1.x, Ps_point1.y, Pe_point1.x, Pe_point1.y))
                        
                    if i<numberofrotations-1:
                        if direction == 1: # this is CCW
                            st_point = Point(Ps_point1.x,Ps_point1.y)
                        else: # this is CW
                            st_point = Point(Pe_point4.x,Pe_point4.y)
                        if (Centerpt.y - (Pockety-Pocketx)/2 - (self.tool_rad + ((i+1)*hRectangleOff)) - self.tool_rad >= miny):
                            en_point = Point(Ps_point1.x + hRectangleOff,Ps_point1.y + hRectangleOff)
                        else:
                            en_point = Point(Centerpt.x + Pocketx/2 - self.tool_rad,Centerpt.y + Pockety/2 - self.tool_rad)
                                
                        self.stmove.append(LineGeo(st_point,en_point))
                elif Pocketx > Pockety:
                    if (Centerpt.x - (Pocketx-Pockety)/2 - (self.tool_rad + (i*hRectangleOff)) - self.tool_rad >= minx):
                        Ps_point1 = Point(Centerpt.x + ((Pocketx-Pockety)/2 +(self.tool_rad + (i*hRectangleOff))) ,Centerpt.y + (self.tool_rad + (i*hRectangleOff)) )
                        Pe_point1 = Point(Centerpt.x - ((Pocketx-Pockety)/2 +(self.tool_rad + (i*hRectangleOff))) ,Centerpt.y + (self.tool_rad + (i*hRectangleOff)) )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - ((Pocketx-Pockety)/2 +(self.tool_rad + (i*hRectangleOff))) ,Centerpt.y - (self.tool_rad + (i*hRectangleOff)) )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + ((Pocketx-Pockety)/2 +(self.tool_rad + (i*hRectangleOff))) ,Centerpt.y - (self.tool_rad + (i*hRectangleOff)) )
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
                    #print("G stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y))
                    if direction == 1: # this is CCW
                        if i == 0:
                            self.stmove.append(LineGeo(currentPoint, Ps_point1))
                            
                        self.stmove.append(LineGeo(Ps_point1,Pe_point1))
                        self.stmove.append(LineGeo(Ps_point2,Pe_point2))
                        self.stmove.append(LineGeo(Ps_point3,Pe_point3))
                        self.stmove.append(LineGeo(Ps_point4,Pe_point4))
                        #print('Z Lines added [CCW]: ')
                        #print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        #print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        #print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        #print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    else: # this is CW
                        if i == 0:
                            self.stmove.append(LineGeo(currentPoint, Pe_point4))
                            
                        self.stmove.append(LineGeo(Pe_point4,Ps_point4))
                        self.stmove.append(LineGeo(Pe_point3,Ps_point3))
                        self.stmove.append(LineGeo(Pe_point2,Ps_point2))
                        self.stmove.append(LineGeo(Pe_point1,Ps_point1))
                        #print('Q Lines added [CW]: ')
                        #print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        #print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        #print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        #print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    if i<numberofrotations-1:
                        if direction == 1: # this is CCW
                            st_point = Point(Ps_point1.x,Ps_point1.y)
                        else: # this is CW
                            st_point = Point(Pe_point4.x,Pe_point4.y)
                        if (Centerpt.x - (Pocketx-Pockety)/2 - (self.tool_rad + ((i+1)*hRectangleOff)) - self.tool_rad >= minx):
                            en_point = Point(Ps_point1.x + hRectangleOff,Ps_point1.y + hRectangleOff)
                        else:
                            en_point = Point(Centerpt.x + Pocketx/2 - self.tool_rad,Centerpt.y + Pockety/2 - self.tool_rad)
                                
                        self.stmove.append(LineGeo(st_point,en_point))
                elif Pocketx == Pockety:
                    if (Centerpt.x - (self.tool_rad + (i*hRectangleOff)) - self.tool_rad >= minx):
                        Ps_point1 = Point(Centerpt.x + (self.tool_rad + (i*hRectangleOff)) ,Centerpt.y + (self.tool_rad + (i*hRectangleOff)) )
                        Pe_point1 = Point(Centerpt.x - (self.tool_rad + (i*hRectangleOff)) ,Centerpt.y + (self.tool_rad + (i*hRectangleOff)) )
                        Ps_point2 = Pe_point1
                        Pe_point2 = Point(Centerpt.x - (self.tool_rad + (i*hRectangleOff)) ,Centerpt.y - (self.tool_rad + (i*hRectangleOff)) )
                        Ps_point3 = Pe_point2
                        Pe_point3 = Point(Centerpt.x + (self.tool_rad + (i*hRectangleOff)) ,Centerpt.y - (self.tool_rad + (i*hRectangleOff)) )
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
                    #print("H stmove:make_start_moves:Starting point at: %f,%f" % (Ps_point1.x, Ps_point1.y)) 
                    if direction == 1: # this is CCW
                        if i == 0:
                            self.stmove.append(LineGeo(currentPoint, Ps_point1))
                            
                        self.stmove.append(LineGeo(Ps_point1,Pe_point1))
                        self.stmove.append(LineGeo(Ps_point2,Pe_point2))
                        self.stmove.append(LineGeo(Ps_point3,Pe_point3))
                        self.stmove.append(LineGeo(Ps_point4,Pe_point4))
                        
                        #print('V Lines added [CCW]: ')
                        #print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        #print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        #print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        #print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    else: # this is CW
                        if i == 0:
                            self.stmove.append(LineGeo(currentPoint, Pe_point4))
                            
                        self.stmove.append(LineGeo(Pe_point4,Ps_point4))
                        self.stmove.append(LineGeo(Pe_point3,Ps_point3))
                        self.stmove.append(LineGeo(Pe_point2,Ps_point2))
                        self.stmove.append(LineGeo(Pe_point1,Ps_point1))
                        #print('P Lines added [CW]: ')
                        #print('Point ' + Ps_point1 + 'x' + Pe_point1)
                        #print('Point ' + Ps_point2 + 'x' + Pe_point2)
                        #print('Point ' + Ps_point3 + 'x' + Pe_point3)
                        #print('Point ' + Ps_point4 + 'x' + Pe_point4)
                        
                    if i<numberofrotations-1:
                        if direction == 1: # this is CCW
                            st_point = Point(Ps_point1.x,Ps_point1.y)
                        else: # this is CW
                            st_point = Point(Pe_point4.x,Pe_point4.y)
                        if (Centerpt.x - (self.tool_rad + ((i+1)*hRectangleOff)) - self.tool_rad >= minx):
                            en_point = Point(Ps_point1.x + hRectangleOff,Ps_point1.y + hRectangleOff)
                        else:
                            en_point = Point(Centerpt.x + Pocketx/2 - self.tool_rad,Centerpt.y + Pockety/2 - self.tool_rad)
                                
                        self.stmove.append(LineGeo(st_point,en_point))
            
        else:
            #distances between  map of points to check
            #TODO?: different distances in X (smaller) and Y
            # TODO: Y distance should be calculated
            
            #rad varsus rad*2^(1/2) is 0,707106781
            self.diff = self.tool_rad*2 * 0.7
            
            compType = self.stmove.shape.cut_cor
            
            #Compensation:
            # 42 - inside
            # 41 - outside
            # 40 - no compensation
            print("Compensations type: %s." % (compType))
            
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
            if compType == 42:
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
            ### Cool! We have now complete array of points to mill
            ### but we need to convert it into LINES now...
                    
            print("Tool rad is %s." % (self.tool_rad))
            
            #currentPoint = Point(self.stmove.start.x, self.stmove.start.y)
            currentPoint = self.stmove.start
                
            while self.bbarray.checkIfAny():
                #Find start for new zig-zag and go there.
                closestPoint = self.bbarray.findClosestEnd(currentPoint)
                closestLine = self.bbarray.findHorizontalWithPoint(closestPoint)
                print("Closest end line to start is %s." % (closestLine))
                print("Closest point to start is %s." % (closestPoint))
                goToPoint = closestLine.Ps
                
                self.stmove.append(LineGeo(currentPoint, goToPoint))
                currentPoint = goToPoint
                
                preferTop = True
                                                
                while True:
                    #currentPoint should be one of bbarray.mill = true now
                    # so we are between Ps and Pe of next line at Y height
                    #Do first line from starting point 
                    line = self.bbarray.findHorizontalWithPoint(currentPoint)    #dir
                    
                    #if toRight == True:
                    #    print("Left to right line at %8.2f: from %8.2f to %8.2f." % (line.Ps.y, line.Ps.x, line.Pe.x))
                    #else:
                    #    print("Right to left line at %8.2f: from %8.2f to %8.2f." % (line.Ps.y, line.Ps.x, line.Pe.x))
                    
                    #print("Line at Y%8.2f: from X%8.2f to X%8.2f." % (line.Ps.y, line.Ps.x, line.Pe.x))
                    
                    #If we are not at start point, go there
                    if currentPoint.x != line.Ps.x:
                        self.stmove.append(LineGeo(currentPoint, line.Ps))                        
                    
                    self.stmove.append(line)
                    self.bbarray.removeLine(line)
                    currentPoint = line.Pe
                    
                    #Now we need to check if there is any near line we can go
                    line, preferTop = self.bbarray.findNextLine(line, preferTop)
                    
                    if line == None:
                        print("Done.")
                        break
                    else:
                        print("Closest line is %s x %s => %s x %s." % (line.Ps.x, line.Ps.y, line.Pe.x, line.Pe.y))
                    
                    #check if we can go straight up, or we need to do some stuff...
                    if not (line.Ps.x <= currentPoint.x <= line.Pe.x or line.Ps.x >= currentPoint.x >= line.Pe.x):
                        #we need to do some stuff: go back under next line
                        goToPoint = Point(line.Ps.x, currentPoint.y)
                        self.stmove.append(LineGeo(currentPoint, goToPoint))
                        currentPoint = goToPoint
                        
                    #Ok, go straight up, and end on nextLine (somewhere 
                    # between or on start/end point
                    goToPoint = Point(currentPoint.x, line.Ps.y)
                    self.stmove.append(LineGeo(currentPoint, goToPoint))
                    currentPoint = goToPoint
                            
                print("Removed lines.")
                self.bbarray.print()
