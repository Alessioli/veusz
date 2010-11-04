# -*- coding: utf-8 -*-

#    Copyright (C) 2010 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
##############################################################################

# $Id$

"""Polar plot widget."""

import qtall as qt4
import numpy as N

from nonorthgraph import NonOrthGraph
from axisticks import AxisTicks
from axis import TickLabel

import veusz.document as document
import veusz.setting as setting
import veusz.utils as utils

class Tick(setting.Line):
    '''Polar tick settings.'''

    def __init__(self, name, **args):
        setting.Line.__init__(self, name, **args)
        self.add( setting.DistancePt( 'length',
                                      '6pt',
                                      descr = 'Length of major ticks',
                                      usertext='Length') )
        self.add( setting.Int( 'number',
                               6,
                               descr = 'Number of major ticks to aim for',
                               usertext='Number') )
        self.add( setting.Bool('hidespokes', False,
                               descr = 'Hide radial spokes',
                               usertext = 'Hide spokes') )
        self.add( setting.Bool('hideannuli', False,
                               descr = 'Hide annuli',
                               usertext = 'Hide annuli') )
        self.get('color').newDefault('grey')

    def getLength(self, painter):
        '''Return tick length in painter coordinates'''
        
        return self.get('length').convert(painter)

class Polar(NonOrthGraph):
    '''Polar plotter.'''

    typename='polar'
    allowusercreation = True
    description = 'Polar graph'

    def __init__(self, parent, name=None):
        '''Initialise polar plot.'''
        NonOrthGraph.__init__(self, parent, name=name)
        if type(self) == NonOrthGraph:
            self.readDefaults()

    @classmethod
    def addSettings(klass, s):
        '''Construct list of settings.'''
        NonOrthGraph.addSettings(s)

        s.add( setting.FloatOrAuto('maxradius', 'Auto',
                                   descr='Maximum value of radius',
                                   usertext='Max radius') )
        s.add( setting.Choice('units',
                              ('degrees', 'radians'), 
                              'degrees', 
                              descr = 'Angular units',
                              usertext='Units') )
        s.add( setting.Choice('direction',
                              ('clockwise', 'anticlockwise'),
                              'anticlockwise',
                              descr = 'Angle direction',
                              usertext = 'Direction') )
        s.add( setting.Choice('position0',
                              ('right', 'top', 'left', 'bottom'),
                              'right',
                              descr = 'Direction of 0 angle',
                              usertext = u'Position of 0°') )

        s.add( TickLabel('TickLabels', descr = 'Tick labels',
                    usertext='Tick labels'),
               pixmap='settings_axisticklabels' )
        s.add( Tick('Tick', descr = 'Tick line',
                    usertext='Tick'),
               pixmap='settings_axismajorticks' )

        s.get('leftMargin').newDefault('1cm')
        s.get('rightMargin').newDefault('1cm')
        s.get('topMargin').newDefault('1cm')
        s.get('bottomMargin').newDefault('1cm')

    def graphToPlotCoords(self, coorda, coordb):
        '''Convert coordinates in r, theta to x, y.'''

        s = self.settings
        cb = coordb
        if s.units == 'degrees':
            cb = coordb * (N.pi/180.)
        ca = coorda / self._maxradius

        # change direction
        if s.direction == 'anticlockwise':
            cb = -cb

        # add offset
        cb -= {'right': 0, 'top': 0.5*N.pi, 'left': N.pi,
               'bottom': 1.5*N.pi}[s.position0]

        x = self._xc + ca * N.cos(cb) * self._xscale
        y = self._yc + ca * N.sin(cb) * self._yscale
        return x, y

    def drawGraph(self, painter, bounds, datarange, outerbounds=None):
        '''Plot graph area and axes.'''

        s = self.settings
        if s.maxradius == 'Auto':
            self._maxradius = datarange[1]
        else:
            self._maxradius = s.maxradius
    
        self._xscale = (bounds[2]-bounds[0])*0.5
        self._yscale = (bounds[3]-bounds[1])*0.5
        self._xc = 0.5*(bounds[0]+bounds[2])
        self._yc = 0.5*(bounds[3]+bounds[1])

        painter.setPen( s.Border.makeQPenWHide(painter) )
        painter.setBrush( s.Background.makeQBrushWHide() )
        painter.drawEllipse( qt4.QRectF( qt4.QPointF(bounds[0], bounds[1]),
                                         qt4.QPointF(bounds[2], bounds[3]) ) )

    def setClip(self, painter, bounds):
        '''Set clipping for graph.'''
        p = qt4.QPainterPath()
        p.addEllipse( qt4.QRectF( qt4.QPointF(bounds[0], bounds[1]),
                                  qt4.QPointF(bounds[2], bounds[3]) ) )
        painter.setClipPath(p)

    def drawAxes(self, painter, bounds, datarange, outerbounds=None):
        '''Plot axes.'''

        s = self.settings
        t = s.Tick

        if self._maxradius <= 0.:
            self._maxradius = 1.

        atick = AxisTicks(0, self._maxradius, t.number,
                          t.number*4,
                          extendbounds=False,  extendzero=False)
        minval, maxval, majtick, mintick, tickformat = atick.getTicks()

        # draw ticks as circles
        if not t.hideannuli:
            painter.setPen( s.Tick.makeQPenWHide(painter) )
            painter.setBrush( qt4.QBrush() )      
            for tick in majtick[1:]:
                radius = tick / self._maxradius

                painter.drawEllipse(qt4.QRectF(
                        qt4.QPointF( self._xc - radius*self._xscale,
                                     self._yc - radius*self._yscale ),
                        qt4.QPointF( self._xc + radius*self._xscale,
                                     self._yc + radius*self._yscale ) ))

        # setup axes plot
        tl = s.TickLabels
        scale, format = tl.scale, tl.format
        if format == 'Auto':
            format = tickformat
        painter.setPen( tl.makeQPen() )
        font = tl.makeQFont(painter)

        # draw radial axis
        for tick in majtick[1:]:
            num = utils.formatNumber(tick*scale, format)
            x = tick / self._maxradius * self._xscale + self._xc
            r = utils.Renderer(painter, font, x, self._yc, num, alignhorz=-1,
                               alignvert=-1, usefullheight=True)
            r.render()

        if s.units == 'degrees':
            angles = [ u'0°', u'30°', u'60°', u'90°', u'120°', u'150°',
                       u'180°', u'210°', u'240°', u'270°', u'300°', u'330°' ]
        else:
            angles = [ '0', u'π/6', u'π/3', u'π/2', u'2π/3', u'5π/6',
                       u'π', u'7π/6', u'4π/3', u'3π/2', u'5π/3', u'11π/6' ]

        align = [ (-1, 1), (-1, 1), (-1, 1), (0, 1), (1, 1), (1, 1),
                  (1, 0), (1, -1), (1, -1), (0, -1), (-1, -1), (-1, -1) ]

        if s.direction == 'anticlockwise':
            angles = angles[0:1] + angles[1:][::-1]
        
        # rotate labels if zero not at right
        if s.position0 == 'top':
            angles = angles[3:] + angles[:4]
        elif s.position0 == 'left':
            angles = angles[6:] + angles[:7]
        elif s.position0 == 'bottom':
            angles = angles[9:] + angles[:10]

        # draw labels around plot
        for i in xrange(12):
            angle = 2 * N.pi / 12
            x = self._xc +  N.cos(angle*i) * self._xscale
            y = self._yc +  N.sin(angle*i) * self._yscale
            r = utils.Renderer(painter, font, x, y, angles[i],
                               alignhorz=align[i][0],
                               alignvert=align[i][1],
                               usefullheight=True)
            r.render()
            
        # draw spokes
        if not t.hidespokes:
            painter.setPen( s.Tick.makeQPenWHide(painter) )
            painter.setBrush( qt4.QBrush() )      
            angle = 2 * N.pi / 12
            lines = []
            for i in xrange(12):
                x = self._xc +  N.cos(angle*i) * self._xscale
                y = self._yc +  N.sin(angle*i) * self._yscale
                lines.append( qt4.QLineF(qt4.QPointF(self._xc, self._yc),
                                         qt4.QPointF(x, y)) )
            painter.drawLines(lines)

document.thefactory.register(Polar)
