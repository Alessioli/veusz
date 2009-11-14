#    Copyright (C) 2008 Jeremy S. Sanders
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

"""Veusz dialogs module."""

# insert history combo into the list of modules so that it can be found
# by loadUi - yuck
import sys
import historycombo
import historycheck
import historyvaluecombo
import recentfilesbutton

sys.modules['historycombo'] = historycombo
sys.modules['historycheck'] = historycheck
sys.modules['historyvaluecombo'] = historyvaluecombo
sys.modules['recentfilesbutton'] = recentfilesbutton
