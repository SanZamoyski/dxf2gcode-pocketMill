# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2008-2015
#    Christian Kohlöffel
#    Vinzenz Schulz
#    Jean-Paul Schouwstra
#
#   Copyright (C) 20019-2020
#    San Zamoyski
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

from dxf2gcode.core.point import Point

import logging
logger = logging.getLogger('core.rapidmove')

class RapidMove(Point):
    def __init__(self, point):
        Point.__init__(self, point.x, point.y)
        self.abs_geo = None
        
        self.feedZ = 0
        self.feedXY = 0
        self.safe = 0
        self.depth = 0
        self.retr = 0

    def get_start_end_points(self, start_point, angles=None):
        if angles is None:
            return self
        elif angles:
            return self, 0
        else:
            return self, Point(0, -1) if start_point else Point(0, -1)
        
    def setZMove(self, feedz, feedxy, safe, depth, retr):
        self.feedZ = feedz
        self.feedXY = feedxy
        self.safe = safe
        self.depth = depth
        self.retr = retr

    def make_abs_geo(self, parent=None):
        """
        Generates the absolute geometry based on itself and the parent. This
        is done for rotating and scaling purposes
        """
        self.abs_geo = RapidMove(self.rot_sca_abs(parent=parent))

    def make_path(self, caller, drawHorLine):
        pass

    def Write_GCode(self, PostPro):
        exstr = ""
        """
        Writes the GCODE for a rapid position.
        @param PostPro: The PostProcessor instance to be used
        @return: Returns the string to be written to a file.
        """
        exstr += PostPro.chg_feed_rate(self.feedZ)
        exstr += PostPro.lin_pol_z(self.safe)
        exstr += PostPro.rap_pos_z(self.retr)
        
        exstr += PostPro.rap_pos_xy(self)
        
        #TODO: going Z-up can be done as full speed?
        exstr += PostPro.rap_pos_z(self.safe)
        exstr += PostPro.chg_feed_rate(self.feedZ)
        exstr += PostPro.lin_pol_z(self.depth)
        exstr += PostPro.chg_feed_rate(self.feedXY)
        
        return exstr
