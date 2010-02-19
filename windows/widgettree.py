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
###############################################################################

# $Id$

"""Contains a model and view for handling a tree of widgets."""

import veusz.qtall as qt4

import veusz.utils as utils
import veusz.document as document

class WidgetTreeModel(qt4.QAbstractItemModel):
    """A model representing the widget tree structure.
    """

    def __init__(self, document, parent=None):
        """Initialise using document."""
        
        qt4.QAbstractItemModel.__init__(self, parent)

        self.document = document

        self.connect( self.document, qt4.SIGNAL("sigModified"),
                      self.slotDocumentModified )
        self.connect( self.document, qt4.SIGNAL("sigWiped"),
                      self.slotDocumentModified )

        # suspend signals to the view that the model has changed
        self.suspendmodified = False

    def slotDocumentModified(self):
        """The document has been changed."""
        if not self.suspendmodified:
            # needs to be suspended within insert/delete row operations
            self.emit( qt4.SIGNAL('layoutChanged()') )

    def columnCount(self, parent):
        """Return number of columns of data."""
        return 2

    def data(self, index, role):
        """Return data for the index given."""

        # why do we get passed invalid indicies? :-)
        if not index.isValid():
            return qt4.QVariant()

        column = index.column()
        obj = index.internalPointer()

        if role == qt4.Qt.DisplayRole:
            # return text for columns
            if column == 0:
                return qt4.QVariant(obj.name)
            elif column == 1:
                return qt4.QVariant(obj.typename)

        elif role == qt4.Qt.DecorationRole:
            # return icon for first column
            if column == 0:
                filename = 'button_%s' % obj.typename
                return qt4.QVariant(utils.getIcon(filename))

        elif role == qt4.Qt.ToolTipRole:
            # provide tool tip showing description
            if obj.userdescription:
                return qt4.QVariant(obj.userdescription)

        elif role == qt4.Qt.TextColorRole:
            # show disabled looking text if object or any parent is hidden
            hidden = False
            p = obj
            while p is not None:
                if 'hide' in p.settings and p.settings.hide:
                    hidden = True
                    break
                p = p.parent

            # return brush for hidden widget text, based on disabled text
            if hidden:
                return qt4.QVariant(qt4.QPalette().brush(qt4.QPalette.Disabled,
                                                         qt4.QPalette.Text))

        # return nothing
        return qt4.QVariant()

    def setData(self, index, value, role):
        """User renames object. This renames the widget."""
        
        widget = index.internalPointer()
        name = unicode(value.toString())

        # check symbols in name
        if not utils.validateWidgetName(name):
            return False
        
        # check name not already used
        if widget.parent.hasChild(name):
            return False

        # actually rename the widget
        self.document.applyOperation(
            document.OperationWidgetRename(widget, name))

        self.emit( qt4.SIGNAL(
                'dataChanged(const QModelIndex &, const QModelIndex &)'),
                   index, index )
        return True
            
    def flags(self, index):
        """What we can do with the item."""
        
        if not index.isValid():
            return qt4.Qt.ItemIsEnabled

        flags = ( qt4.Qt.ItemIsEnabled | qt4.Qt.ItemIsSelectable |
                  qt4.Qt.ItemIsDropEnabled )
        if ( index.internalPointer() is not self.document.basewidget and
             index.column() == 0 ):
            # allow items other than root to be edited and dragged
            flags |= qt4.Qt.ItemIsEditable | qt4.Qt.ItemIsDragEnabled

        return flags

    def headerData(self, section, orientation, role):
        """Return the header of the tree."""
        
        if orientation == qt4.Qt.Horizontal and role == qt4.Qt.DisplayRole:
            val = ('Name', 'Type')[section]
            return qt4.QVariant(val)

        return qt4.QVariant()

    def _getChildren(self, parent):
        """Get a list of children for the parent given (None selects root)."""

        if parent is None:
            return [self.document.basewidget]
        else:
            return parent.children

    def index(self, row, column, parent):
        """Construct an index for a child of parent."""

        if not parent.isValid():
            parentobj = None
        else:
            parentobj = parent.internalPointer()

        children = self._getChildren(parentobj)

        try:
            c = children[row]
        except IndexError:
            # sometimes this function gets called with an invalid row
            # when deleting, so we return an error result
            return qt4.QModelIndex()

        return self.createIndex(row, column, c)

    def getWidgetIndex(self, widget):
        """Returns index for widget specified."""

        # walk index tree back to widget from root
        widgetlist = []
        w = widget
        while w is not None:
            widgetlist.append(w)
            w = w.parent

        # now iteratively look up indices
        parent = qt4.QModelIndex()
        while widgetlist:
            w = widgetlist.pop()
            row = self._getChildren(w.parent).index(w)
            parent = self.index(row, 0, parent)

        return parent
    
    def parent(self, index):
        """Find the parent of the index given."""

        if not index.isValid():
            return qt4.QModelIndex()

        thisobj = index.internalPointer()
        parentobj = thisobj.parent

        if parentobj is None:
            return qt4.QModelIndex()
        else:
            # lookup parent in grandparent's children
            grandparentchildren = self._getChildren(parentobj.parent)
            try:
                parentrow = grandparentchildren.index(parentobj)
            except ValueError:
                return qt4.QModelIndex()

            return self.createIndex(parentrow, 0, parentobj)

    def rowCount(self, parent):
        """Return number of rows of children."""

        if not parent.isValid():
            parentobj = None
        else:
            parentobj = parent.internalPointer()

        children = self._getChildren(parentobj)
        return len(children)

    def getSettings(self, index):
        """Return the settings for the index selected."""
        obj = index.internalPointer()
        return obj.settings

    def getWidget(self, index):
        """Get associated widget for index selected."""
        return index.internalPointer()

    def removeRows(self, row, count, parentindex):
        """Remove widgets from parent."""

        if not parentindex.isValid():
            return

        parent = self.getWidget(parentindex)
        self.suspendmodified = True
        self.beginRemoveRows(parentindex, row, row+count-1)

        # construct an operation for deleting the rows
        deleteops = []
        for w in parent.children[row:row+count]:
            deleteops.append( document.OperationWidgetDelete(w) )
        op = document.OperationMultiple(deleteops, descr="remove widget(s)")
        self.document.applyOperation(op)

        self.endRemoveRows()
        self.suspendmodified = False
        return True

    def supportedDropActions(self):
        """Supported drag and drop actions."""
        return qt4.Qt.MoveAction | qt4.Qt.CopyAction

    def mimeData(self, indexes):
        """Get mime data for indexes."""
        widgets = [idx.internalPointer() for idx in indexes]
        return document.generateWidgetsMime(widgets)

    def mimeTypes(self):
        """Accepted mime types."""
        return [document.widgetmime]

    def dropMimeData(self, mimedata, action, row, column, parentindex):
        """User drags and drops widget."""

        if action == qt4.Qt.IgnoreAction:
            return True
        if not mimedata.hasFormat(document.widgetmime):
            return False

        data = str(mimedata.data(document.widgetmime))
        if parentindex.isValid():
            parent = self.getWidget(parentindex)
        else:
            parent = self.document.basewidget

        # check parent supports child
        if not document.isMimeDropable(parent, data):
            return False

        # work out where row will be pasted
        startrow = row
        if row == -1:
            startrow = len(parent.children)

        # need to tell qt that these rows are being inserted, so that the
        # right number of rows are removed afterwards
        self.suspendmodified = True
        self.beginInsertRows(parentindex, startrow,
                             startrow+document.getMimeWidgetCount(data)-1)
        document.pasteMime(parent, data, index=startrow)
        self.endInsertRows()
        self.suspendmodified = False

        return True

class WidgetTreeView(qt4.QTreeView):
    """A model view for viewing the widgets."""

    def __init__(self, model, *args):
        qt4.QTreeView.__init__(self, *args)
        self.setModel(model)
        self.expandAll()

        # stretch header
        hdr = self.header()
        hdr.setStretchLastSection(False)
        hdr.setResizeMode(0, qt4.QHeaderView.Stretch)
        hdr.setResizeMode(1, qt4.QHeaderView.Custom)

        # setup drag and drop
        self.setSelectionMode(qt4.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        
    def testModifier(self, e):
        """Look for keyboard modifier for copy or move."""
        if e.keyboardModifiers() & qt4.Qt.ControlModifier:
            e.setDropAction(qt4.Qt.CopyAction)
        else:
            e.setDropAction(qt4.Qt.MoveAction)

    def handleInternalMove(self, event):
        """Handle a move inside treeview."""

        # make sure qt doesn't handle this
        event.setDropAction(qt4.Qt.IgnoreAction)
        event.ignore()

        if not self.viewport().rect().contains(event.pos()):
            return

        # get widget at event position
        index = self.indexAt(event.pos())
        if not index.isValid():
            index = self.rootIndex()

        # adjust according to drop indicator position
        row = -1
        posn = self.dropIndicatorPosition()
        if posn == qt4.QAbstractItemView.AboveItem:
            row = index.row()
            index = index.parent()
        elif posn == qt4.QAbstractItemView.BelowItem:
            row = index.row() + 1
            index = index.parent()

        if index.isValid():
            parent = self.model().getWidget(index)
            data = str(event.mimeData().data(document.widgetmime))
            if document.isMimeDropable(parent, data):
                # move the widget!
                parentpath = parent.path
                widgetpaths = document.getMimeWidgetPaths(data)
                ops = []
                r = row
                for path in widgetpaths:
                    ops.append(
                        document.OperationWidgetMove(path, parentpath, r) )
                    if r >= 0:
                        r += 1

                self.model().document.applyOperation(
                    document.OperationMultiple(ops, descr='move'))
                event.ignore()

    def dropEvent(self, e):
        """When an object is dropped on the view."""
        self.testModifier(e)

        if e.source() is self and e.dropAction() == qt4.Qt.MoveAction:
            self.handleInternalMove(e)

        qt4.QTreeView.dropEvent(self, e)

    def dragMoveEvent(self, e):
        """Make items move by default and copy if Ctrl is held down."""
        self.testModifier(e)

        qt4.QTreeView.dragMoveEvent(self, e)

