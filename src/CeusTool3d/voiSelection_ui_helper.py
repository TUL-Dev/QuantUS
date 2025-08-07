import os
from pathlib import Path
from itertools import chain
from contextlib import suppress

from PIL.ImageQt import ImageQt
from PIL import Image, ImageEnhance
import nibabel as nib
import numpy as np
import scipy.interpolate as interpolate
from scipy.spatial import ConvexHull
from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog
from PyQt6.QtGui import QPixmap, QImage, QResizeEvent, QWheelEvent, QPainter, QCursor
from PyQt6.QtCore import Qt, QPoint, QLine, pyqtSlot
from scipy.ndimage import binary_fill_holes

import src.Utils.utils as ut
from src.CeusTool3d.voiSelection_ui import Ui_constructVoi
from src.CeusTool3d.saveVoi_ui_helper import SaveVoiGUI
from src.CeusTool3d.ticAnalysis_ui_helper import TicAnalysisGUI
from src.CeusTool3d.interpolationLoading_ui_helper import InterpolationLoadingGUI
from src.CeusTool3d.advancedRoi_ui_helper import AdvancedRoiDrawGUI
from src.Utils.qtSupport import MouseTracker, qImToPIL
from src.Utils.spline import calculateSpline3D, calculateSpline, removeDuplicates

class VoiSelectionGUI(Ui_constructVoi, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setLayout(self.fullScreenLayout)
        self.hideVoiAlphaLayout()
        self.hideDrawVoiLayout()
        self.hideVoiDecisionLayout()
        self.toggleButton.hide(); self.navigatingLabel.hide()
        self.toggleButton.setCheckable(True)
        self.showHideCrossButton.setCheckable(True)
        self.drawRoiButton.setCheckable(True)
        
        self.scrollPaused = False
        self.sliceSpinBoxChanged = False
        self.sliceSliderChanged = False
        self.newData = None
        self.auc = None
        self.pe = None
        self.tp = None
        self.mtt = None
        self.tmppv = None
        self.fullPath = None
        self.bmode4dImg = None
        self.curSliceIndex = 0
        self.curAlpha = 255
        self.curPointsPlottedX = []; self.curPointsPlottedY = []
        self.interpolatedPoints = []; self.negInterpolatedPoints = []; self.prevInterpolatedPoints = []
        self.planesDrawn = []; self.pointsPlotted = []
        self.painted = "none"; self.paintedSlice = []
        self.lastGui = None
        self.saveVoiGUI = None
        self.timeconst = None
        self.drawingNeg = False

        self.ticAnalysisGui = None
        self.loadingGUI = InterpolationLoadingGUI()
        self.advancedRoiDrawGui = AdvancedRoiDrawGUI()
        
        self.voiAlphaSpinBox.setMinimum(0)
        self.voiAlphaSpinBox.setMaximum(255)
        self.voiAlphaStatus.setMinimum(0)
        self.voiAlphaStatus.setMaximum(255)
        self.voiAlphaStatus.setValue(255)
        self.voiAlphaSpinBox.setValue(255)

        self.enhanceContrastButton.setChecked(False)
        self.enhanceContrastButton.clicked.connect(self.enhanceContrastChecked)
        self.drawNegVoiButton.clicked.connect(self.startNegDraw)
        self.backToPrevVoiButton.clicked.connect(self.backToPrevVoi)
        self.drawNewVoiButton.clicked.connect(self.drawNewVoi)
        self.backFromDrawButton.clicked.connect(self.backFromDraw)
        self.loadVoiButton.clicked.connect(self.loadVoi)
        self.continueButton.clicked.connect(self.moveToTic)
        self.drawRoiButton.clicked.connect(self.startRoiDraw)
        self.undoLastPtButton.clicked.connect(self.undoLastPoint)
        self.restartVoiButton.clicked.connect(self.restartVoi)
        self.voiAlphaSpinBox.valueChanged.connect(self.alphaValueChanged)
        self.backButton.clicked.connect(self.backToLastScreen)
        self.saveVoiButton.clicked.connect(self.startSaveVoi)
        self.showHideCrossButton.clicked.connect(self.showHideCross)
        self.interpolateVoiButton.clicked.connect(self.voi3dInterpolation)
        self.toggleButton.clicked.connect(self.toggleIms)
        
    def enhanceContrastChecked(self):
        self.changeAxialSlices()
        self.changeSagSlices()
        self.changeCorSlices()

    def axAdvancedRoiDraw(self):
        axDrawings = np.array([planeDrawn[1] for planeDrawn in self.planesDrawn if planeDrawn[0] == "ax"])
        drawingZSlices = axDrawings[:,0]
        closestZIndex = np.argmin(abs(drawingZSlices - self.newZVal))
        closestAxDrawing = axDrawings[closestZIndex]

        planeIdx = [i for i, planeDrawn in enumerate(self.planesDrawn) if planeDrawn[0] == "ax" and np.all(planeDrawn[1] == closestAxDrawing)][0]
        pointsPlottedX, pointsPlottedY = self.pointsPlotted[planeIdx]

        data2dAx = self.data4dImg[:, :, closestAxDrawing[0], closestAxDrawing[1]]
        data2dAx = np.rot90(np.flipud(data2dAx), 3)
        data2dAx = np.require(data2dAx, np.uint8, "C")
        self.newZVal = closestAxDrawing[0]; 
        self.curSliceSlider.setValue(closestAxDrawing[1])
        self.updateCrosshairs()
        self.startAdvancedRoiDraw(data2dAx, pointsPlottedX, pointsPlottedY, planeIdx)

    def sagAdvancedRoiDraw(self):
        sagDrawings = np.array([planeDrawn[1] for planeDrawn in self.planesDrawn if planeDrawn[0] == "sag"])
        drawingXSlices = sagDrawings[:,0]
        closestXIndex = np.argmin(abs(drawingXSlices - self.newXVal))
        closestSagDrawing = sagDrawings[closestXIndex]
        
        planeIdx = [i for i, planeDrawn in enumerate(self.planesDrawn) if planeDrawn[0] == "sag" and np.all(planeDrawn[1] == closestSagDrawing)][0]
        pointsPlottedX, pointsPlottedY = self.pointsPlotted[planeIdx]

        data2dSag = self.data4dImg[closestSagDrawing[0], :, :, closestSagDrawing[1]]
        data2dSag = np.require(data2dSag, np.uint8, "C")
        self.newXVal = closestSagDrawing[0]; 
        self.curSliceSlider.setValue(closestSagDrawing[1]) 
        self.updateCrosshairs()
        self.startAdvancedRoiDraw(data2dSag, pointsPlottedX, pointsPlottedY, planeIdx)
    
    def corAdvancedRoiDraw(self):
        corDrawings = np.array([planeDrawn[1] for planeDrawn in self.planesDrawn if planeDrawn[0] == "cor"])
        drawingYSlices = corDrawings[:,0]
        closestYIndex = np.argmin(abs(drawingYSlices - self.newYVal))
        closestCorDrawing = corDrawings[closestYIndex]
        
        planeIdx = [i for i, planeDrawn in enumerate(self.planesDrawn) if planeDrawn[0] == "cor" and np.all(planeDrawn[1] == closestCorDrawing)][0]
        pointsPlottedX, pointsPlottedY = self.pointsPlotted[planeIdx]

        data2dCor = self.data4dImg[:, closestCorDrawing[0], :, closestCorDrawing[1]]
        data2dCor = np.fliplr(np.rot90(data2dCor, 3))
        data2dCor = np.require(data2dCor, np.uint8, "C")
        self.newYVal = closestCorDrawing[0]; 
        self.curSliceSlider.setValue(closestCorDrawing[1]) 
        self.updateCrosshairs()
        self.startAdvancedRoiDraw(data2dCor, pointsPlottedX, pointsPlottedY, planeIdx)

    def startAdvancedRoiDraw(self, image, pointsPlottedX, pointsPlottedY, drawingIdx):
        self.advancedRoiDrawGui.voiSelectionGUI = self
        self.advancedRoiDrawGui.drawingIdx = drawingIdx
        self.advancedRoiDrawGui.curPlane = self.planesDrawn[drawingIdx]
        self.advancedRoiDrawGui.ax.clear()
        self.advancedRoiDrawGui.x = pointsPlottedX
        self.advancedRoiDrawGui.y = pointsPlottedY
        self.advancedRoiDrawGui.ax.imshow(image, cmap="Greys_r", aspect="auto")
        self.advancedRoiDrawGui.prepPlot()
        self.advancedRoiDrawGui.canvas.draw()
        self.advancedRoiDrawGui.resize(self.size())
        self.advancedRoiDrawGui.show()

    def mousePressEvent(self, event):
        if (self.drawRoiButton.isHidden() or not self.drawRoiButton.isChecked()) and self.painted == "none":
            if self.navigatingLabel.isHidden():
                self.navigatingLabel.show(); self.observingLabel.hide()
                if not self.showHideCrossButton.isChecked():
                    self.axialPlane.setCursor(QCursor(Qt.CursorShape.BlankCursor))
                    self.sagPlane.setCursor(QCursor(Qt.CursorShape.BlankCursor))
                    self.corPlane.setCursor(QCursor(Qt.CursorShape.BlankCursor))
            else:
                self.navigatingLabel.hide(); self.observingLabel.show()
                self.axialPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                self.sagPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                self.corPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def startSaveVoi(self):
        del self.saveVoiGUI
        self.saveVoiGUI = SaveVoiGUI()
        self.saveVoiGUI.voiSelectionGUI = self
        destPath = Path(self.fullPath).parent / Path("nifti_segmentation_QUANTUS")
        destPath.mkdir(exist_ok=True)

        self.saveVoiGUI.newFolderPathInput.setText(f"{destPath}")
        self.saveVoiGUI.newFileNameInput.setText(
            str(Path(self.fullPath).name[:-7] + "_segmentation.nii.gz")
        )
        self.saveVoiGUI.show()

    def saveVoi(self, fileDestination, name, frame):
        segMask = np.zeros([self.x + 1, self.y + 1, self.z + 1])
        for point in self.interpolatedPoints[0]:
            segMask[point[0], point[1], point[2]] = 1

        affine = np.eye(4)
        niiarray = nib.Nifti1Image(segMask.astype("uint8"), affine)
        niiarray.header["descrip"] = self.imagePathInput.text()
        outputPath = os.path.join(fileDestination, name)
        if os.path.exists(outputPath):
            os.remove(outputPath)
        nib.save(niiarray, outputPath)

    def loadVoi(self):
        fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter="*.nii.gz")
        if fileName != "":
            nibIm = nib.load(fileName)
            niftiScan = bytes(nibIm.header["descrip"]).decode("UTF-8")
            nameIdx = niftiScan.rfind(".nii.gz")
            niftiScan = niftiScan[:nameIdx+len(".nii.gz")]
            
            if self.imagePathInput.text().replace("'", '"') == niftiScan:
                mask = np.asarray(nibIm.dataobj, dtype=np.uint8)
            else:
                print("Mask is not compatible with this image")
                return
        else:
            return
        maskPoints = np.where(mask > 0)
        maskPoints = np.transpose(maskPoints)
        for point in maskPoints:
            self.maskCoverImg[point[0], point[1], point[2]] = [0, 0, 255, int(self.curAlpha)]
        
        self.interpolatedPoints = [np.transpose(np.where(self.maskCoverImg[:,:,:,2] == 255))]
        self.curFrameIndex = maskPoints[0, 0]

        self.hideVoiApproachLayout()
        self.showVoiDecisionLayout()
        self.showVoiAlphaLayout()
        self.updateCrosshairs()

    def backFromDraw(self):
        self.hideDrawVoiLayout()
        self.showVoiApproachLayout()

        self.interpolatedPoints = []
        self.planesDrawn = []
        self.pointsPlotted = []
        self.maskCoverImg.fill(0)
        self.painted = "none"; self.paintedSlice = []
        self.advancedRoiEditAxButton.setChecked(False)
        self.advancedRoiEditSagButton.setChecked(False); self.advancedRoiEditCorButton.setChecked(False)
        self.scrollPaused = False
        self.drawRoiButton.setChecked(False)
        self.updateCrosshairs()

    def drawNewVoi(self):
        self.hideVoiApproachLayout()
        self.showDrawVoiLayout()

    def backToLastScreen(self):
        self.lastGui.timeconst = None
        self.lastGui.hideFrameRateLabels()
        self.lastGui.imagePath = ""
        self.lastGui.bmodeImagePath = ""
        self.lastGui.show()
        self.lastGui.resize(self.size())
        self.hide()

    def wheelEvent(self, event: QWheelEvent):
        curTime = self.curSliceSpinBox.value()
        if event.angleDelta().y() > 0:
            self.curSliceSpinBox.setValue(curTime+1)
        else:
            self.curSliceSpinBox.setValue(curTime-1)

    def startNegDraw(self):
        self.negInterpolatedPoints = []; self.planesDrawn = []; self.drawingNeg = True
        self.pointsPlotted = []
        self.showVoiAlphaLayout(); self.hideVoiDecisionLayout()
        self.showVoiApproachLayout(); self.updateCrosshairs()

    def restartVoi(self):
        self.interpolatedPoints = []; self.negInterpolatedPoints = []; self.prevInterpolatedPoints = []
        self.planesDrawn = []; self.pointsPlotted = []; self.maskCoverImg.fill(0)
        self.voiAlphaStatus.setValue(255); self.voiAlphaSpinBox.setValue(255)
        self.hideVoiAlphaLayout(); self.hideVoiDecisionLayout()
        self.showVoiApproachLayout(); self.updateCrosshairs()
        self.backFromDraw()

    def computeTic(self):
        times = [i * self.timeconst for i in range(1, self.ceus4dImg.shape[3] + 1)]
        self.voxelScale = (
            self.header[1] * self.header[2] * self.header[3]
        )  # /1000/1000/1000 # mm^3
        print("Voxel volume:", self.voxelScale)
        self.voxelScale *= len(self.interpolatedPoints[0])
        print("Num voxels:", len(self.interpolatedPoints[0]))
        simplifiedMask = self.maskCoverImg[:, :, :, 2]
        TIC = ut.generate_TIC(
            self.ceus4dImg, simplifiedMask, times, 24.09, self.voxelScale
        )  # hard-coded for now

        # Bunch of checks
        if np.isnan(np.sum(TIC[:, 1])):
            print("STOPPED:NaNs in the VOI")
            return
        if np.isinf(np.sum(TIC[:, 1])):
            print("STOPPED:InFs in the VOI")
            return

        self.ticX = np.array([[TIC[i, 0], i] for i in range(len(TIC[:, 0]))])
        self.ticY = TIC[:, 1]
        self.ticAnalysisGui.ax.clear()
        self.ticAnalysisGui.ticX = []
        self.ticAnalysisGui.ticY = []
        self.ticAnalysisGui.removedPointsX = []
        self.ticAnalysisGui.removedPointsY = []
        self.ticAnalysisGui.selectedPoints = []
        self.ticAnalysisGui.t0Index = -2
        self.ticAnalysisGui.graph(self.ticX, self.ticY)

    def setFilenameDisplays(self, imageName):
        self.imagePathInput.setHidden(False)

        imFile = imageName.split("/")[-1]
        self.fullPath = imageName

        self.imagePathInput.setText(imFile)
        self.inputTextPath = imageName

    def curSliceSpinBoxValueChanged(self):
        if not self.sliceSliderChanged:
            self.sliceSpinBoxChanged = True
            self.sliceValueChanged()

    def curSliceSliderValueChanged(self):
        if not self.sliceSpinBoxChanged:
            self.sliceSliderChanged = True
            self.sliceValueChanged()

    def findSliceFromTime(self, inputtedTime):
        i = 0
        while i < len(self.sliceArray):
            if inputtedTime < self.sliceArray[i]:
                break
            i += 1
        if i == len(self.sliceArray):
            i -= 1
        elif i > 0:
            if (self.sliceArray[i] - inputtedTime) > (
                self.sliceArray[i - 1] - inputtedTime
            ):
                i -= 1
        if i < 0:
            i = 0
        return i

    def sliceValueChanged(self):
        if self.sliceSpinBoxChanged and self.sliceSliderChanged:
            self.sliceSpinBoxChanged = False
            self.sliceSliderChanged = False
            print("Error tracking slices")
            return
        if self.sliceSpinBoxChanged:
            self.curSliceIndex = self.findSliceFromTime(self.curSliceSpinBox.value())
            self.curSliceSlider.setValue(self.curSliceIndex)
            self.sliceSpinBoxChanged = False
        if self.sliceSliderChanged:
            self.curSliceIndex = int(self.curSliceSlider.value())
            self.curSliceSpinBox.setValue(self.sliceArray[self.curSliceIndex])
            self.sliceSliderChanged = False
        self.updateCrosshairs()

    def alphaValueChanged(self):
        self.curAlpha = int(self.voiAlphaSpinBox.value())
        self.voiAlphaSpinBoxChanged = False
        self.voiAlphaStatus.setValue(self.curAlpha)
        for i in range(len(self.interpolatedPoints)):
            for j in range(len(self.interpolatedPoints[i])):
                self.maskCoverImg[
                    self.interpolatedPoints[i][j][0],
                    self.interpolatedPoints[i][j][1],
                    self.interpolatedPoints[i][j][2],
                    3,
                ] = self.curAlpha
        self.updateCrosshairs()

    def toggleIms(self):
        if self.toggleButton.isChecked():
            self.data4dImg = self.bmode4dImg
        else:
            self.data4dImg = self.ceus4dImg
        self.updateCrosshairs()

    def showHideCross(self):
        if self.showHideCrossButton.isChecked():
            pilIms = [self.imAxPIL, self.imSagPIL, self.imCorPIL]
            pixmaps = [self.pixmapAx, self.pixmapSag, self.pixmapCor]
            for i, pilIm in enumerate(pilIms):
                pixmaps[i] = QPixmap.fromImage(ImageQt(pilIm))
            self.changeAxialSlices(); self.changeSagSlices(); self.changeCorSlices()
            self.axialPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.sagPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.corPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            if self.observingLabel.isHidden():
                self.axialPlane.setCursor(QCursor(Qt.CursorShape.BlankCursor))
                self.sagPlane.setCursor(QCursor(Qt.CursorShape.BlankCursor))
                self.corPlane.setCursor(QCursor(Qt.CursorShape.BlankCursor))
            self.updateCrosshairs()

    def openImage(self, bmodePath):
        nibCeusImg = nib.load(self.inputTextPath, mmap=False)
        self.ceus4dImg = np.asarray(nibCeusImg.dataobj, dtype=np.uint8)
        
        self.data4dImg = self.ceus4dImg

        self.x, self.y, self.z, self.numSlices = self.data4dImg.shape
        self.maskCoverImg = np.zeros([self.x, self.y, self.z, 4])
        self.curSliceSlider.setMaximum(self.numSlices - 1)

        if bmodePath is not None:
            nibBmodeImg = nib.load(bmodePath, mmap=False)
            self.bmode4dImg = np.asarray(nibBmodeImg.dataobj, dtype=np.uint8)
            self.toggleButton.show()

        self.header = nibCeusImg.header["pixdim"]  # [dims, voxel dims (3 vals), timeconst, 0, 0, 0], assume mm/pix
        self.sliceArray = np.round(
            [i * self.timeconst for i in range(1, self.ceus4dImg.shape[3] + 1)],
            decimals=2,
        )
        self.curSliceSpinBox.setMaximum(self.sliceArray[-1])
        self.curSliceTotal.setText(str(self.sliceArray[-1]))

        self.curSliceSpinBox.setValue(self.sliceArray[self.curSliceIndex])
        self.curSliceSlider.setValue(self.curSliceIndex)
        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)

        self.axialTotalFrames.setText(str(self.z + 1))
        self.sagittalTotalFrames.setText(str(self.x + 1))
        self.coronalTotalFrames.setText(str(self.y + 1))
        self.axialFrameNum.setText("1")
        self.sagittalFrameNum.setText("1")
        self.coronalFrameNum.setText("1")

        self.x -= 1; self.y -= 1; self.z -= 1
        self.newXVal = 0; self.newYVal = 0; self.newZVal = 0
        self.updateCrosshairs()

        trackerAx = MouseTracker(self.axialPlane)
        trackerAx.positionChanged.connect(self.axCoordChanged)
        trackerAx.positionClicked.connect(self.axPlaneClicked)
        trackerSag = MouseTracker(self.sagPlane)
        trackerSag.positionChanged.connect(self.sagCoordChanged)
        trackerSag.positionClicked.connect(self.sagPlaneClicked)
        trackerCor = MouseTracker(self.corPlane)
        trackerCor.positionChanged.connect(self.corCoordChanged)
        trackerCor.positionClicked.connect(self.corPlaneClicked)

    @pyqtSlot(QPoint)
    def axPlaneClicked(self, pos):
        if self.drawRoiButton.isChecked():
            if self.painted == "none":
                self.painted = "ax"
                self.paintedSlice = [self.newZVal, self.curSliceIndex]
            if self.painted == "ax":
                self.axCoordChanged(pos)
                if self.drawingNeg:
                    self.maskCoverImg[self.newXVal, self.newYVal, self.newZVal] = [0, 255, 0, int(self.curAlpha)]
                else:
                    self.maskCoverImg[self.newXVal, self.newYVal, self.newZVal] = [0, 0, 255, int(self.curAlpha)]
                self.curPointsPlottedX.append(self.newXVal); self.curPointsPlottedY.append(self.newYVal)
                self.updateCrosshairs()
        elif not self.drawRoiButton.isHidden() and self.painted == "ax":
            self.scrollPaused = True if not self.scrollPaused else False

    @pyqtSlot(QPoint)
    def axCoordChanged(self, pos):
        if not self.scrollPaused and ((self.observingLabel.isHidden() and self.painted == "none") or self.painted == "ax"):
            xdiff = self.axialPlane.width() - self.axialPlane.pixmap().width()
            ydiff = self.axialPlane.height() - self.axialPlane.pixmap().height()
            xCoord = pos.x() - xdiff/2; yCoord = pos.y() - ydiff/2

            if xCoord < 0 or yCoord < 0 or xCoord >= self.axialPlane.pixmap().width() or yCoord >= self.axialPlane.pixmap().height():
                return
            self.newXVal = int((xCoord/self.axialPlane.pixmap().width()) * self.x)
            self.newYVal = int((yCoord/self.axialPlane.pixmap().height()) * self.y)
            self.updateCrosshairs()

    @pyqtSlot(QPoint)
    def sagPlaneClicked(self, pos):
        if self.drawRoiButton.isChecked():
            if self.painted == "none":
                self.painted = "sag"
                self.paintedSlice = [self.newXVal, self.curSliceIndex]
            if self.painted == "sag":
                self.sagCoordChanged(pos)
                if self.drawingNeg:
                    self.maskCoverImg[self.newXVal, self.newYVal, self.newZVal] = [0, 255, 0, int(self.curAlpha)]
                else:
                    self.maskCoverImg[self.newXVal, self.newYVal, self.newZVal] = [0, 0, 255, int(self.curAlpha)]
                self.curPointsPlottedX.append(self.newZVal); self.curPointsPlottedY.append(self.newYVal)
                self.updateCrosshairs()
        elif not self.drawRoiButton.isHidden() and self.painted == "sag":
            self.scrollPaused = True if not self.scrollPaused else False

    @pyqtSlot(QPoint)
    def sagCoordChanged(self, pos):
        if not self.scrollPaused and ((self.observingLabel.isHidden() and self.painted == "none") or self.painted == "sag"):
            xdiff = self.sagPlane.width() - self.sagPlane.pixmap().width()
            ydiff = self.sagPlane.height() - self.sagPlane.pixmap().height()
            xCoord = pos.x() - xdiff/2; yCoord = pos.y() - ydiff/2

            if xCoord < 0 or yCoord < 0 or xCoord >= self.sagPlane.pixmap().width() or yCoord >= self.sagPlane.pixmap().height():
                return
            self.newZVal = int((xCoord/self.sagPlane.pixmap().width()) * self.z)
            self.newYVal = int((yCoord/self.sagPlane.pixmap().height()) * self.y)
            self.updateCrosshairs()

    @pyqtSlot(QPoint)
    def corPlaneClicked(self, pos):
        if self.drawRoiButton.isChecked():
            if self.painted == "none":
                self.painted = "cor"
                self.paintedSlice = [self.newYVal, self.curSliceIndex]
            if self.painted == "cor":
                self.corCoordChanged(pos)
                if self.drawingNeg:
                    self.maskCoverImg[self.newXVal, self.newYVal, self.newZVal] = [0, 255, 0, int(self.curAlpha)]
                else:
                    self.maskCoverImg[self.newXVal, self.newYVal, self.newZVal] = [0, 0, 255, int(self.curAlpha)]
                self.curPointsPlottedX.append(self.newXVal); self.curPointsPlottedY.append(self.newZVal)
                self.updateCrosshairs()
        elif not self.drawRoiButton.isHidden() and self.painted == "cor":
            self.scrollPaused = True if not self.scrollPaused else False
        
    @pyqtSlot(QPoint)
    def corCoordChanged(self, pos):
        if not self.scrollPaused and ((self.observingLabel.isHidden() and self.painted == "none") or self.painted == "cor"):
            xdiff = self.corPlane.width() - self.corPlane.pixmap().width()
            ydiff = self.corPlane.height() - self.corPlane.pixmap().height()
            xCoord = pos.x() - xdiff/2; yCoord = pos.y() - ydiff/2

            if xCoord < 0 or yCoord < 0 or xCoord >= self.corPlane.pixmap().width() or yCoord >= self.corPlane.pixmap().height():
                return
            self.newXVal = int((xCoord/self.corPlane.pixmap().width()) * self.x)
            self.newZVal = int((yCoord/self.corPlane.pixmap().height()) * self.z)
            self.updateCrosshairs()

    def updateCrosshairs(self):
        self.updateAdvancedRoiEditButtons()
        self.changeAxialSlices(); self.changeSagSlices(); self.changeCorSlices()
        xCoordAx = int((self.newXVal/self.x) * self.axialPlane.pixmap().width())
        yCoordAx = int((self.newYVal/self.y) * self.axialPlane.pixmap().height())
        xCoordSag = int((self.newZVal/self.z) * self.sagPlane.pixmap().width())
        yCoordSag = int((self.newYVal/self.y) * self.sagPlane.pixmap().height())
        xCoordCor = int((self.newXVal/self.x) * self.corPlane.pixmap().width())
        yCoordCor = int((self.newZVal/self.z) * self.corPlane.pixmap().height())

        if not self.showHideCrossButton.isChecked():
            pixmaps = [self.axialPlane.pixmap(), self.sagPlane.pixmap(), self.corPlane.pixmap()]
            points = [(xCoordAx, yCoordAx), (xCoordSag, yCoordSag), (xCoordCor, yCoordCor)]
            for i, pixmap in enumerate(pixmaps):
                painter = QPainter(pixmap); painter.setPen(Qt.GlobalColor.yellow)
                coord = points[i]
                vertLine = QLine(coord[0], 0, coord[0], pixmap.height())
                latLine = QLine(0, coord[1], pixmap.width(), coord[1])
                painter.drawLines([vertLine, latLine])
                painter.end()
                if i == 0:
                    self.axialPlane.setPixmap(pixmap)
                elif i == 1:
                    self.sagPlane.setPixmap(pixmap)
                else:         
                    self.corPlane.setPixmap(pixmap)


    def hideDrawVoiLayout(self):
        self.drawRoiButton.hide()
        self.undoLastPtButton.hide()
        self.multiUseRoiButton.hide()
        self.interpolateVoiButton.hide()
        self.backFromDrawButton.hide()
        self.voiAdviceLabel.hide()
        self.drawRoiButton.setChecked(False)

    def hideVoiDecisionLayout(self):
        self.restartVoiButton.hide()
        self.saveVoiButton.hide()
        self.continueButton.hide()
        self.drawNegVoiButton.hide()
        self.backToPrevVoiButton.hide()

    def hideVoiApproachLayout(self):
        self.drawNewVoiButton.hide()
        self.loadVoiButton.hide()

    def hideVoiAlphaLayout(self):
        self.voiAlphaOfLabel.hide()
        self.voiAlphaSpinBox.hide()
        self.voiAlphaStatus.hide()
        self.voiAlphaTotal.hide()
        self.voiAlphaLabel.hide()

    def showDrawVoiLayout(self):
        self.drawRoiButton.show()
        self.undoLastPtButton.show()
        self.multiUseRoiButton.show()
        self.interpolateVoiButton.show()
        self.backFromDrawButton.show()
        self.voiAdviceLabel.show()

    def showVoiDecisionLayout(self):
        self.restartVoiButton.show()
        self.saveVoiButton.show()
        self.continueButton.show()
        self.drawNegVoiButton.show()

    def showVoiApproachLayout(self):
        self.drawNewVoiButton.show()
        self.loadVoiButton.show()

    def showVoiAlphaLayout(self):
        self.voiAlphaOfLabel.show()
        self.voiAlphaSpinBox.show()
        self.voiAlphaStatus.show()
        self.voiAlphaTotal.show()
        self.voiAlphaLabel.show()
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.axialPlane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sagPlane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.corPlane.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.updateCrosshairs()

    def changeAxialSlices(self):
        self.axialFrameNum.setText(str(self.newZVal + 1))

        data2dAx = self.data4dImg[:, :, self.newZVal, self.curSliceIndex]
        data2dAx = np.rot90(np.flipud(data2dAx), 3).astype(np.uint8)
        if self.enhanceContrastButton.isChecked():
            data2dAx = np.array(ImageEnhance.Contrast(Image.fromarray(data2dAx)).enhance(2.0))
        # data2dAx -= np.amin(data2dAx)
        # data2dAx = (data2dAx.astype(np.float64) * (255/np.amax(data2dAx))).astype(np.uint8)
        data2dAx = np.require(data2dAx, np.uint8, "C")
        heightAx, widthAx = data2dAx.shape  # getting height and width for each plane
        bytesLineAx, _ = data2dAx.strides

        qImgAx = QImage(data2dAx, widthAx, heightAx, bytesLineAx, QImage.Format.Format_Grayscale8)
        qImgAx = qImgAx.convertToFormat(QImage.Format.Format_ARGB32)

        tempAx = self.maskCoverImg[:, :, self.newZVal, :]  # 2D data for axial
        tempAx = np.rot90(np.flipud(tempAx), 3)
        tempAx = np.require(tempAx, np.uint8, "C")
        maskAxH, maskAxW = tempAx[:, :, 0].shape
        maskBytesLineAx, _ = tempAx[:, :, 0].strides

        curMaskAxIm = QImage(tempAx, maskAxW, maskAxH, maskBytesLineAx, QImage.Format.Format_ARGB32)

        self.imAxPIL = qImToPIL(qImgAx); maskAx = qImToPIL(curMaskAxIm)
        self.imAxPIL.paste(maskAx, mask=maskAx)
        self.pixmapAx = QPixmap.fromImage(ImageQt(self.imAxPIL))
        self.axialPlane.setPixmap(self.pixmapAx.scaled(
            self.axialPlane.width(), self.axialPlane.height(), Qt.AspectRatioMode.KeepAspectRatio))

    def changeSagSlices(self):
        self.sagittalFrameNum.setText(str(self.newXVal + 1))

        data2dSag = self.data4dImg[self.newXVal, :, :, self.curSliceIndex].astype(np.uint8)
        if self.enhanceContrastButton.isChecked():
            data2dSag = np.array(ImageEnhance.Contrast(Image.fromarray(data2dSag)).enhance(2.0))
        # data2dSag -= np.amin(data2dSag)
        # data2dSag = (data2dSag.astype(np.float64) * (255/np.amax(data2dSag))).astype(np.uint8)
        data2dSag = np.require(data2dSag, np.uint8, "C")
        heightSag, widthSag = data2dSag.shape
        bytesLineSag, _ = data2dSag.strides
        
        qImgSag = QImage(data2dSag, widthSag, heightSag, bytesLineSag, QImage.Format.Format_Grayscale8)
        qImgSag = qImgSag.convertToFormat(QImage.Format.Format_ARGB32)

        tempSag = self.maskCoverImg[self.newXVal, :, :, :]  # 2D data for sagittal
        tempSag = np.require(tempSag, np.uint8, "C")
        maskSagH, maskSagW = tempSag[:, :, 0].shape
        maskBytesLineSag, _ = tempSag[:, :, 0].strides

        curMaskSagIm = QImage(tempSag, maskSagW, maskSagH, maskBytesLineSag, QImage.Format.Format_ARGB32)

        self.imSagPIL = qImToPIL(qImgSag); maskSag = qImToPIL(curMaskSagIm)
        self.imSagPIL.paste(maskSag, mask=maskSag)
        self.pixmapSag = QPixmap.fromImage(ImageQt(self.imSagPIL))
        self.sagPlane.setPixmap(self.pixmapSag.scaled(
            self.sagPlane.width(), self.sagPlane.height(), Qt.AspectRatioMode.KeepAspectRatio))

    def changeCorSlices(self):
        self.coronalFrameNum.setText(str(self.newYVal + 1))

        data2dCor = self.data4dImg[:, self.newYVal, :, self.curSliceIndex]
        data2dCor = np.fliplr(np.rot90(data2dCor, 3)).astype(np.uint8)
        if self.enhanceContrastButton.isChecked():
            data2dCor = np.array(ImageEnhance.Contrast(Image.fromarray(data2dCor)).enhance(2.0))
        # data2dCor -= np.amin(data2dCor)
        # data2dCor = (data2dCor.astype(np.float64) * (255/np.amax(data2dCor))).astype(np.uint8)
        data2dCor = np.require(data2dCor, np.uint8, "C")
        heightCor, widthCor = data2dCor.shape
        bytesLineCor, _ = data2dCor.strides

        qImgCor = QImage(data2dCor, widthCor, heightCor, bytesLineCor, QImage.Format.Format_Grayscale8)
        qImgCor = qImgCor.convertToFormat(QImage.Format.Format_ARGB32)

        tempCor = self.maskCoverImg[:, self.newYVal, :, :]  # 2D data for coronal
        tempCor = np.fliplr(np.rot90(tempCor, 3))
        tempCor = np.require(tempCor, np.uint8, "C")
        maskCorH, maskCorW = tempCor[:, :, 0].shape
        maskBytesLineCor, _ = tempCor[:, :, 0].strides

        curMaskCorIm = QImage(tempCor, maskCorW, maskCorH, maskBytesLineCor, QImage.Format.Format_ARGB32)

        self.imCorPIL = qImToPIL(qImgCor); maskCor = qImToPIL(curMaskCorIm)
        self.imCorPIL.paste(maskCor, mask=maskCor)
        self.pixmapCor = QPixmap.fromImage(ImageQt(self.imCorPIL))
        self.corPlane.setPixmap(self.pixmapCor.scaled(
            self.corPlane.width(), self.corPlane.height(), Qt.AspectRatioMode.KeepAspectRatio))

    def acceptRoi(self):
        # 2d interpolation
        if len(self.curPointsPlottedX):
            self.drawRoiButton.setChecked(False)

            # remove duplicate points
            points = np.transpose(
                np.array([self.curPointsPlottedX, self.curPointsPlottedY])
            )
            points = removeDuplicates(points)
            [self.curPointsPlottedX, self.curPointsPlottedY] = np.transpose(points)
            self.curPointsPlottedX = list(self.curPointsPlottedX)
            self.curPointsPlottedY = list(self.curPointsPlottedY)

            self.curPointsPlottedX.append(self.curPointsPlottedX[0])
            self.curPointsPlottedY.append(self.curPointsPlottedY[0])
            self.maskCoverImg.fill(0)
            x, y = calculateSpline(self.curPointsPlottedX, self.curPointsPlottedY)
            newROI = []
            for i in range(len(x)):
                if self.painted == "ax":
                    if not len(newROI) or newROI[-1] != (int(x[i]), int(y[i]), self.newZVal):
                        newROI.append((int(x[i]), int(y[i]), self.newZVal))
                elif self.painted == "sag":
                    if not len(newROI) or newROI[-1] != (self.newXVal, int(y[i]), int(x[i])):
                        newROI.append((self.newXVal, int(y[i]), int(x[i])))
                elif self.painted == "cor":
                    if not len(newROI) or newROI[-1] != (int(x[i]), self.newYVal, int(y[i])):
                        newROI.append((int(x[i]), self.newYVal, int(y[i])))
            if not self.drawingNeg:
                self.interpolatedPoints.append(newROI)
                self.pointsPlotted.append([self.curPointsPlottedX, self.curPointsPlottedY])
            for i in range(len(self.interpolatedPoints)):
                for j in range(len(self.interpolatedPoints[i])):
                    self.maskCoverImg[self.interpolatedPoints[i][j][0], self.interpolatedPoints[i][j][1], self.interpolatedPoints[i][j][2],
                    ] = [0, 0, 255, int(self.curAlpha)]
            if self.drawingNeg:
                self.negInterpolatedPoints.append(newROI)
                self.pointsPlotted.append([self.curPointsPlottedX, self.curPointsPlottedY])
                for i in range(len(self.negInterpolatedPoints)):
                    for j in range(len(self.negInterpolatedPoints[i])):
                        self.maskCoverImg[self.negInterpolatedPoints[i][j][0], self.negInterpolatedPoints[i][j][1], self.negInterpolatedPoints[i][j][2],
                        ] = [0, 255, 0, int(self.curAlpha)]
            self.updateCrosshairs()
            self.curPointsPlottedX = []; self.curPointsPlottedY = []
            self.planesDrawn.append([self.painted, self.paintedSlice])
            self.painted = "none"; self.paintedSlice = []
            self.curROIDrawn = True
            self.multiUseRoiButton.setText("Undo Last ROI")
            self.multiUseRoiButton.clicked.disconnect()
            self.multiUseRoiButton.clicked.connect(self.undoLastRoi)
            self.updateAdvancedRoiEditButtons()

    def updateAdvancedRoiEditButtons(self):
        if not self.continueButton.isHidden() or not np.amax(self.maskCoverImg): # if 3D VOI interpolation is complete
            with suppress(TypeError): self.advancedRoiEditAxButton.clicked.disconnect()
            with suppress(TypeError): self.advancedRoiEditSagButton.clicked.disconnect()
            with suppress(TypeError): self.advancedRoiEditCorButton.clicked.disconnect()
            self.advancedRoiEditAxButton.setStyleSheet("color: white; font-size: 16px; background: rgb(255, 37, 14); border-radius: 15px;")
            self.advancedRoiEditSagButton.setStyleSheet("color: white; font-size: 16px; background: rgb(255, 37, 14); border-radius: 15px;")
            self.advancedRoiEditCorButton.setStyleSheet("color: white; font-size: 16px; background: rgb(255, 37, 14); border-radius: 15px;")
            return

        if len(self.planesDrawn) and self.painted == "none" and "ax" in np.array(self.planesDrawn, dtype=object)[:,0]:
            self.advancedRoiEditAxButton.clicked.connect(self.axAdvancedRoiDraw)
            self.advancedRoiEditAxButton.setStyleSheet("color: white; font-size: 16px; background: rgb(0, 255, 71); border-radius: 15px;")
        else:
            with suppress(TypeError): self.advancedRoiEditAxButton.clicked.disconnect()
            self.advancedRoiEditAxButton.setStyleSheet("color: white; font-size: 16px; background: rgb(255, 37, 14); border-radius: 15px;")
        if len(self.planesDrawn) and self.painted == "none" and "sag" in np.array(self.planesDrawn, dtype=object)[:,0]:
            self.advancedRoiEditSagButton.clicked.connect(self.sagAdvancedRoiDraw)
            self.advancedRoiEditSagButton.setStyleSheet("color: white; font-size: 16px; background: rgb(0, 255, 71); border-radius: 15px;")
        else:
            with suppress(TypeError): self.advancedRoiEditSagButton.clicked.disconnect()
            self.advancedRoiEditSagButton.setStyleSheet("color: white; font-size: 16px; background: rgb(255, 37, 14); border-radius: 15px;")
        if len(self.planesDrawn) and self.painted == "none" and "cor" in np.array(self.planesDrawn, dtype=object)[:,0]:
            self.advancedRoiEditCorButton.clicked.connect(self.corAdvancedRoiDraw)
            self.advancedRoiEditCorButton.setStyleSheet("color: white; font-size: 16px; background: rgb(0, 255, 71); border-radius: 15px;")
        else:
            with suppress(TypeError): self.advancedRoiEditCorButton.clicked.disconnect()
            self.advancedRoiEditCorButton.setStyleSheet("color: white; font-size: 16px; background: rgb(255, 37, 14); border-radius: 15px;")

    def undoLastPoint(self):
        if len(self.curPointsPlottedX) != 0:
            self.maskCoverImg[self.curPointsPlottedX[-1]]
            self.curPointsPlottedX.pop()
            self.curPointsPlottedY.pop()
            self.maskCoverImg.fill(0)
            for i in range(len(self.interpolatedPoints)):
                for j in range(len(self.interpolatedPoints[i])):
                    self.maskCoverImg[
                        self.interpolatedPoints[i][j][0],
                        self.interpolatedPoints[i][j][1],
                        self.interpolatedPoints[i][j][2],
                    ] = [0, 0, 255, int(self.curAlpha)]
            for i in range(len(self.curPointsPlottedX)):
                if self.painted == "ax":
                    if self.drawingNeg:
                        self.maskCoverImg[
                            int(self.curPointsPlottedX[i]),
                            int(self.curPointsPlottedY[i]),
                            self.newZVal,
                        ] = [0, 255, 0, int(self.curAlpha)]
                    else:
                        self.maskCoverImg[
                            int(self.curPointsPlottedX[i]),
                            int(self.curPointsPlottedY[i]),
                            self.newZVal,
                        ] = [0, 0, 255, int(self.curAlpha)]
                elif self.painted == "sag":
                    if self.drawingNeg:
                        self.maskCoverImg[
                            self.newXVal,
                            int(self.curPointsPlottedY[i]),
                            int(self.curPointsPlottedX[i]),
                        ] = [0, 255, 0, int(self.curAlpha)]
                    else:
                        self.maskCoverImg[
                            self.newXVal,
                            int(self.curPointsPlottedY[i]),
                            int(self.curPointsPlottedX[i]),
                        ] = [0, 0, 255, int(self.curAlpha)]
                elif self.painted == "cor":
                    if self.drawingNeg:
                        self.maskCoverImg[
                            int(self.curPointsPlottedX[i]),
                            self.newYVal,
                            int(self.curPointsPlottedY[i]),
                        ] = [0, 255, 0, int(self.curAlpha)]
                    else:
                        self.maskCoverImg[
                            int(self.curPointsPlottedX[i]),
                            self.newYVal,
                            int(self.curPointsPlottedY[i]),
                        ] = [0, 0, 255, int(self.curAlpha)]

            self.updateCrosshairs()
        if not len(self.curPointsPlottedX):
            self.painted = "none"; self.paintedSlice = []
            self.scrollPaused = False

    def moveToTic(self):
        del self.ticAnalysisGui
        self.ticAnalysisGui = TicAnalysisGUI()
        if self.bmode4dImg is not None:
            self.ticAnalysisGui.toggleButton.show()
            if self.toggleButton.isChecked():
                self.ticAnalysisGui.toggleButton.setChecked(True)
        self.ticAnalysisGui.timeLine = None
        self.computeTic()
        self.voiAlphaSpinBox.setValue(100)
        self.ticAnalysisGui.interpolatedPoints = self.interpolatedPoints
        self.ticAnalysisGui.voxelScale = self.voxelScale
        self.ticAnalysisGui.ceus4dImg = self.ceus4dImg
        self.ticAnalysisGui.bmode4dImg = self.bmode4dImg
        self.ticAnalysisGui.data4dImg = self.data4dImg
        self.ticAnalysisGui.curSliceIndex = self.curSliceIndex
        self.ticAnalysisGui.newXVal = self.newXVal
        self.ticAnalysisGui.newYVal = self.newYVal
        self.ticAnalysisGui.newZVal = self.newZVal
        self.ticAnalysisGui.x = self.x
        self.ticAnalysisGui.y = self.y
        self.ticAnalysisGui.z = self.z
        self.ticAnalysisGui.maskCoverImg = self.maskCoverImg
        self.ticAnalysisGui.sliceArray = self.sliceArray
        self.ticAnalysisGui.lastGui = self
        self.ticAnalysisGui.imagePathInput.setText(self.imagePathInput.text())
        self.ticAnalysisGui.updateCrosshairs()
        self.ticAnalysisGui.show()
        self.ticAnalysisGui.resize(self.size())
        self.hide()

    def backToPrevVoi(self):
        if len(self.prevInterpolatedPoints):
            self.interpolatedPoints = self.prevInterpolatedPoints
            self.prevInterpolatedPoints = []
            self.backToPrevVoiButton.hide()
            for i in range(len(self.interpolatedPoints)):
                for j in range(len(self.interpolatedPoints[i])):
                    self.maskCoverImg[self.interpolatedPoints[i][j][0], self.interpolatedPoints[i][j][1], self.interpolatedPoints[i][j][2],
                    ] = [0, 0, 255, int(self.curAlpha)]
            self.alphaValueChanged()

    def startRoiDraw(self):
        if self.drawRoiButton.isChecked():
            self.multiUseRoiButton.setText("Close ROI")
            try:
                self.multiUseRoiButton.clicked.disconnect()
            except:
                pass
            self.multiUseRoiButton.clicked.connect(self.acceptRoi)
            self.observingLabel.show(); self.navigatingLabel.hide()
            self.axialPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.sagPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.corPlane.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        elif not len(self.curPointsPlottedX):
            self.multiUseRoiButton.setText("Undo Last ROI")
            try:
                self.multiUseRoiButton.clicked.disconnect()
            except:
                pass
            self.multiUseRoiButton.clicked.connect(self.undoLastRoi)
        self.scrollPaused = False

    def undoLastRoi(self):
        if len(self.planesDrawn):
            self.planesDrawn.pop()
            self.maskCoverImg.fill(0)
            if not self.drawingNeg:
                self.interpolatedPoints.pop()
            for i in range(len(self.interpolatedPoints)):
                for j in range(len(self.interpolatedPoints[i])):
                    self.maskCoverImg[
                        self.interpolatedPoints[i][j][0],
                        self.interpolatedPoints[i][j][1],
                        self.interpolatedPoints[i][j][2],
                    ] = [0, 0, 255, int(self.curAlpha)]
            if self.drawingNeg:
                self.negInterpolatedPoints.pop()
                for i in range(len(self.negInterpolatedPoints)):
                    for j in range(len(self.negInterpolatedPoints[i])):
                        self.maskCoverImg[self.negInterpolatedPoints[i][j][0], self.negInterpolatedPoints[i][j][1], self.negInterpolatedPoints[i][j][2],
                        ] = [0, 255, 0, int(self.curAlpha)]
            self.updateCrosshairs()

    def complete3dInterpolation(self):
        if len(self.planesDrawn):
            pointsPlotted = self.negInterpolatedPoints if self.drawingNeg else self.interpolatedPoints
            if len(self.planesDrawn) >= 3:
                points = calculateSpline3D(
                    list(chain.from_iterable(pointsPlotted))
                )
            elif len(self.planesDrawn) == 2:
                return
            else:
                points = set()
                for group in np.array(pointsPlotted):
                    for point in group:
                        points.add(tuple(point))

            pointsPlotted = []
            if not self.drawingNeg:
                self.maskCoverImg.fill(0)

            for point in points:
                if max(self.data4dImg[tuple(point)]) != 0:
                    if self.drawingNeg:
                        self.maskCoverImg[tuple(point)] = [0, 0, 0, 0]
                    else:
                        self.maskCoverImg[tuple(point)] = [0, 0, 255, int(self.curAlpha)]
                    pointsPlotted.append(tuple(point))
            if len(self.interpolatedPoints) == 0:
                print("VOI not in US image.\nDraw new VOI over US image")
                self.maskCoverImg.fill(0)
                self.updateCrosshairs()
                return
            
            mask = np.zeros((self.maskCoverImg.shape[0], self.maskCoverImg.shape[1], self.maskCoverImg.shape[2]))

            for point in pointsPlotted:
                mask[point] = 1
            for i in range(mask.shape[2]):
                border = np.where(mask[:, :, i] == 1)
                if (
                    (not len(border[0]))
                    or (max(border[0]) == min(border[0]))
                    or (max(border[1]) == min(border[1]))
                ):
                    continue
                border = np.array(border).T
                hull = ConvexHull(border)
                vertices = border[hull.vertices]
                shape = vertices.shape
                vertices = np.reshape(
                    np.append(vertices, vertices[0]), (shape[0] + 1, shape[1])
                )

                # Linear interpolation of 2d convex hull
                tck, _ = interpolate.splprep(vertices.T, s=0.0, k=1)
                splineX, splineY = np.array(
                    interpolate.splev(np.linspace(0, 1, 1000), tck)
                )

                mask[:, :, i] = np.zeros((mask.shape[0], mask.shape[1]))
                for j in range(len(splineX)):
                    mask[int(splineX[j]), int(splineY[j]), i] = 1
                filledMask = binary_fill_holes(mask[:, :, i])
                mask[:, :, i] = binary_fill_holes(mask[:, :, i])
                maskPoints = np.array(np.where(filledMask > 0))
                for j in range(len(maskPoints[0])):
                    if self.drawingNeg:
                        self.maskCoverImg[maskPoints[0][j], maskPoints[1][j], i] = [0]*4
                    else:
                        self.maskCoverImg[maskPoints[0][j], maskPoints[1][j], i] = [0, 0, 255, int(self.curAlpha)]
                        # self.interpolatedPoints.append((maskPoints[0][j], maskPoints[1][j], i))

            if self.drawingNeg:
                self.prevInterpolatedPoints = self.interpolatedPoints
                self.backToPrevVoiButton.show()
                self.drawingNeg = False
                
            self.interpolatedPoints = [np.transpose(np.where(self.maskCoverImg[:,:,:,2] == 255))]

            self.hideDrawVoiLayout()
            self.showVoiDecisionLayout()
            self.showVoiAlphaLayout()
            self.updateCrosshairs()

    def voi3dInterpolation(self):
        if len(self.planesDrawn):
            self.loadingGUI.show()
            QApplication.processEvents() # quick solution --> not most robust but doesn't affect this use case outside of GIF
            self.complete3dInterpolation()
            self.loadingGUI.hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = VoiSelectionGUI()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())
