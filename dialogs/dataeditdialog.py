# data editting dialog

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
##############################################################################

# $Id$

"""Module for implementing dialog box for viewing/editing data."""

import itertools
import os.path

import veusz.qtall as qt4

import veusz.document as document
import veusz.utils as utils

# register dialog type to recreate dataset
recreate_register = {}

class DatasetTableModel1D(qt4.QAbstractTableModel):
    """Provides access to editing and viewing of datasets."""

    def __init__(self, parent, document, datasetname):
        qt4.QAbstractTableModel.__init__(self, parent)

        self.document = document
        self.dsname = datasetname
        self.connect(document, qt4.SIGNAL('sigModified'),
                     self.slotDocumentModified)

    def rowCount(self, parent):
        """Return number of rows."""
        try:
            return len(self.document.data[self.dsname].data)
        except (KeyError, AttributeError):
            return 0
        
    def slotDocumentModified(self):
        """Called when document modified."""
        self.emit( qt4.SIGNAL('layoutChanged()') )

    def columnCount(self, parent):
        """Return number of columns."""
        try:
            ds = self.document.data[self.dsname]
        except KeyError:
            return 0
        return len( ds.column_descriptions )

    def data(self, index, role):
        """Return data associated with column given."""
        if role == qt4.Qt.DisplayRole:
            # select correct part of dataset
            ds = self.document.data[self.dsname]
            data = getattr(ds, ds.columns[index.column()])

            if data is not None:
                d = data[index.row()]
                if isinstance(d, basestring):
                    return qt4.QVariant(d)
                else:
                    # value needs converting to float as QVariant doesn't
                    # support numpy numeric types
                    return qt4.QVariant(float(d))

        # return nothing otherwise
        return qt4.QVariant()

    def headerData(self, section, orientation, role):
        """Return headers at top."""

        if role == qt4.Qt.DisplayRole:
            if orientation == qt4.Qt.Horizontal:
                try:
                    ds = self.document.data[self.dsname]
                except KeyError:
                    return qt4.QVariant()
                return qt4.QVariant( ds.column_descriptions[section] )
            else:
                # return row numbers
                return qt4.QVariant(section+1)

        return qt4.QVariant()
        
    def flags(self, index):
        """Update flags to say that items are editable."""
        
        if not index.isValid():
            return qt4.Qt.ItemIsEnabled
        else:
            return qt4.QAbstractTableModel.flags(self, index) | qt4.Qt.ItemIsEditable

    def removeRows(self, row, count):
        """Remove rows."""
        self.document.applyOperation(
            document.OperationDatasetDeleteRow(self.dsname, row, count))

    def insertRows(self, row, count):
        """Remove rows."""
        self.document.applyOperation(
            document.OperationDatasetInsertRow(self.dsname, row, count))

    def setData(self, index, value, role):
        """Called to set the data."""

        if index.isValid() and role == qt4.Qt.EditRole:
            row = index.row()
            column = index.column()
            ds = self.document.data[self.dsname]
            data = getattr(ds, ds.columns[index.column()])

            # add new column if necessary
            if data is None:
                self.document.applyOperation(
                    document.OperationDatasetAddColumn(self.dsname,
                                                       ds.columns[column]) )


            # update if conversion okay
            try:
                val = ds.convertToDataItem( value.toString() )
            except ValueError:
                return False
            
            op = document.OperationDatasetSetVal(self.dsname,
                                                 ds.columns[column],
                                                 row, val)
            self.document.applyOperation(op)
            return True

        else:
            return False

class DatasetTableModel2D(qt4.QAbstractTableModel):
    """A 2D dataset model."""

    def __init__(self, parent, document, datasetname):
        qt4.QAbstractTableModel.__init__(self, parent)

        self.document = document
        self.dsname = datasetname

    def rowCount(self, parent):
        ds = self.document.data[self.dsname].data
        if ds is not None:
            return ds.shape[0]
        else:
            return 0

    def columnCount(self, parent):
        ds = self.document.data[self.dsname].data
        if ds is not None:
            return ds.shape[1]
        else:
            return 0

    def data(self, index, role):
        if role == qt4.Qt.DisplayRole:
            # get data (note y is reversed, sigh)
            ds = self.document.data[self.dsname].data
            if ds is not None:
                num = ds[ds.shape[0]-index.row()-1, index.column()]
                return qt4.QVariant( float(num) )

        return qt4.QVariant()

    def headerData(self, section, orientation, role):
        """Return headers at top."""

        if role == qt4.Qt.DisplayRole:
            ds = self.document.data[self.dsname]

            if ds is not None:
                # return a number for the top left of the cell
                if orientation == qt4.Qt.Horizontal:
                    r = ds.xrange
                    num = ds.data.shape[1]
                else:
                    r = ds.yrange
                    r = (r[1], r[0]) # swap (as y reversed)
                    num = ds.data.shape[0]
                val = (r[1]-r[0])/num*(section+0.5)+r[0]
                return qt4.QVariant( '%g' % val )

        return qt4.QVariant()

class DatasetListModel(qt4.QAbstractListModel):
    """A model to allow the list of datasets to be viewed."""

    def __init__(self, parent, document):
        qt4.QAbstractListModel.__init__(self, parent)
        self.document = document

        self.connect(document, qt4.SIGNAL('sigModified'),
                     self.slotDocumentModified)

        # initial variable state
        self._changeset = -1

    def _getDSList(self):
        """A cached copy of a list of datasets, which updates if doc changes."""
        if self._changeset != self.document.changeset:
            self._changeset = self.document.changeset
            self._realDSList = self.document.data.keys()
            self._realDSList.sort()
        return self._realDSList
    datasets = property(_getDSList)

    def slotDocumentModified(self):
        """Called when document modified."""
        self.emit( qt4.SIGNAL('layoutChanged()') )

    def rowCount(self, parent):
        return len(self.datasets)

    def datasetName(self, index):
        return self.datasets[index.row()]

    def data(self, index, role):
        try:
            if role == qt4.Qt.DisplayRole:
                return qt4.QVariant(self.datasets[index.row()])
        except IndexError:
            pass

        # return nothing otherwise
        return qt4.QVariant()

    def flags(self, index):
        """Return flags for items."""
        if not index.isValid():
            return qt4.Qt.ItemIsEnabled
        
        return qt4.QAbstractListModel.flags(self, index) | qt4.Qt.ItemIsEditable

    def setData(self, index, value, role):
        """Called to rename a dataset."""

        if index.isValid() and role == qt4.Qt.EditRole:
            name = self.datasetName(index)
            newname = unicode( value.toString() )
            if not utils.validateDatasetName(newname):
                return False

            self.datasets[index.row()] = newname
            self.emit(qt4.SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &'),
                      index, index)

            self.document.applyOperation(document.OperationDatasetRename(name, newname))
            return True

        return False
    
class DataEditDialog(qt4.QDialog):
    """Dialog for editing and rearranging data sets."""
    
    def __init__(self, parent, document, *args):

        # load up UI
        qt4.QDialog.__init__(self, parent, *args)
        qt4.loadUi(os.path.join(utils.veuszDirectory, 'dialogs',
                                'dataedit.ui'),
                   self)
        self.document = document

        # set up dataset list
        self.dslistmodel = DatasetListModel(self, document)
        self.datasetlistview.setModel(self.dslistmodel)

        # actions for data table
        for text, slot in (
            ('Copy', self.slotCopy),
            ('Delete row', self.slotDeleteRow),
            ('Insert row', self.slotInsertRow),
            ):
            act = qt4.QAction(text, self)
            self.connect(act, qt4.SIGNAL('triggered()'), slot)
            self.datatableview.addAction(act)
        self.datatableview.setContextMenuPolicy( qt4.Qt.ActionsContextMenu )

        # layout edit dialog improvement
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)

        # don't want text to look editable or special
        self.linkedlabel.setFrameShape(qt4.QFrame.NoFrame)
        self.linkedlabel.viewport().setBackgroundRole(qt4.QPalette.Window)

        # document changes
        self.connect(document, qt4.SIGNAL('sigModified'),
                     self.slotDocumentModified)

        # receive change in selection
        self.connect(self.datasetlistview.selectionModel(),
                     qt4.SIGNAL('selectionChanged(const QItemSelection &, const QItemSelection &)'),
                     self.slotDatasetSelected)

        # select first item (phew)
        if self.dslistmodel.rowCount(None) > 0:
            self.datasetlistview.selectionModel().select(
                self.dslistmodel.createIndex(0, 0),
                qt4.QItemSelectionModel.Select)

        # connect buttons
        self.connect(self.deletebutton, qt4.SIGNAL('clicked()'),
                     self.slotDatasetDelete)
        self.connect(self.unlinkbutton, qt4.SIGNAL('clicked()'),
                     self.slotDatasetUnlink)
        self.connect(self.duplicatebutton, qt4.SIGNAL('clicked()'),
                     self.slotDatasetDuplicate)
        self.connect(self.importbutton, qt4.SIGNAL('clicked()'),
                     self.slotDatasetImport)
        self.connect(self.createbutton, qt4.SIGNAL('clicked()'),
                     self.slotDatasetCreate)
        self.connect(self.editbutton, qt4.SIGNAL('clicked()'),
                     self.slotDatasetEdit)

    def slotDatasetSelected(self, current, deselected):
        """Called when a new dataset is selected."""

        # FIXME: Make readonly models readonly!!
        index = current.indexes()[0]
        name = self.dslistmodel.datasetName(index)
        ds = self.document.data[name]

        if ds.dimensions == 1:
            model = DatasetTableModel1D(self, self.document, name)
        elif ds.dimensions == 2:
            model = DatasetTableModel2D(self, self.document, name)

        self.datatableview.setModel(model)
            
        self.setUnlinkState()

    def setUnlinkState(self):
        """Enable the unlink button correctly."""
        # get dataset
        dsname = self.getSelectedDataset()

        try:
            ds = self.document.data[dsname]
        except KeyError:
            return

        # linked dataset
        unlink = ds.canUnlink()
        readonly = not unlink

        self.editbutton.setVisible(type(ds) in recreate_register)
        self.unlinkbutton.setEnabled(unlink)
        self.linkedlabel.setText( ds.linkedInformation() )

    def slotDocumentModified(self):
        """Set unlink status when document modified."""
        self.setUnlinkState()

    def getSelectedDataset(self):
        """Return the selected dataset."""
        selitems = self.datasetlistview.selectionModel().selection().indexes()
        if len(selitems) != 0:
            return self.dslistmodel.datasetName(selitems[0])
        else:
            return None
        
    def slotDatasetDelete(self):
        """Delete selected dataset."""

        datasetname = self.getSelectedDataset()
        if datasetname is not None:
            row = self.datasetlistview.selectionModel(
                ).selection().indexes()[0].row()

            self.document.applyOperation(
                document.OperationDatasetDelete(datasetname))

            # select new item in list
            model = self.datasetlistview.model()
            row = min(model.rowCount(None)-1, row)
            if row >= 0:
                # select new row
                newindex = model.index(row)
                self.datasetlistview.selectionModel().select(
                    newindex, qt4.QItemSelectionModel.ClearAndSelect)
                self.slotDatasetSelected(
                    self.datasetlistview.selectionModel().selection(), None)
            else:
                # clear model
                self.datatableview.setModel(None)

    def slotDatasetUnlink(self):
        """Allow user to remove link to file or other datasets."""

        datasetname = self.getSelectedDataset()
        if datasetname is not None:
            d = self.document.data[datasetname]
            if d.linked is not None:
                op = document.OperationDatasetUnlinkFile(datasetname)
            else:
                op = document.OperationDatasetUnlinkRelation(datasetname)
            self.document.applyOperation(op)

    def slotDatasetDuplicate(self):
        """Duplicate selected dataset."""
        
        datasetname = self.getSelectedDataset()
        if datasetname is not None:
            # generate new name for dataset
            newname = datasetname + '_copy'
            index = 2
            while newname in self.document.data:
                newname = '%s_copy_%i' % (datasetname, index)
                index += 1

            self.document.applyOperation(
                document.OperationDatasetDuplicate(datasetname, newname))

    def slotDatasetImport(self):
        """Show import dialog."""
        self.parent().slotDataImport()

    def slotDatasetCreate(self):
        """Show dataset creation dialog."""
        self.parent().slotDataCreate()

    def slotDatasetEdit(self):
        """Reload dataset into dataset create dialog."""
        dsname = unicode(self.getSelectedDataset())
        if dsname:
            dataset = self.document.data[dsname]
            dialog = recreate_register[type(dataset)](self.parent(),
                                                      self.document)
            self.parent().showDialog(dialog)
            dialog.reEditDataset(dsname)

    def slotCopy(self):
        """Copy text from selection."""
        # get list of selected rows and columns
        selmodel = self.datatableview.selectionModel()
        model = self.datatableview.model()
        indices = []
        for index in selmodel.selectedIndexes():
            indices.append( (index.row(), index.column()) )
        indices.sort()

        # build up text stream for copying to clipboard
        lines = []
        rowitems = []
        lastrow = -1
        for row, column in indices:
            if row != lastrow:
                if rowitems:
                    # items are tab separated
                    lines.append( '\t'.join(rowitems) )
                    rowitems = []
                lastrow = row
            rowitems.append( unicode(
                model.createIndex(row, column).data().toString()) )
        if rowitems:
            lines.append( '\t'.join(rowitems) )
        lines.append('')  # blank line at end
        lines = '\n'.join(lines)

        # put text on clipboard
        qt4.QApplication.clipboard().setText(lines)

    def slotDeleteRow(self):
        """Delete the current row."""
        self.datatableview.model().removeRows(
            self.datatableview.currentIndex().row(), 1)

    def slotInsertRow(self):
        """Insert a new row."""
        self.datatableview.model().insertRows(
            self.datatableview.currentIndex().row(), 1)
