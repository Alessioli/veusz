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

import os.path

import veusz.qtall as qt4
import veusz.setting as setting
import veusz.utils as utils
import veusz.document as document
from veusz.setting.controls import populateCombo

import dataeditdialog

import numpy as N

def checkValidator(combo):
    """Is this validator ok?"""
    valid = combo.validator()
    state, x = valid.validate( combo.currentText(), 0 )
    return state == qt4.QValidator.Acceptable

class ManualBinModel(qt4.QAbstractListModel):
    """Model to store a list of floating point values in a list."""
    def __init__(self, data):
        qt4.QAbstractListModel.__init__(self)
        self.data = data
    def data(self, index, role):
        if role == qt4.Qt.DisplayRole and index.isValid():
            return qt4.QVariant(float(self.data[index.row()]))
        return qt4.QVariant()
    def rowCount(self, parent):
        return len(self.data)
    def flags(self, index):
        return ( qt4.Qt.ItemIsSelectable | qt4.Qt.ItemIsEnabled |
                 qt4.Qt.ItemIsEditable )
    def setData(self, index, value, role):
        if role == qt4.Qt.EditRole:
            val, ok = value.toDouble()
            if ok:
                self.data[ index.row() ] = val
                self.emit( qt4.SIGNAL("dataChanged(const QModelIndex &,"
                                      " const QModelIndex &)"), index, index)
                return True
        return False

class HistoDataDialog(qt4.QDialog):
    """Preferences dialog."""

    def __init__(self, parent, document):
        """Setup dialog."""
        qt4.QDialog.__init__(self, parent)
        qt4.loadUi(os.path.join(utils.veuszDirectory, 'dialogs',
                                'histodata.ui'),
                   self)

        self.document = document

        self.minval.default = self.maxval.default = ['Auto']
        regexp = qt4.QRegExp("^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?|Auto$")
        validator = qt4.QRegExpValidator(regexp, self)
        self.minval.setValidator(validator)
        self.maxval.setValidator(validator)
        self.connect( self.buttonBox.button(qt4.QDialogButtonBox.Apply),
                      qt4.SIGNAL("clicked()"), self.applyClicked )
        self.connect( self.buttonBox.button(qt4.QDialogButtonBox.Reset),
                      qt4.SIGNAL('clicked()'), self.resetClicked )
        self.connect( self.bingenerate, qt4.SIGNAL('clicked()'),
                      self.generateManualBins )
        self.connect( self.binadd, qt4.SIGNAL('clicked()'), self.addManualBins )
        self.connect( self.binremove, qt4.SIGNAL('clicked()'),
                      self.removeManualBins )


        self.bindata = []
        self.binmodel = ManualBinModel(self.bindata)
        self.binmanuals.setModel(self.binmodel)

        self.connect(document, qt4.SIGNAL("sigModified"),
                     self.updateDatasetLists)
        self.updateDatasetLists()

    def escapeDatasets(self, dsnames):
        """Escape dataset names if they are not typical python ones."""

        for i in xrange(len(dsnames)):
            if not utils.validPythonIdentifier(dsnames[i]):
                dsnames[i] = '`%s`' % dsnames[i]

    def updateDatasetLists(self):
        """Update list of datasets."""

        datasets = []
        for name, ds in self.document.data.iteritems():
            if ds.datatype == 'numeric' and ds.dimensions == 1:
                datasets.append(name)
        datasets.sort()

        # make sure names are escaped if they have funny characters
        self.escapeDatasets(datasets)

        # help the user by listing existing datasets
        populateCombo(self.indataset, datasets)

    def datasetExprChanged(self):
        """Validate expression."""
        text = self.indataset.text()
        res = document.simpleEvalExpression(self.document, unicode(text))
        print res

    class Params(object):
        """Parameters to creation of histogram."""

        def __init__(self, dialog):
            """Initialise parameters from dialog."""
            numbins = dialog.numbins.value()

            if not checkValidator(dialog.minval):
                raise RuntimeError("Invalid minimum value")
            minval = unicode( dialog.minval.text() )
            if minval != 'Auto':
                minval = float(minval)

            if not checkValidator(dialog.maxval):
                raise RuntimeError("Invalid maximum value")
            maxval = unicode( dialog.maxval.text() )
            if maxval != 'Auto':
                maxval = float(maxval)

            islog = dialog.logarithmic.isChecked()
            self.binparams = (numbins, minval, maxval, islog)

            self.expr = unicode( dialog.indataset.currentText() )
            self.outdataset = unicode( dialog.outdataset.currentText() )
            self.outbins = unicode( dialog.outbins.currentText() )
            self.method = unicode( dialog.methodGroup.getRadioChecked().
                                   objectName() )
            self.manualbins = list( dialog.bindata )
            self.manualbins.sort()
            if len(self.manualbins) == 0:
                self.manualbins = None

            self.errors = dialog.errorBars.isChecked()
            cuml = dialog.cumlGroup.getRadioChecked().objectName()
            self.cumulative = 'none'
            if cuml == 'cumlStoL':
                self.cumulative = 'smalltolarge'
            elif cuml == 'cumlLtoS':
                self.cumulative = 'largetosmall'

        def getGenerator(self, doc):
            """Return dataset generator."""
            return document.DatasetHistoGenerator(
                doc, self.expr, binparams = self.binparams,
                binmanual = self.manualbins, method = self.method,
                cumulative = self.cumulative, errors = self.errors)

        def getOperation(self):
            """Get operation to make histogram."""
            return document.OperationDatasetHistogram(
                self.expr, self.outbins, self.outdataset,
                binparams = self.binparams,
                binmanual = self.manualbins,
                method = self.method,
                cumulative = self.cumulative,
                errors = self.errors)

    def generateManualBins(self):
        """Generate manual bins."""

        try:
            p = HistoDataDialog.Params(self)
        except RuntimeError, ex:
            qt4.QMessageBox.warning(self, "Invalid parameters", unicode(ex))
            return

        if p.expr != '':
            p.manualbins = []
            gen = p.getGenerator(self.document)
            self.bindata[:] = list(gen.binLocations())
        else:
            del self.bindata[:]
        self.binmodel.reset()

    def addManualBins(self):
        """Add an extra bin to the manual list."""
        self.bindata.insert(0, 0.)
        self.binmodel.reset()

    def removeManualBins(self):
        """Remove selected bins."""
        indexes = self.binmanuals.selectionModel().selectedIndexes()
        if indexes:
            del self.bindata[ indexes[0].row() ]
            self.binmodel.reset()

    def resetClicked(self):
        """Reset button clicked."""

        for cntrl in (self.indataset, self.outdataset, self.outbins):
            cntrl.setEditText("")

        self.numbins.setValue(10)
        self.minval.setEditText("Auto")
        self.maxval.setEditText("Auto")
        self.logarithmic.setChecked(False)

        del self.bindata[:]
        self.binmodel.reset()

        self.errorBars.setChecked(False)
        self.counts.click()
        self.cumlOff.click()

    def reEditDataset(self, dsname):
        """Re-edit dataset."""

        try:
            ds = self.document.data[dsname]
        except KeyError:
            return
        gen = ds.generator

        self.indataset.setEditText(gen.inexpr)

        # need to map backwards to get dataset names
        revds = dict( (a,b) for b,a in self.document.data.iteritems() )
        self.outdataset.setEditText( revds[gen.valuedataset] )
        self.outbins.setEditText( revds[gen.bindataset] )

        # if there are parameters
        if gen.binparams:
            p = gen.binparams
            self.numbins.setValue( p[0] )
            self.minval.setEditText( unicode(p[1]) )
            self.maxval.setEditText( unicode(p[2]) )
            self.logarithmic.setChecked( bool(p[3]) )
        else:
            self.numbins.setValue(10)
            self.minval.setEditText("Auto")
            self.maxval.setEditText("Auto")
            self.logarithmic.setChecked(False)

        # if there is a manual list of bins
        if gen.binmanual:
            self.bindata[:] = list(gen.binmanual)
            self.binmodel.reset()

        # select correct method
        {'counts': self.counts, 'density': self.density,
         'fractions': self.fractions}[gen.method].click()
        
        # select if cumulative
        {'none': self.cumlOff, 'smalltolarge': self.cumlStoL,
         'largetosmall': self.cumlLtoS}[gen.cumulative].click()

        # if error bars
        self.errorBars.setChecked( bool(gen.errors) )

    def applyClicked(self):
        """Create histogram."""

        def clearlabel(self=self):
            self.statuslabel.setText("")
        qt4.QTimer.singleShot(4000, clearlabel)

        try:
            p = HistoDataDialog.Params(self)
        except RuntimeError, ex:
            self.statuslabel.setText("Invalid parameters: %s" % unicode(ex))
            return

        exprresult = document.simpleEvalExpression(self.document, p.expr)
        if len(exprresult) == 0:
            self.statuslabel.setText("Invalid expression")
            return

        op = p.getOperation()
        self.document.applyOperation(op)

        self.statuslabel.setText(
            'Created datasets "%s" and "%s"' % (p.outbins, p.outdataset))

dataeditdialog.recreate_register[document.DatasetHistoValues] = HistoDataDialog
dataeditdialog.recreate_register[document.DatasetHistoBins] = HistoDataDialog
