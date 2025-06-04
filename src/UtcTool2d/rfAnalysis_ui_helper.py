import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import pyqtgraph as pg
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QWidget, QHBoxLayout

from pyquantus.utc import UtcData
from src.UtcTool2d.rfAnalysis_ui import Ui_rfAnalysis
from src.UtcTool2d.exportData_ui_helper import ExportDataGUI
import src.UtcTool2d.analysisParamsSelection_ui_helper as AnalysisParamsSelection
from src.UtcTool2d.psGraphDisplay_ui_helper import PsGraphDisplay
from src.UtcTool2d.saveConfig_ui_helper import SaveConfigGUI
from src.UtcTool2d.windowsTooLarge_ui_helper import WindowsTooLargeGUI


class RfAnalysisGUI(QWidget, Ui_rfAnalysis):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setLayout(self.fullScreenLayout)

        self.exportDataGUI = ExportDataGUI()
        self.lastGui: AnalysisParamsSelection.AnalysisParamsGUI
        self.utcData: UtcData
        self.frame: int
        self.newData = None
        self.psGraphDisplay = PsGraphDisplay()
        self.saveConfigGUI = SaveConfigGUI()
        self.windowsTooLargeGUI = WindowsTooLargeGUI()
        self.selectedImage: np.ndarray | None = None

        # Display B-Mode
        self.horizontalLayout = QHBoxLayout(self.imDisplayFrame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.horizontalLayout.addWidget(self.canvas)

        self.displayMbfButton.setCheckable(True)
        self.displaySiButton.setCheckable(True)
        self.displaySsButton.setCheckable(True)

        self.displayMbfButton.clicked.connect(self.mbfChecked)
        self.displaySsButton.clicked.connect(self.ssChecked)
        self.displaySiButton.clicked.connect(self.siChecked)

        # Prepare heatmap legend plot
        self.horizLayoutLeg = QHBoxLayout(self.legend)
        self.horizLayoutLeg.setObjectName("horizLayoutLeg")
        self.figLeg = plt.figure()
        self.legAx = self.figLeg.add_subplot(111)
        self.cax = self.figLeg.add_axes([0, 0.1, 0.35, 0.8])
        self.canvasLeg = FigureCanvas(self.figLeg)
        self.horizLayoutLeg.addWidget(self.canvasLeg)
        self.canvasLeg.draw()
        self.backButton.clicked.connect(self.backToLastScreen)
        self.exportDataButton.clicked.connect(self.moveToExport)
        self.displayNpsButton.clicked.connect(self.displayNps)
        self.displayNpsButton.setCheckable(True)
        self.saveConfigButton.clicked.connect(self.saveConfig)
        self.backToImgSelButton.clicked.connect(self.backToImgSelection)
        self.updateLegend("clear")
        
    def backToImgSelection(self):
        self.backToLastScreen()
        self.lastGui.backToLastScreen()
        self.lastGui.lastGui.backToSelectionScreen()
        self.lastGui.lastGui.lastGui.backToChoice()

    def saveConfig(self):
        self.saveConfigGUI.imName = self.imagePathInput.text()
        self.saveConfigGUI.phantomName = self.phantomPathInput.text()
        self.saveConfigGUI.config = self.utcData.utcAnalysis.config
        self.saveConfigGUI.show()

    def completeUtcAnalysis(self) -> int:
        if hasattr(self.utcData, 'scConfig'):
            self.utcData.utcAnalysis.splineToPreSc()
        self.utcData.utcAnalysis.generateRoiWindows()
        success = self.utcData.utcAnalysis.computeUtcWindows(extraParams=False)
        if success < 0:
            self.windowsTooLargeGUI.show()
            return -1
        self.utcData.drawCmaps()
        if hasattr(self.utcData, 'scConfig'):
            self.utcData.scanConvertCmaps()

        mbfMean = np.mean(self.utcData.mbfArr)
        ssMean = np.mean(np.array(self.utcData.ssArr))
        siMean = np.mean(self.utcData.siArr)
        self.avMbfVal.setText(f"{np.round(mbfMean, decimals=1)}")
        self.avSsVal.setText(f"{np.round(ssMean, decimals=2)}")
        self.avSiVal.setText(f"{np.round(siMean, decimals=1)}")

        npsArr = [window.results.nps for window in self.utcData.utcAnalysis.roiWindows]
        avNps = np.mean(npsArr, axis=0)
        f = self.utcData.utcAnalysis.roiWindows[0].results.f
        x = np.linspace(min(f), max(f), 100)
        y = ssMean*x/1e6 + siMean

        del self.psGraphDisplay
        self.psGraphDisplay = PsGraphDisplay()

        # ps = self.utcData.utcAnalysis.roiWindows[0].results.ps
        # rps = self.utcData.utcAnalysis.roiWindows[0].results.rPs
        # nps = self.utcData.utcAnalysis.roiWindows[0].results.nps
        # self.psGraphDisplay.plotGraph.plot(f/1e6, ps, pen=pg.mkPen(color="b"), name="PS")
        # self.psGraphDisplay.plotGraph.plot(f/1e6, rps, pen=pg.mkPen(color="r"), name="rPS")
        # self.psGraphDisplay.plotGraph.plot(f/1e6, nps+np.amin(ps), pen=pg.mkPen(color="g"), name="NPS")

        for nps in npsArr:
            self.psGraphDisplay.plotGraph.plot(f/1e6, nps, pen=pg.mkPen(color=(0, 0, 255, 51)))
        self.psGraphDisplay.plotGraph.plot(f/1e6, avNps, pen=pg.mkPen(color="r", width=2))
        self.psGraphDisplay.plotGraph.plot(x/1e6, y, pen=pg.mkPen(color=(255, 172, 28), width=2))
        self.psGraphDisplay.plotGraph.plot(2*[self.utcData.analysisFreqBand[0]/1e6], [np.amin(npsArr), np.amax(npsArr)], 
                                            pen=pg.mkPen(color="m", width=2))
        self.psGraphDisplay.plotGraph.plot(2*[self.utcData.analysisFreqBand[1]/1e6], [np.amin(npsArr), np.amax(npsArr)], 
                                            pen=pg.mkPen(color="m", width=2))
        self.psGraphDisplay.plotGraph.setYRange(np.amin(npsArr), np.amax(npsArr))

        self.plotOnCanvas()
        return 0

    def displayNps(self):
        if self.displayNpsButton.isChecked():
            self.psGraphDisplay.show()
        else:
            self.psGraphDisplay.hide()

    def moveToExport(self):
        # if len(self.utcData.dataFrame):
        del self.exportDataGUI
        self.exportDataGUI = ExportDataGUI()
        curData = {
                "Patient": [self.imagePathInput.text()],
                "Phantom": [self.phantomPathInput.text()],
                "Midband Fit (MBF)": [np.mean(self.utcData.mbfArr)],
                "Spectral Slope (SS)": [np.mean(self.utcData.ssArr)],
                "Spectral Intercept (SI)": [np.mean(self.utcData.siArr)],
                "ROI Name": "",
                "Frame Number": [self.frame],
            }
        self.exportDataGUI.dataFrame = pd.DataFrame.from_dict(curData)
        self.exportDataGUI.lastGui = self
        self.exportDataGUI.setFilenameDisplays(
            self.imagePathInput.text(), self.phantomPathInput.text()
        )
        self.exportDataGUI.show()
        self.exportDataGUI.resize(self.size())
        self.hide()

    def backToLastScreen(self):
        self.psGraphDisplay.hide()
        del self.psGraphDisplay
        self.lastGui.utcData = self.utcData
        self.lastGui.show()
        self.lastGui.resize(self.size())
        self.hide()

    def setFilenameDisplays(self, imageName, phantomName):
        self.imagePathInput.setHidden(False)
        self.phantomPathInput.setHidden(False)
        self.imagePathInput.setText(imageName)
        self.phantomPathInput.setText(phantomName)

    def plotOnCanvas(self):  # Plot current image on GUI
        self.ax.clear()
        self.selectedImage = self.utcData.finalBmode if self.selectedImage is None else self.selectedImage
        quotient = self.utcData.depth / self.utcData.width
        self.ax.imshow(self.selectedImage, aspect=quotient*(self.selectedImage.shape[1]/self.selectedImage.shape[0]))
        self.figure.set_facecolor((0, 0, 0, 0))
        self.ax.axis("off")

        self.ax.plot(
            self.utcData.splineX,
            self.utcData.splineY,
            color="cyan",
            zorder=1,
            linewidth=0.75,
        )
        self.figure.subplots_adjust(
            left=0, right=1, bottom=0, top=1, hspace=0.2, wspace=0.2
        )
        self.cursor = matplotlib.widgets.Cursor(
            self.ax, color="gold", linewidth=0.4, useblit=True
        )
        self.cursor.set_active(False)
        plt.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
        self.canvas.draw()  # Refresh canvas

    def mbfChecked(self):
        if self.displayMbfButton.isChecked():
            if self.displaySsButton.isChecked() or self.displaySiButton.isChecked():
                self.displaySsButton.setChecked(False)
                self.displaySiButton.setChecked(False)
            self.selectedImage = self.utcData.finalMbfIm
            self.updateLegend("MBF")
        else:
            self.selectedImage = self.utcData.finalBmode
            self.updateLegend("clear")
        self.plotOnCanvas()
        
    def ssChecked(self):
        if self.displaySsButton.isChecked():
            if self.displayMbfButton.isChecked() or self.displaySiButton.isChecked():
                self.displayMbfButton.setChecked(False)
                self.displaySiButton.setChecked(False)
            self.selectedImage = self.utcData.finalSsIm
            self.updateLegend("SS")
        else:
            self.selectedImage = self.utcData.finalBmode
            self.updateLegend("clear")
        self.plotOnCanvas()
        
    def siChecked(self):
        global curDisp
        if self.displaySiButton.isChecked():
            if self.displayMbfButton.isChecked() or self.displaySsButton.isChecked():
                self.displayMbfButton.setChecked(False)
                self.displaySsButton.setChecked(False)
            self.selectedImage = self.utcData.finalSiIm
            self.updateLegend("SI")
        else:
            self.selectedImage = self.utcData.finalBmode
            self.updateLegend("clear")
        self.plotOnCanvas()

    def updateLegend(self, curDisp):
        self.legAx.clear()
        self.figLeg.set_visible(True)
        a = np.array([[0, 1]])
        if curDisp == "" or curDisp == "clear":
            self.figLeg.set_visible(False)
            self.canvasLeg.draw()
            return
        elif curDisp == "MBF":
            img = self.legAx.imshow(a, cmap="viridis")
            self.legAx.set_visible(False)
            self.figLeg.colorbar(
                orientation="vertical", cax=self.cax, mappable=img
            )
            self.legAx.text(2.1, 0.21, "Midband Fit", rotation=270, size=9)
            minVal = self.utcData.minMbf
            maxVal = self.utcData.maxMbf
        elif curDisp == "SS":
            img = self.legAx.imshow(a, cmap="magma")
            self.legAx.set_visible(False)
            self.figLeg.colorbar(orientation="vertical", cax=self.cax, mappable=img)
            self.legAx.text(2.2, 0, "Spectral Slope (1e-6)", rotation=270, size=6)
            self.legAx.tick_params("y", labelsize=7, pad=0.7)
            minVal = self.utcData.minSs
            maxVal = self.utcData.maxSs
        elif curDisp == "SI":
            img = self.legAx.imshow(a, cmap="plasma")
            self.legAx.set_visible(False)
            self.figLeg.colorbar(orientation="vertical", cax=self.cax, mappable=img)
            self.legAx.text(2.2, 0.09, "Spectral Intercept", rotation=270, size=6)
            self.legAx.tick_params("y", labelsize=7, pad=0.7)
            minVal = self.utcData.minSi
            maxVal = self.utcData.maxSi
        else:
            raise ValueError("Invalid value for curDisp")
            
        self.legAx.tick_params("y", labelsize=7, pad=0.5)
        self.cax.set_yticks([0, 0.25, 0.5, 0.75, 1])
        self.cax.set_yticklabels(
            [
                np.round(minVal, 1),
                np.round(
                    ((maxVal - minVal) / 4)
                    + minVal,
                    1,
                ),
                np.round(
                    ((maxVal - minVal) / 2)
                    + minVal,
                    1,
                ),
                np.round(
                    (3 * (maxVal - minVal) / 4)
                    + minVal,
                    1,
                ),
                np.round(maxVal, 1),
            ]
        )
        self.figLeg.set_facecolor((1, 1, 1, 1))
        self.canvasLeg.draw()