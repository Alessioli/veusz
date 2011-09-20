#    Copyright (C) 2005 Jeremy S. Sanders
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
###############################################################################

"""Image plotting from 2d datasets."""

import veusz.qtall as qt4
import numpy as N

import veusz.setting as setting
import veusz.document as document
import veusz.utils as utils

import plotters

class Image(plotters.GenericPlotter):
    """A class which plots an image on a graph with a specified
    coordinate system."""

    typename='image'
    allowusercreation=True
    description='Plot a 2d dataset as an image'

    def __init__(self, parent, name=None):
        """Initialise plotter with axes."""

        plotters.GenericPlotter.__init__(self, parent, name=name)

        self.lastcolormap = None
        self.lastdataset = None
        self.schangeset = -1

        # this is the range of data plotted, computed when plot is changed
        # the ColorBar object needs this later
        self.cacheddatarange = (0, 1)

        if type(self) == Image:
            self.readDefaults()

    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        plotters.GenericPlotter.addSettings(s)

        s.add( setting.Dataset('data', '',
                               dimensions = 2,
                               descr = 'Dataset to plot',
                               usertext='Dataset'),
               0 )
        s.add( setting.FloatOrAuto('min', 'Auto',
                                   descr = 'Minimum value of image scale',
                                   usertext='Min. value'),
               1 )
        s.add( setting.FloatOrAuto('max', 'Auto',
                                   descr = 'Maximum value of image scale',
                                   usertext='Max. value'),
               2 )
        s.add( setting.Choice('colorScaling',
                              ['linear', 'sqrt', 'log', 'squared'],
                              'linear',
                              descr = 'Scaling to transform numbers to color',
                              usertext='Scaling'),
               3 )

        s.add( setting.Dataset('transparencyData', '',
                               dimensions = 2,
                               descr = 'Dataset to use for transparency '
                               '(0 to 1)',
                               usertext='Transparent data'),
               4 )

        s.add( setting.Colormap('colorMap',
                                'grey',
                                descr = 'Set of colors to plot data with',
                                usertext='Colormap',
                                formatting=True),
               5 )
        s.add( setting.Bool('colorInvert', False,
                            descr = 'Invert color map',
                            usertext='Invert colormap',
                            formatting=True),
               6 )
        s.add( setting.Int( 'transparency', 0,
                            descr = 'Transparency percentage',
                            usertext = 'Transparency',
                            minval = 0,
                            maxval = 100,
                            formatting=True),
               7 )

        s.add( setting.Bool( 'smooth', False,
                             descr = 'Smooth image to display resolution',
                             usertext = 'Smooth',
                             formatting = True ) )

    def dataHasChanged(self):
        s = self.settings
        return self.dsmonitor.hasChanged(s.get('data'), s.get('transparencyData'))

    def _getUserDescription(self):
        """User friendly description."""
        s = self.settings
        out = []
        if s.data:
            out.append(s.data)
        out += [s.colorScaling, s.colorMap]
        return ', '.join(out)
    userdescription = property(_getUserDescription)

    def updateImage(self):
        """Update the image with new contents."""

        s = self.settings
        d = self.document
        data = d.data[s.data]

        transimg = None
        if s.transparencyData in d.data:
            transimg = d.data[s.transparencyData].data

        minval = s.min
        if minval == 'Auto':
            minval = N.nanmin(data.data)
        maxval = s.max
        if maxval == 'Auto':
            maxval = N.nanmax(data.data)

        # this is used currently by colorbar objects
        self.cacheddatarange = (minval, maxval)

        # use grey by default
        cmap = d.colormaps.get(s.colorMap, d.colormaps['grey'])
        if s.colorInvert:
            cmap = cmap[::-1]

        self.image = utils.applyColorMap(
            cmap, s.colorScaling, data.data, minval, maxval,
            s.transparency, transimg=transimg)

    def providesAxesDependency(self):
        """Range information provided by widget."""
        s = self.settings
        return ( (s.xAxis, 'sx'), (s.yAxis, 'sy') )

    def updateAxisRange(self, axis, depname, axrange):
        """Automatically determine the ranges of variable on the axes."""

        # this is copied from Image, probably should combine
        s = self.settings
        d = self.document

        # return if no data
        if s.data not in d.data:
            return

        # return if the dataset isn't two dimensional
        data = d.data[s.data]
        if data.dimensions != 2:
            return

        if depname == 'sx':
            dxrange = data.xrange
            axrange[0] = min( axrange[0], dxrange[0] )
            axrange[1] = max( axrange[1], dxrange[1] )
        elif depname == 'sy':
            dyrange = data.yrange
            axrange[0] = min( axrange[0], dyrange[0] )
            axrange[1] = max( axrange[1], dyrange[1] )

    def cutImageToFit(self, pltx, plty, posn):
        x1, y1, x2, y2 = posn
        pltx1, pltx2 = pltx
        pltw = pltx2-pltx1
        plty2, plty1 = plty
        plth = plty2-plty1

        imw = self.image.width()
        imh = self.image.height()
        pixw = pltw / float(imw)
        pixh = plth / float(imh)
        cutr = [0, 0, imw-1, imh-1]

        # work out where image intercepts posn, and make sure image
        # fills at least that area

        # need to chop left
        if pltx1 < x1:
            d = int((x1-pltx1) / pixw)
            cutr[0] += d
            pltx[0] += d*pixw

        # need to chop right
        if pltx2 > x2:
            d = max(0, int((pltx2-x2) / pixw) - 1)
            cutr[2] -= d
            pltx[1] -= d*pixw

        # chop top
        if plty1 < y1:
            d = int((y1-plty1) / pixh)
            cutr[1] += d
            plty[1] += d*pixh
            
        # chop bottom
        if plty2 > y2:
            d = max(0, int((plty2-y2) / pixh) - 1)
            cutr[3] -= d
            plty[0] -= d*pixh

        # create chopped-down image
        newimage = self.image.copy(cutr[0], cutr[1],
                                   cutr[2]-cutr[0]+1, cutr[3]-cutr[1]+1)

        # return new image coordinates and image
        return pltx, plty, newimage

    def makeColorbarImage(self, direction='horz'):
        """Make a QImage colorbar for the current plot.

        direction is 'horizontal' or 'vertical' to draw horizontal or
          vertical bars

        Returns a tuple (minval, maxval, scale, qimage)

        minval is the minimum value which should be plotted on the axis
        maxval is the maximum "                                       "
        scale is 'linear' or 'log', depending on how numbers should be scaled
        qimage is a QImage of 1 x barsize
        """

        self.recomputeInternals()

        barsize = 128
        s = self.settings
        minval, maxval = self.cacheddatarange

        if s.colorScaling in ('linear', 'sqrt', 'squared'):
            # do a linear color scaling
            vals = N.arange(barsize)/(barsize-1.0)*(maxval-minval) + minval
            colorscaling = s.colorScaling
            coloraxisscale = 'linear'
        else:
            assert s.colorScaling == 'log'

            # a logarithmic color scaling
            # we cheat here by actually plotting a linear colorbar
            # and telling veusz to put a log axis along it
            # (as we only care about the endpoints)
            # maybe should do this better...
            
            vals = N.arange(barsize)/(barsize-1.0)*(maxval-minval) + minval
            colorscaling = 'linear'
            coloraxisscale = 'log'

        # convert 1d array to 2d image
        if direction == 'horizontal':
            vals = vals.reshape(1, barsize)
        else:
            assert direction == 'vertical'
            vals = vals.reshape(barsize, 1)

        cmap = self.document.colormaps[s.colorMap]
        if s.colorInvert:
            cmap = cmap[::-1]

        img = utils.applyColorMap(cmap, colorscaling, vals,
                                  minval, maxval, s.transparency)

        return (minval, maxval, coloraxisscale, img)

    def recomputeInternals(self):
        """Recompute the internals if required.

        This is used by colorbar as it needs to know data range when plotting
        """

        s = self.settings
        d = self.document

        # return if the dataset isn't two dimensional
        try:
            data = d.data[s.data]
        except KeyError:
            return None

        # recompute data 
        if data.dimensions == 2:
            if data != self.lastdataset or self.schangeset != self.changeset:
                self.updateImage()
                self.lastdataset = data
                self.schangeset = self.changeset
            return data
        else:
            return None
    
    def draw(self, parentposn, phelper, outerbounds = None):
        """Draw the image."""

        posn = plotters.GenericPlotter.draw(self, parentposn, phelper,
                                            outerbounds = outerbounds)
        x1, y1, x2, y2 = posn
        s = self.settings
        d = self.document

        # get axes widgets
        axes = self.parent.getAxes( (s.xAxis, s.yAxis) )

        # return if there's no proper axes
        if ( None in axes or
             axes[0].settings.direction != 'horizontal' or
             axes[1].settings.direction != 'vertical' ):
            return

        # get data and update internal computations
        data = self.recomputeInternals()
        if not data or s.hide:
            return

        # find coordinates of image coordinate bounds
        rangex, rangey = data.getDataRanges()

        # translate coordinates to plotter coordinates
        coordsx = axes[0].dataToPlotterCoords(posn, N.array(rangex))
        coordsy = axes[1].dataToPlotterCoords(posn, N.array(rangey))

        # truncate image down if necessary
        # This assumes linear pixels!
        if ( coordsx[0] < x1 or coordsx[1] > x2 or
             coordsy[0] < y1 or coordsy[1] > y2 ):

            coordsx, coordsy, image = self.cutImageToFit(coordsx, coordsy,
                                                         posn)
        else:
            image = self.image

        # clip data within bounds of plotter
        clip = self.clipAxesBounds(axes, posn)
        painter = phelper.painter(self, posn, clip=clip)

        # optionally smooth images before displaying
        if s.smooth:
            image = image.scaled( coordsx[1]-coordsx[0], coordsy[0]-coordsy[1],
                                  qt4.Qt.IgnoreAspectRatio,
                                  qt4.Qt.SmoothTransformation )

        # get position and size of output image
        xp, yp = coordsx[0], coordsy[1]
        xw = coordsx[1]-coordsx[0]
        yw = coordsy[0]-coordsy[1]

        # invert output drawing if axes go from positive->negative
        # we only translate the coordinate system if this is the case
        xscale = yscale = 1
        if xw < 0:
            xscale = -1
        if yw < 0:
            yscale = -1
        if xscale != 1 or yscale != 1:
            painter.save()
            painter.translate(xp, yp)
            xp = yp = 0
            painter.scale(xscale, yscale)

        # draw image
        painter.drawImage(qt4.QRectF(xp, yp, abs(xw), abs(yw)), image)

        # restore painter if image was inverted
        if xscale != 1 or yscale != 1:
            painter.restore()

# allow the factory to instantiate an image
document.thefactory.register( Image )
