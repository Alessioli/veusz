# __init__.py file for utils
  
#    Copyright (C) 2004 Jeremy S. Sanders
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

# $Id$

from utilfuncs import *
from textrender import *
from points import *
from version import *
from fitlm import *
from action import *
from pdf import *
from dates import *
from safe_eval import veusz_eval_context, checkCode

try:
    from veusz.helpers.qtloops import addNumpyToPolygonF, plotPathsToPainter, plotLinesToPainter
except ImportError:
    print "Warning: Using slow substitutes for some functions"
    print "Compile helpers to avoid this warning"
    from slowfuncs import addNumpyToPolygonF, plotPathsToPainter, plotLinesToPainter
