from CeusMcTool2d.ceusAnalysis_ui import *
from CeusMcTool2d.exportData_ui_helper import *

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class CeusAnalysisGUI(Ui_ceusAnalysis, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.mcResultsBmode = None
        self.mcResultsCE = None
        self.curFrameIndex = None
        self.xCur = None
        self.yCur = None
        self.x = None
        self.y = None
        self.sliceArray = None
        self.lastGui = None
        self.x0_bmode = None
        self.y0_bmode = None
        self.w_bmode = None
        self.h_bmode = None
        self.x0_CE = None
        self.y0_CE = None
        self.w_CE = None
        self.h_CE = None
        self.dataFrame = None
        self.exportDataGUI = None
        self.auc = None
        self.pe = None
        self.tp = None
        self.mtt = None
        self.tmppv = None
        self.roiArea = None
        self.newData = None
        self.ticParamap = None

        self.bmodeCoverPixmap = QPixmap(381, 351)
        self.bmodeCoverPixmap.fill(Qt.transparent)
        self.bmodeCoverLabel.setPixmap(self.bmodeCoverPixmap)
        self.ceCoverPixmap = QPixmap(381, 351)
        self.ceCoverPixmap.fill(Qt.transparent)
        self.ceCoverLabel.setPixmap(self.ceCoverPixmap)

        self.setMouseTracking(True)

        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)
        self.backButton.clicked.connect(self.backToLastScreen)
        self.exportDataButton.clicked.connect(self.moveToExport)
        self.saveDataButton.clicked.connect(self.saveData)

    def moveToExport(self):
        if len(self.dataFrame):
            del self.exportDataGUI
            self.exportDataGUI = ExportDataGUI()
            self.exportDataGUI.dataFrame = self.dataFrame
            self.exportDataGUI.lastGui = self
            self.exportDataGUI.setFilenameDisplays(self.imagePathInput.text())
            self.exportDataGUI.show()
            self.hide()

    def saveData(self):
        if self.newData is None:
            self.newData = {"Patient": self.imagePathInput.text(), "Area Under Curve (AUC)": self.auc, \
                            "Peak Enhancement (PE)": self.pe, "Time to Peak (TP)": self.tp, \
                            "Mean Transit Time (MTT)": self.mtt, "TMPPV": self.tmppv, "ROI Area (mm^2)": self.roiArea}
            self.dataFrame = self.dataFrame.append(self.newData, ignore_index=True)


    def backToLastScreen(self):
        self.lastGui.dataFrame = self.dataFrame
        self.lastGui.show()
        self.hide()

    def updateBmode(self):
        self.mcDataBmode = np.require(self.mcResultsBmode[self.curFrameIndex], np.uint8, 'C')
        self.bytesLineMc, _ = self.mcDataBmode[:,:,0].strides
        self.qImgMcBmode = QImage(self.mcDataBmode, self.x, self.y, self.bytesLineMc, QImage.Format_RGB888)
        self.mcBmodeDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMcBmode).scaled(381, 351))
    
    def updateCE(self):
        self.mcDataCE = np.require(self.mcResultsCE[self.curFrameIndex], np.uint8, 'C')
        self.bytesLineMc, _ = self.mcDataCE[:,:,0].strides
        self.qImgMcCE = QImage(self.mcDataCE, self.x, self.y, self.bytesLineMc, QImage.Format_RGB888)
        self.mcCeDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMcCE).scaled(381, 351))

    def setFilenameDisplays(self, imageName):
        self.imagePathInput.setHidden(False)
        
        imFile = imageName.split('/')[-1]

        self.imagePathInput.setText(imFile)
        self.inputTextPath = imageName

    def updateCrosshair(self):
        if self.xCur < 741 and self.xCur > 360 and self.yCur < 501 and self.yCur > 150:
            self.actualX = int((self.xCur - 361)*(self.h_bmode-1)/381)
            self.actualY = int((self.yCur - 151)*(self.w_bmode-1)/351)
            plotX = self.xCur - 361
        elif self.xCur < 1151 and self.xCur > 770 and self.yCur < 501 and self.yCur > 150:
            self.actualX = int((self.xCur-771)*(self.h_CE-1)/381)
            self.actualY = int((self.yCur-151)*(self.w_CE-1)/351)
            plotX = self.xCur - 771
        else:
            return
        
        plotY = self.yCur - 151

        self.bmodeCoverLabel.pixmap().fill(Qt.transparent)
        painter = QPainter(self.bmodeCoverLabel.pixmap())
        painter.setPen(Qt.yellow)
        bmodeVertLine = QLine(plotX, 0, plotX, 351)
        bmodeLatLine = QLine(0, plotY, 381, plotY)
        painter.drawLines([bmodeVertLine, bmodeLatLine])
        painter.end()
            
        self.ceCoverLabel.pixmap().fill(Qt.transparent)
        painter = QPainter(self.ceCoverLabel.pixmap())
        painter.setPen(Qt.yellow)
        ceVertLine = QLine(plotX, 0, plotX, 351)
        ceLatLine = QLine(0, plotY, 381, plotY)
        painter.drawLines([ceVertLine, ceLatLine])
        painter.end()
        self.update()

    def mousePressEvent(self,event):
        self.xCur = event.x()
        self.yCur = event.y()

    def mouseMoveEvent(self, event):
        self.xCur = event.x()
        self.yCur = event.y()
        self.updateCrosshair()

    def curSliceSpinBoxValueChanged(self):
        self.curFrameIndex = int(self.curSliceSpinBox.value())
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSecondLabel.setText(str(self.sliceArray[self.curFrameIndex]))
        self.updateBmode()
        self.updateCE()
        self.update()

    def curSliceSliderValueChanged(self):
        self.curFrameIndex = int(self.curSliceSlider.value())
        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.curSecondLabel.setText(str(self.sliceArray[self.curFrameIndex]))
        self.updateBmode()
        self.updateCE()
        self.update()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = CeusAnalysisGUI()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())