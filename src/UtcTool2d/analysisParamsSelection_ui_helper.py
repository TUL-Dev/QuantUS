import numpy as np
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QImage, QPixmap

from pyquantus.utc import UtcData
from src.UtcTool2d.analysisParamsSelection_ui import Ui_analysisParams
from src.UtcTool2d.rfAnalysis_ui_helper import RfAnalysisGUI
from src.UtcTool2d.loadConfig_ui_helper import LoadConfigGUI

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.UtcTool2d.roiSelection_ui_helper import RoiSelectionGUI


class AnalysisParamsGUI(Ui_analysisParams, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setLayout(self.fullScreenLayout)

        self.rfAnalysisGUI = RfAnalysisGUI()
        self.loadConfigGUI = LoadConfigGUI()
        self.lastGui: RoiSelectionGUI
        self.utcData: UtcData
        self.frame: int

        self.continueButton.clicked.connect(self.continueToRfAnalysis)
        self.backButton.clicked.connect(self.backToLastScreen)
        self.singleRoiWindowButton.clicked.connect(self.singleRoiWindow)
        self.loadConfigButton.clicked.connect(self.loadConfig)
        self.backToImgSelButton.clicked.connect(self.backToImgSelection)
        
    def backToImgSelection(self):
        self.backToLastScreen()
        self.lastGui.backToSelectionScreen()
        self.lastGui.lastGui.backToChoice()

    def loadConfig(self):
        self.loadConfigGUI.analysisParamsGUI = self
        self.loadConfigGUI.show()

    def initParams(self):
        self.axWinSizeVal.setMinimum(
            2 * self.utcData.waveLength
        )  # should be at least 10 times wavelength, must be at least 2 times
        self.latWinSizeVal.setMinimum(
            2 * self.utcData.waveLength
        )  # should be at least 10 times wavelength, must be at least 2 times

        self.axWinSizeVal.setValue(self.utcData.axWinSize)
        self.latWinSizeVal.setValue(self.utcData.latWinSize)
        self.axOverlapVal.setValue(int(self.utcData.axOverlap*100))
        self.latOverlapVal.setValue(int(self.utcData.latOverlap*100))
        self.windowThresholdVal.setValue(int(self.utcData.roiWindowThreshold*100))
        self.minFreqVal.setValue(self.utcData.transducerFreqBand[0]/1000000)
        self.maxFreqVal.setValue(self.utcData.transducerFreqBand[1]/1000000)
        self.lowBandFreqVal.setValue(self.utcData.analysisFreqBand[0]/1000000)
        self.upBandFreqVal.setValue(self.utcData.analysisFreqBand[1]/1000000)
        self.samplingFreqVal.setValue(self.utcData.samplingFrequency/1000000)

        self.imageDepthVal.setText(
            str(np.round(self.utcData.depth, decimals=1))
        )
        self.imageWidthVal.setText(
            str(np.round(self.utcData.width, decimals=1))
        )
        
        self.axWavelengthRatioVal.setText(
            str(np.round(self.axWinSizeVal.value() / self.utcData.waveLength, decimals=2))
        )
        self.latWavelengthRatioVal.setText(
            str(np.round(self.latWinSizeVal.value() / self.utcData.waveLength, decimals=2))
        )
        
        self.axWinSizeVal.valueChanged.connect(self.updateRoiSize)
        self.latWinSizeVal.valueChanged.connect(self.updateRoiSize)
        self.axOverlapVal.valueChanged.connect(self.updateRoiSize)
        self.latOverlapVal.valueChanged.connect(self.updateRoiSize)

    def singleRoiWindow(self):
        self.axOverlapVal.setValue(0)
        self.latOverlapVal.setValue(0)
        self.windowThresholdVal.setValue(50)

        mplPixWidth = max(self.utcData.splineX) - min(
            self.utcData.splineX
        )
        imPixWidth = mplPixWidth * self.utcData.lateralRes
        mmWidth = self.utcData.lateralRes * imPixWidth  # (mm/pixel)*pixels

        mplPixHeight = max(self.utcData.splineY) - min(
            self.utcData.splineY
        )
        imPixHeight = mplPixHeight * self.utcData.axialRes
        mmHeight = self.utcData.axialRes * imPixHeight  # (mm/pixel)*pixels

        self.axWinSizeVal.setValue(np.round(mmHeight, decimals=2))
        self.latWinSizeVal.setValue(np.round(mmWidth, decimals=2))

        # self.updateRoiSize()

    def updateRoiSize(self):
        if self.axWinSizeVal.value() > 0 and self.latWinSizeVal.value() > 0:
            self.axWavelengthRatioVal.setText(
                str(np.round(self.axWinSizeVal.value() / self.utcData.waveLength, decimals=2))
            )
            self.latWavelengthRatioVal.setText(
                str(np.round(self.latWinSizeVal.value() / self.utcData.waveLength, decimals=2))
            )

            # self.maskCoverMesh.fill(0)
            # axialRSize = self.axWinSizeVal.value()
            # lateralRSize = self.latWinSizeVal.value()
            # axialRes = self.utcData.axialRes
            # lateralRes = self.utcData.lateralRes
            # axialSize = round(axialRSize / axialRes)  # in pixels :: mm/(mm/pixel)
            # lateralSize = round(lateralRSize / lateralRes)
            # axialOverlap = self.axOverlapVal.value() / 100
            # lateralOverlap = self.latOverlapVal.value() / 100

            # xScale = self.utcData.roiWidthScale / (self.utcData.pixWidth)
            # yScale = self.utcData.roiDepthScale / (self.utcData.pixDepth)
            # x = self.utcData.splineX / xScale
            # y = self.utcData.splineY / yScale

            # # Some axial/lateral dims
            # axialSize = round(axialRSize / axialRes)  # in pixels :: mm/(mm/pixel)
            # lateralSize = round(lateralRSize / lateralRes)

            # # Overlap fraction determines the incremental distance between ROIs
            # axialIncrement = axialSize * (1 - axialOverlap)
            # lateralIncrement = lateralSize * (1 - lateralOverlap)

            # for x in np.arange(0, self.maskCoverMesh.shape[0], axialIncrement):
            #     ind = round(x)
            #     if ind < self.maskCoverMesh.shape[0]:
            #         self.maskCoverMesh[ind - 2 : ind + 2, 0:] = [0, 255, 255, 255]

            # for y in np.arange(0, self.maskCoverMesh.shape[1], lateralIncrement):
            #     ind = round(y)
            #     if ind < self.maskCoverMesh.shape[1]:
            #         self.maskCoverMesh[0:, ind] = [0, 255, 255, 255]

            # self.maskCoverMesh = np.require(self.maskCoverMesh, np.uint8, "C")
            # self.bytesLineMesh, _ = self.maskCoverMesh[:, :, 0].strides
            # self.qImgMesh = QImage(
            #     self.maskCoverMesh,
            #     self.maskCoverMesh.shape[1],
            #     self.maskCoverMesh.shape[0],
            #     self.bytesLineMesh,
            #     QImage.Format.Format_ARGB32,
            # )

            # self.previewFrameMesh.setPixmap(
            #     QPixmap.fromImage(self.qImgMesh).scaled(
            #         self.widthScale, self.depthScale
            #     )
            # )
            
            self.update()

    def plotRoiPreview(self):
        self.minX = min(self.utcData.splineX)
        self.maxX = max(self.utcData.splineX)
        self.minY = min(self.utcData.splineY)
        self.maxY = max(self.utcData.splineY)

        quotient = (self.maxX - self.minX) / (self.maxY - self.minY)
        if quotient > (341 / 231):
            self.widthScale = 341
            self.depthScale = int(self.widthScale / (
                (self.maxX - self.minX) / (self.maxY - self.minY)
            ))
        else:
            self.widthScale = int(231 * quotient)
            self.depthScale = 231

        self.xLen = round(self.maxX - self.minX)
        self.yLen = round(self.maxY - self.minY)

        self.xScale = self.utcData.pixWidth / self.utcData.roiWidthScale
        self.yScale = self.utcData.pixDepth / self.utcData.roiDepthScale
        self.xLenBmode = round(self.xLen * self.xScale)
        self.yLenBmode = round(self.yLen * self.yScale)
        self.minXBmode = round(self.minX * self.xScale)
        self.minYBmode = round(self.minY * self.yScale)
        endXBmode = min(self.minXBmode + self.xLenBmode, self.utcData.pixWidth - 1)
        endYBmode = min(self.minYBmode + self.yLenBmode, self.utcData.pixDepth - 1)
        self.imData = np.require(
            self.utcData.finalBmode[self.minYBmode : endYBmode, self.minXBmode : endXBmode],
            np.uint8,
            "C",
        )
        self.arHeight = self.imData.shape[0]
        self.arWidth = self.imData.shape[1]

        self.bytesLine = self.imData.strides[0]

        self.maskCoverImg = np.zeros((self.yLen, self.xLen, 4))
        self.maskCoverMesh = np.zeros((self.yLenBmode, self.xLenBmode, 4))

        for i in range(len(self.utcData.splineX)):
            self.maskCoverImg[
                max(round(self.utcData.splineY[i] - self.minY - 1), 0) : max(
                    round(self.utcData.splineY[i] - self.minY - 1), 0
                )
                + 2,
                max(round(self.utcData.splineX[i] - self.minX - 1), 0) : max(
                    round(self.utcData.splineX[i] - self.minX - 1), 0
                )
                + 2,
            ] = [255, 255, 0, 255]

        self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, "C")
        self.bytesLineMask, _ = self.maskCoverImg[:, :, 0].strides
        self.qImgMask = QImage(
            self.maskCoverImg,
            self.maskCoverImg.shape[1],
            self.maskCoverImg.shape[0],
            self.bytesLineMask,
            QImage.Format.Format_ARGB32,
        )

        # self.previewFrameMask.setPixmap(
        #     QPixmap.fromImage(self.qImgMask).scaled(self.widthScale, self.depthScale)
        # )

        # self.qIm = QImage(
        #     self.imData,
        #     self.arWidth,
        #     self.arHeight,
        #     self.bytesLine,
        #     QImage.Format.Format_RGB888,
        # )
        # self.previewFrame.setPixmap(
        #     QPixmap.fromImage(self.qIm).scaled(self.widthScale, self.depthScale)
        # )

        self.updateRoiSize()
        self.axWinSizeVal.valueChanged.connect(self.updateRoiSize)
        self.latWinSizeVal.valueChanged.connect(self.updateRoiSize)
        self.axOverlapVal.valueChanged.connect(self.updateRoiSize)
        self.latOverlapVal.valueChanged.connect(self.updateRoiSize)

    def backToLastScreen(self):
        self.lastGui.utcData = self.utcData
        self.lastGui.show()
        self.lastGui.resize(self.size())
        self.hide()

    def setFilenameDisplays(self, imageName, phantomName):
        self.imagePathInput.setHidden(False)
        self.phantomPathInput.setHidden(False)
        self.imagePathInput.setText(imageName)
        self.phantomPathInput.setText(phantomName)

    def continueToRfAnalysis(self):
        self.utcData.axWinSize = self.axWinSizeVal.value()
        self.utcData.latWinSize = self.latWinSizeVal.value()
        self.utcData.axOverlap = self.axOverlapVal.value() / 100
        self.utcData.latOverlap = self.latOverlapVal.value() / 100
        self.utcData.roiWindowThreshold = self.windowThresholdVal.value() / 100
        self.utcData.transducerFreqBand = [self.minFreqVal.value() * 1000000, self.maxFreqVal.value() * 1000000] # Hz
        self.utcData.samplingFrequency = self.samplingFreqVal.value() * 1000000  # Hz
        self.utcData.analysisFreqBand = [self.lowBandFreqVal.value() * 1000000, self.upBandFreqVal.value() * 1000000] # Hz

        del self.rfAnalysisGUI
        self.rfAnalysisGUI = RfAnalysisGUI()
        self.rfAnalysisGUI.utcData = self.utcData
        self.rfAnalysisGUI.setFilenameDisplays(
            self.imagePathInput.text().split("/")[-1],
            self.phantomPathInput.text().split("/")[-1],
        )
        success = self.rfAnalysisGUI.completeUtcAnalysis()

        if success < 0:
            return
        self.rfAnalysisGUI.show()
        self.rfAnalysisGUI.lastGui = self
        self.rfAnalysisGUI.resize(self.size())
        self.rfAnalysisGUI.frame = self.frame
        self.hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = AnalysisParamsGUI()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())
