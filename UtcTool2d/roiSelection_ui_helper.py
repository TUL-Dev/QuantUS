from UtcTool2d.roiSelection_ui import *
from UtcTool2d.editImageDisplay_ui_helper import *
from UtcTool2d.analysisParamsSelection_ui_helper import *
from UtcTool2d.loadRoi_ui_helper import *
import Parsers.philipsMatParser as matParser
import Parsers.siemensRfdParser as rfdParser
import Parsers.terasonRfParser as tera
from Parsers.philipsRfParser import main_parser_stanford

import pydicom
import os
import numpy as np
from PIL import Image, ImageEnhance
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib
import scipy.interpolate as interpolate
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtCore import QLine, Qt

import platform
system = platform.system()


class RoiSelectionGUI(QWidget, Ui_constructRoi):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        if system == 'Windows':
            self.roiSidebarLabel.setStyleSheet("""QLabel { 
                font-size: 18px; 
                color: rgb(255, 255, 255); 
                background-color: rgba(255, 255, 255, 0); 
                border: 0px; 
                font-weight: bold; 
            }""")
            self.imageSelectionLabelSidebar.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }""")
            self.imageLabel.setStyleSheet("""QLabel {
                font-size: 13px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }""")
            self.phantomLabel.setStyleSheet("""QLabel {
                font-size: 13px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }""")
            self.imagePathInput.setStyleSheet("""QLabel {
                font-size: 11px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
            }""")
            self.phantomPathInput.setStyleSheet("""QLabel {
                font-size: 11px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
            }""")
            self.analysisParamsLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }""")
            self.rfAnalysisLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }""")
            self.exportResultsLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }""")

        self.curPointsPlottedX = []
        self.curPointsPlottedY = []
        self.oldSpline = []
        self.multipleFrames = False
        self.imagePathInput.setHidden(True)
        self.phantomPathInput.setHidden(True)
        self.ofFramesLabel.setHidden(True)
        self.curFrameLabel.setHidden(True)
        self.totalFramesLabel.setHidden(True)
        self.curFrameSlider.setHidden(True)
        self.drawRoiButton.setHidden(True)
        self.closeRoiButton.setHidden(True)
        self.undoLastPtButton.setHidden(True)
        self.redrawRoiButton.setHidden(True)
        self.acceptRoiButton.setHidden(True)
        self.drawRectButton.setHidden(True)
        self.redrawRectButton.setHidden(True)
        self.acceptRectButton.setHidden(True)
        self.undoLoadedRoiButton.setHidden(True)
        self.acceptLoadedRoiButton.setHidden(True)
        self.acceptLoadedRoiButton.clicked.connect(self.acceptROI)
        self.undoLoadedRoiButton.clicked.connect(self.undoRoiLoad)

        self.loadRoiGUI = LoadRoiGUI()

        self.editImageDisplayButton.setHidden(True)

        self.imCoverPixmap = QPixmap(721, 501)
        self.imCoverPixmap.fill(Qt.transparent)
        self.imCoverFrame.setPixmap(self.imCoverPixmap)

        self.lastGui = None
        self.imArray = None
        self.axOverlapVal = None
        self.latOverlapVal = None
        self.minFreqVal = None
        self.maxFreqVal = None
        self.startDepthVal = None
        self.endDepthVal = None
        self.clipFactorVal = None
        self.samplingFreqVal = None
        self.analysisParamsGUI = None
        self.maskCoverImg = None
        self.dataFrame = None

        self.scatteredPoints = []
        
        self.undoLastPtButton.clicked.connect(self.undoLastPt)
        self.closeRoiButton.clicked.connect(self.closeInterpolation)
        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.acceptRoiButton.clicked.connect(self.acceptROI)
        self.backButton.clicked.connect(self.backToLastScreen)
        self.newRoiButton.clicked.connect(self.drawNewRoi)
        self.loadRoiButton.clicked.connect(self.openLoadRoiWindow)

        self.rectRoiButton.clicked.connect(self.drawRectRoi)
        # self.drawRectButton.clicked.connect(self.recordDrawRectClicked)
        self.redrawRectButton.clicked.connect(self.clearRect)
        self.acceptRectButton.clicked.connect(self.acceptRect)
    
    def undoRoiLoad(self):
        self.undoLoadedRoiButton.setHidden(True)
        self.acceptLoadedRoiButton.setHidden(True)
        self.loadRoiButton.setHidden(False)
        self.newRoiButton.setHidden(False)

        self.undoLastRoi()

    def openLoadRoiWindow(self):
        self.loadRoiGUI.chooseRoiGUI = self
        self.hide()
        self.loadRoiGUI.show()

    def drawNewRoi(self):
        self.newRoiButton.setHidden(True)
        self.rectRoiButton.setHidden(True)
        self.loadRoiButton.setHidden(True)
        self.drawRoiButton.setHidden(False)
        self.undoLastPtButton.setHidden(False)
        self.closeRoiButton.setHidden(False)
        self.acceptRoiButton.setHidden(False)
    
    def drawRectRoi(self):
        self.newRoiButton.setHidden(True)
        self.rectRoiButton.setHidden(True)
        self.loadRoiButton.setHidden(True)
        self.drawRectButton.setHidden(False)
        self.redrawRectButton.setHidden(False)
        self.acceptRectButton.setHidden(False)

    def backToLastScreen(self):
        self.lastGui.dataFrame = self.dataFrame
        self.lastGui.show()
        self.hide()

    def mousePressEvent(self,event):
        self.xCur = event.x()
        self.yCur = event.y()
        if self.drawRoiButton.isChecked():
            # Plot ROI points
            if self.xCur < self.xBorderMax and self.xCur > self.xBorderMin and self.yCur < self.yBorderMax and self.yCur > self.yBorderMin:
                plotX = self.xCur - 401
                plotY = self.yCur - 171
            else:
                return
            self.curPointsPlottedX.append(plotX)
            self.curPointsPlottedY.append(plotY)
            self.updateSpline()
<<<<<<< HEAD
        if self.drawRectButton.isChecked():
=======
        elif self.drawRectButton.isChecked():
>>>>>>> 26f306db3fd746efd9f22f176306475dbce85142
            if self.xCur < self.xBorderMax and self.xCur > self.xBorderMin and self.yCur < self.yBorderMax and self.yCur > self.yBorderMin:
                plotX = self.xCur - 401
                plotY = self.yCur - 171
            else:
                return
<<<<<<< HEAD
            self.addRectPoint(plotX, plotY)
=======
            if len(self.curPointsPlottedX) < 2:
                self.curPointsPlottedX.append(int(plotX))
                self.curPointsPlottedY.append(int(plotY))
                self.updateRect()

            self.plotOnCanvas()
>>>>>>> 26f306db3fd746efd9f22f176306475dbce85142

    def updateSpline(self):
        self.maskCoverImg.fill(0)
        if len(self.curPointsPlottedX) > 0:            
            if len(self.curPointsPlottedX) > 1:
                xSpline, ySpline = calculateSpline(self.curPointsPlottedX, self.curPointsPlottedY)
                spline = [(int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))]
                spline = np.array([*set(spline)])
                xSpline, ySpline = np.transpose(spline)
                xSpline = np.clip(xSpline, a_min=round(self.xBorderMin - 400)+1, a_max=720 + round(self.xBorderMax - 1121))
                ySpline = np.clip(ySpline, a_min=round(self.yBorderMin - 170)+1, a_max=500 + round(self.yBorderMax - 671))
                for i in range(len(xSpline)):
                    self.maskCoverImg[ySpline[i]-1:ySpline[i]+2, xSpline[i]-1:xSpline[i]+2] = [255, 255, 0, 255]

            for i in range(len(self.curPointsPlottedX)):
                self.maskCoverImg[self.curPointsPlottedY[i]-2:self.curPointsPlottedY[i]+3, \
                                    self.curPointsPlottedX[i]-2:self.curPointsPlottedX[i]+3] = [0,0,255, 255]

        self.plotOnCanvas()
        # self.updateCrosshair()
    
    def updateRect(self):
        self.maskCoverImg.fill(0)
        if len(self.curPointsPlottedX) > 0:            
            if len(self.curPointsPlottedX) > 1:
                if self.curPointsPlottedX[0] == self.curPointsPlottedX[1]:
                    self.curPointsPlottedX[1] += 1
                if self.curPointsPlottedY[0] == self.curPointsPlottedY[1]:
                    self.curPointsPlottedY[1] += 1
                # rectXs = [min(self.curPointsPlottedX), max(self.curPointsPlottedX), max(self.curPointsPlottedX), min(self.curPointsPlottedX), min(self.curPointsPlottedX)]
                # rectYs = [min(self.curPointsPlottedY), min(self.curPointsPlottedY), max(self.curPointsPlottedY), max(self.curPointsPlottedY), min(self.curPointsPlottedY)]
                min_x = min(self.curPointsPlottedX)
                max_x = max(self.curPointsPlottedX)
                min_y = min(self.curPointsPlottedY)
                max_y = max(self.curPointsPlottedY)
                for x in range(min_x, max_x + 1):
                    self.maskCoverImg[min_y, x] = [0, 255, 255, 255]
                    self.maskCoverImg[max_y, x] = [0, 255, 255, 255]

                for y in range(min_y, max_y + 1):
                    self.maskCoverImg[y, min_x] = [0, 255, 255, 255]
                    self.maskCoverImg[y, max_x] = [0, 255, 255, 255]

            for i in range(len(self.curPointsPlottedX)):
                self.maskCoverImg[self.curPointsPlottedY[i]-2:self.curPointsPlottedY[i]+3, \
                                    self.curPointsPlottedX[i]-2:self.curPointsPlottedX[i]+3] = [0,0,255, 255]

        self.plotOnCanvas()
        # self.updateCrosshair()

    def mouseMoveEvent(self, event):
        self.xCur = event.x()
        self.yCur = event.y()
        # self.updateCrosshair()

    # def updateCrosshair(self):
    #     if self.xCur < 1121 and self.xCur > 400 and self.yCur < 671 and self.yCur > 170:
    #         plotX = self.xCur - 401
    #     else:
    #         return
        
    #     plotY = self.yCur - 171
    #     self.imCoverFrame.pixmap().fill(Qt.transparent)
    #     painter = QPainter(self.imCoverFrame.pixmap())
    #     painter.setPen(Qt.yellow)
    #     bmodeVertLine = QLine(plotX, 0, plotX, 501)
    #     bmodeLatLine = QLine(0, plotY, 721, plotY)
    #     painter.drawLines([bmodeVertLine, bmodeLatLine])
    #     painter.end()
    #     self.update()

    def setFilenameDisplays(self, imageName, phantomName):
        self.imagePathInput.setHidden(False)
        self.phantomPathInput.setHidden(False)
        self.imagePathInput.setText(imageName)
        self.phantomPathInput.setText(phantomName)
    
    def plotOnCanvas(self): # Plot current image on GUI
        if self.multipleFrames:
            self.imData = np.array(self.imArray[self.frame]).reshape(self.arHeight, self.arWidth)
        self.imData = np.require(self.imData,np.uint8,'C')
        self.bytesLine = self.imData.strides[0]
        self.arHeight = self.imData.shape[0]
        self.arWidth = self.imData.shape[1]

        self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, 'C')
        self.bytesLineMask, _ = self.maskCoverImg[:,:,0].strides
        self.qImgMask = QImage(self.maskCoverImg, self.maskCoverImg.shape[1], self.maskCoverImg.shape[0], self.bytesLineMask, QImage.Format_ARGB32)

        self.imMaskFrame.setPixmap(QPixmap.fromImage(self.qImgMask).scaled(721, 501))

        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8)
        self.imDisplayFrame.setPixmap(QPixmap.fromImage(self.qIm).scaled(self.widthScale, self.depthScale))

    def openPhilipsImage(self, imageFilePath, phantomFilePath):
        tmpLocation = imageFilePath.split("/")
        dataFileName = tmpLocation[-1]
        dataFileLocation = imageFilePath[:len(imageFilePath)-len(dataFileName)]
        tmpPhantLocation = phantomFilePath.split("/")
        phantFileName = tmpPhantLocation[-1]
        phantFileLocation = phantomFilePath[:len(phantomFilePath)-len(phantFileName)]
        if dataFileName[-3:] == ".rf":
            dataFile = open(imageFilePath, 'rb')
            datasig = list(dataFile.read(8))
            if datasig != [0,0,0,0,255,255,0,0]: # Philips signature parameters
                # self.invalidPath.setText("Data and Phantom files are both invalid.\nPlease use Philips .rf files.")
                return
            elif datasig != [0,0,0,0,255,255,0,0]:
                # self.invalidPath.setText("Invalid phantom file.\nPlease use Philips .rf files.")
                return
            else: # Display Philips image and assign relevant default analysis
                main_parser_stanford(imageFilePath) # parse image filee

                dataFileName = str(dataFileLocation[:-3]+'.mat')
        if phantFileName[-3:] == ".rf": # Check binary signatures at start of .rf files
            phantFile = open(phantomFilePath, 'rb')
            phantsig = list(phantFile.read(8))
            if phantsig != [0,0,0,0,255,255,0,0]: # Philips signature parameters
                # self.invalidPath.setText("Data and Phantom files are both invalid.\nPlease use Philips .rf files.")
                return
            elif phantsig != [0,0,0,0,255,255,0,0]:
                # self.invalidPath.setText("Invalid phantom file.\nPlease use Philips .rf files.")
                return
            else: # Display Philips image and assign relevant default analysis
                main_parser_stanford(imageFilePath) # parse image filee

                phantFileName = str(phantFileName[:-3]+'.mat')

        # Display Philips image and assign relevant default analysis params
        self.frame = None
        self.imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = matParser.getImage(dataFileName, dataFileLocation, phantFileName, phantFileLocation, self.frame)
        self.arHeight = self.imArray.shape[0]
        self.arWidth = self.imArray.shape[1]
        self.imData = np.array(self.imArray)
        self.imData = np.require(self.imData,np.uint8,'C')
        self.maskCoverImg = np.zeros([501, 721, 4]) # Hard-coded values match size of frame on GUI
        self.bytesLine = self.imData.strides[0]

        quotient = self.imgInfoStruct.width / self.imgInfoStruct.depth
        if quotient > (721/501):
            self.widthScale = 721
            self.depthScale = self.widthScale / (self.imgInfoStruct.width/self.imgInfoStruct.depth)
        else:
            self.widthScale = 501 * quotient
            self.depthScale = 501
        self.yBorderMin = 170 + ((501 - self.depthScale)/2)
        self.yBorderMax = 671 - ((501 - self.depthScale)/2)
        self.xBorderMin = 400 + ((721 - self.widthScale)/2)
        self.xBorderMax = 1121 - ((721 - self.widthScale)/2)

        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8).scaled(self.widthScale, self.depthScale)

        self.imDisplayFrame.setPixmap(QPixmap.fromImage(self.qIm).scaled(self.widthScale, self.depthScale))

        self.pixSizeAx = self.imgDataStruct.bMode.shape[0] #were both scBmode
        self.pixSizeLat = self.imgDataStruct.bMode.shape[1]

        self.axOverlapVal = 50
        self.latOverlapVal = 50
        self.minFreqVal = 3
        self.maxFreqVal = 4.5
        self.startDepthVal = 0.04
        self.endDepthVal = 0.16
        self.clipFactorVal = 95
        self.samplingFreqVal = 20

        self.plotOnCanvas()

    def openSiemensImage(self, imageFilePath, phantomFilePath):
        tmpLocation = imageFilePath.split("/")
        dataFileName = tmpLocation[-1]
        dataFileLocation = imageFilePath[:len(imageFilePath)-len(dataFileName)]
        tmpPhantLocation = phantomFilePath.split("/")
        phantFileName = tmpPhantLocation[-1]
        phantFileLocation = phantomFilePath[:len(phantomFilePath)-len(phantFileName)]

        self.imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = rfdParser.getImage(dataFileName, dataFileLocation, phantFileName, phantFileLocation)
        self.frame = 0
        self.imData = np.array(self.imArray[self.frame]).reshape(self.imArray.shape[1], self.imArray.shape[2])
        self.imData = np.require(self.imData,np.uint8,'C')
        self.maskCoverImg = np.zeros([501, 721, 4]) # Hard-coded values match size of frame on GUI
        self.bytesLine = self.imData.strides[0]
        self.arHeight = self.imData.shape[0]
        self.arWidth = self.imData.shape[1]
        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8)

        quotient = self.imgInfoStruct.width / self.imgInfoStruct.depth
        if quotient > (721/501):
            self.widthScale = 721
            self.depthScale = self.widthScale / (self.imgInfoStruct.width/self.imgInfoStruct.depth)
        else:
            self.widthScale = 501 * quotient
            self.depthScale = 501
        self.yBorderMin = 170 + ((501 - self.depthScale)/2)
        self.yBorderMax = 671 - ((501 - self.depthScale)/2)
        self.xBorderMin = 400 + ((721 - self.widthScale)/2)
        self.xBorderMax = 1121 - ((721 - self.widthScale)/2)

        self.imDisplayFrame.setPixmap(QPixmap.fromImage(self.qIm).scaled(self.widthScale, self.depthScale))

        self.pixSizeAx = self.imgDataStruct.bMode.shape[1] #were both scBmode
        self.pixSizeLat = self.imgDataStruct.bMode.shape[2]

        self.ofFramesLabel.setHidden(False)
        self.curFrameLabel.setHidden(False)
        self.totalFramesLabel.setHidden(False)
        self.curFrameSlider.setHidden(False)
        self.curFrameSlider.setMaximum(self.imArray.shape[0]-1)
        self.totalFramesLabel.setText(str(self.imArray.shape[0]-1))
        self.curFrameSlider.valueChanged.connect(self.curFrameChanged)

        self.axOverlapVal = 50
        self.latOverlapVal = 50
        self.startDepthVal = 0.04
        self.endDepthVal = 0.16
        self.clipFactorVal = 95
        self.minFreqVal = 7
        self.maxFreqVal = 17
        self.samplingFreqVal = 40
        self.multipleFrames = True
        self.physicalDepthVal.setText(str(np.round(self.imgInfoStruct.depth, decimals=2)))
        self.physicalWidthVal.setText(str(np.round(self.imgInfoStruct.width, decimals=2)))
        self.pixelWidthVal.setText(str(self.imArray.shape[2]))
        self.pixelDepthVal.setText(str(self.imArray.shape[1]))

        self.plotOnCanvas()

    def openTerasonImage(self, imageFilePath, phantomFilePath):
        self.imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = tera.getImage(imageFilePath, phantomFilePath)

        quotient = self.imgInfoStruct.width / self.imgInfoStruct.depth
        if quotient > (721/501):
            self.widthScale = 721
            self.depthScale = self.widthScale / (self.imgInfoStruct.width/self.imgInfoStruct.depth)
        else:
            self.widthScale = 501 * quotient
            self.depthScale = 501
        self.maskCoverImg = np.zeros([501, 721, 4]) # Hard-coded values match size of frame on GUI
        self.yBorderMin = 170 + ((501 - self.depthScale)/2)
        self.yBorderMax = 671 - ((501 - self.depthScale)/2)
        self.xBorderMin = 400 + ((721 - self.widthScale)/2)
        self.xBorderMax = 1121 - ((721 - self.widthScale)/2)
            

        self.arHeight = self.imArray.shape[0]
        self.arWidth = self.imArray.shape[1]
        self.imData = np.array(self.imArray)
        self.imData = np.require(self.imData,np.uint8,'C')
        self.bytesLine = self.imData.strides[0]
        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8).scaled(self.widthScale, self.depthScale)

        self.imDisplayFrame.setPixmap(QPixmap.fromImage(self.qIm).scaled(self.widthScale, self.depthScale))

        self.pixSizeAx = self.imArray.shape[0]
        self.pixSizeLat = self.imArray.shape[1]
        self.axOverlapVal = 50
        self.latOverlapVal = 50
        self.minFreqVal = 3
        self.maxFreqVal = 4.5
        self.startDepthVal = 0.04
        self.endDepthVal = 0.16
        self.clipFactorVal = 95
        self.samplingFreqVal = 20
        self.frame = None
        self.physicalDepthVal.setText(str(np.round(self.imgInfoStruct.depth, decimals=2)))
        self.physicalWidthVal.setText(str(np.round(self.imgInfoStruct.width, decimals=2)))
        self.pixelWidthVal.setText(str(self.imArray.shape[1]))
        self.pixelDepthVal.setText(str(self.imArray.shape[0]))


        self.plotOnCanvas()
        

    def curFrameChanged(self):
        self.frame = self.curFrameSlider.value()
        self.curFrameLabel.setText(str(self.frame))
        self.plotOnCanvas()

    def closeInterpolation(self): # Finish drawing ROI
        if len(self.curPointsPlottedX) > 2:
            self.drawRoiButton.setChecked(False)

            # remove duplicate points
            points = np.transpose(np.array([self.curPointsPlottedX, self.curPointsPlottedY]))
            points = removeDuplicates(points)
            [self.curPointsPlottedX, self.curPointsPlottedY] = np.transpose(points)
            self.curPointsPlottedX = list(self.curPointsPlottedX)
            self.curPointsPlottedY = list(self.curPointsPlottedY)
            self.curPointsPlottedX.append(self.curPointsPlottedX[0])
            self.curPointsPlottedY.append(self.curPointsPlottedY[0])
            self.maskCoverImg.fill(0)

            xSpline, ySpline = calculateSpline(self.curPointsPlottedX, self.curPointsPlottedY)
            xSpline = np.clip(xSpline, a_min=round(self.xBorderMin - 400)+1, a_max=720 + round(self.xBorderMax - 1121))
            ySpline = np.clip(ySpline, a_min=round(self.yBorderMin - 170)+1, a_max=500 + round(self.yBorderMax - 671))
            self.xSpline = xSpline
            self.ySpline = ySpline
            spline = [(int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))]
            spline = np.array([*set(spline)])
            xSpline, ySpline = np.transpose(spline)
            for i in range(len(xSpline)):
                self.maskCoverImg[ySpline[i]-1:ySpline[i]+2, xSpline[i]-1:xSpline[i]+2] = [0, 0, 255, 255]
            self.drawRoiButton.setChecked(False)
            self.drawRoiButton.setCheckable(False)
            self.redrawRoiButton.setHidden(False)
            self.closeRoiButton.setHidden(True)
            self.plotOnCanvas()

    def undoLastPt(self):
        if len(self.curPointsPlottedX):
            self.maskCoverImg[self.curPointsPlottedX[-1]-2:self.curPointsPlottedX[-1]+3, \
                            self.curPointsPlottedY[-1]-2:self.curPointsPlottedY[-1]+3] = [0,0,0,0]
            self.curPointsPlottedX.pop()
            self.curPointsPlottedY.pop()
            self.updateSpline()

    def undoLastRoi(self):
        if not self.drawRoiButton.isCheckable() or self.drawRoiButton.isHidden():
            self.curPointsPlottedX = []
            self.curPointsPlottedY = []
            self.drawRoiButton.setCheckable(True)
            self.redrawRoiButton.setHidden(True)
            self.closeRoiButton.setHidden(False)
            self.maskCoverImg.fill(0)
            self.plotOnCanvas()
            self.update()
    
    # def recordDrawRectClicked(self):
    #     if self.drawRectButton.isChecked(): # Set up b-mode to be drawn on
    #         # image, =self.ax.plot([], [], marker="o",markersize=3, markerfacecolor="red")
    #         # self.cid = image.figure.canvas.mpl_connect('button_press_event', self.interpolatePoints)
    #         self.cid = self.figure.canvas.mpl_connect('button_press_event', self.addRectPoint)
    #         self.cursor.set_active(True)
    #     else: # No longer let b-mode be drawn on
    #         self.cid = self.figure.canvas.mpl_disconnect(self.cid)
    #         self.cursor.set_active(False)
    #     self.canvas.draw()

    # def addRectPoint(self, event):
    #     try:
    #         if self.imgInfoStruct.numSamplesDrOut == 1400:
    #             # Preset 1 boundaries for 20220831121844_IQ.bin
    #             leftSlope = (500 - 0)/(154.22 - 148.76)
    #             pointSlopeLeft = (event.ydata - 0) / (event.xdata - 148.76)
    #             if pointSlopeLeft <= 0 or leftSlope < pointSlopeLeft:
    #                 return

    #             bottomSlope = (386.78 - 358.38) / (716 - 0)
    #             pointSlopeBottom = (event.ydata - 358.38) / (event.xdata - 0)
    #             rightSlope = (500 - 0) / (509.967 - 572.47)
    #             pointSlopeRight = (event.ydata - 0) / (event.xdata - 572.47)

    #         elif self.imgInfoStruct.numSamplesDrOut == 1496:
    #             # Preset 2 boundaries for 20220831121752_IQ.bin
    #             leftSlope = (500 - 0) / (120.79 - 146.9)
    #             pointSlopeLeft = (event.ydata - 0) / (event.xdata - 146.9)
    #             if pointSlopeLeft > leftSlope and pointSlopeLeft <= 0:
    #                 return

    #             bottomSlope = (500 - 462.41) / (644.76 - 0)
    #             pointSlopeBottom = (event.ydata - 462.41) / (event.xdata - 0)
    #             rightSlope = (500 - 0) / (595.84 - 614.48)
    #             pointSlopeRight = (event.ydata - 0) / (event.xdata - 614.48)

    #         else:
    #             print("Preset not found!")
    #             return

    #         if pointSlopeBottom > bottomSlope:
    #                 return
    #         if pointSlopeRight >= 0 or pointSlopeRight < rightSlope:
    #             return
    #     except:
    #         pass

    #     self.pointsPlottedX.append(int(event.xdata))
    #     self.pointsPlottedY.append(int(event.ydata))
    #     self.scatteredPoints.append(self.ax.scatter(self.pointsPlottedX[-1], self.pointsPlottedY[-1], marker="o", s=0.5, c="red", zorder=500))

    #     assert(len(self.pointsPlottedX) == len(self.pointsPlottedY))

    #     if len(self.pointsPlottedX) == 1:
    #         pass
    #     elif len(self.pointsPlottedX) == 2:
    #         self.closeRect()
    #     else:
    #         print("Whoops, wrong number of rectangle points. This shouldn't have happened.")
    #         assert(False)

    #     self.canvas.draw()

    def clearRect(self):
        self.curPointsPlottedX = []
        self.curPointsPlottedY = []
        self.scatteredPoints = []
        self.drawRectButton.setChecked(False)
        self.drawRectButton.setCheckable(True)
        self.undoLastPtButton.clicked.connect(self.undoLastPt)
        self.plotOnCanvas()

    def acceptROI(self):
        if len(self.curPointsPlottedX) > 1 and self.curPointsPlottedX[-1] == self.curPointsPlottedX[0]:
            del self.analysisParamsGUI

            if self.multipleFrames:
                imData = np.array(self.imArray[self.frame]).reshape(self.arHeight, self.arWidth)
            else:
                imData = self.imArray
            imData = np.flipud(imData)
            imData = np.require(imData, np.uint8, 'C')
            bytesLine = imData.strides[0]
            arHeight = imData.shape[0]
            arWidth = imData.shape[1]
            savedIm = QImage(imData, arWidth, arHeight, bytesLine, QImage.Format_Grayscale8).scaled(self.widthScale, self.depthScale)

            savedIm.mirrored().save(os.path.join("Junk", "bModeImRaw.png"))
            savedIm.mirrored().save(os.path.join("Junk", "bModeIm.png"))
            self.analysisParamsGUI = AnalysisParamsGUI()
            self.analysisParamsGUI.finalSplineX = self.xSpline - ((721 - self.widthScale)/2)
            self.analysisParamsGUI.finalSplineY = self.ySpline - ((501 - self.depthScale)/2)
            self.analysisParamsGUI.curPointsPlottedX = self.curPointsPlottedX
            self.analysisParamsGUI.curPointsPlottedY = self.curPointsPlottedY
            self.analysisParamsGUI.frame = self.frame
            self.analysisParamsGUI.imArray = self.imArray
            self.analysisParamsGUI.dataFrame = self.dataFrame
            self.analysisParamsGUI.imageDepthVal.setText(str(np.round(self.imgInfoStruct.depth, decimals=1)))
            self.analysisParamsGUI.imageWidthVal.setText(str(np.round(self.imgInfoStruct.width, decimals=1)))

            speedOfSoundInTissue = 1540 #m/s
            self.waveLength = (speedOfSoundInTissue/self.imgInfoStruct.centerFrequency)*1000 #mm
            self.analysisParamsGUI.axWinSizeVal.setValue(self.waveLength*10)
            self.analysisParamsGUI.latWinSizeVal.setValue(self.waveLength*10)
            # self.analysisParamsGUI.yBorderMin = (721 - self.widthScale)/2
            # self.analysisParamsGUI.xBorderMin = (501 - self.depthScale)/2
            self.analysisParamsGUI.imWidthScale = self.widthScale
            self.analysisParamsGUI.imDepthScale = self.depthScale

            self.analysisParamsGUI.axOverlapVal.setValue(self.axOverlapVal)
            self.analysisParamsGUI.latOverlapVal.setValue(self.latOverlapVal)
            self.analysisParamsGUI.windowThresholdVal.setValue(95)
            self.analysisParamsGUI.minFreqVal.setValue(np.round(self.imgInfoStruct.minFrequency/1000000, decimals=2))
            self.analysisParamsGUI.maxFreqVal.setValue(np.round(self.imgInfoStruct.maxFrequency/1000000, decimals=2))
            self.analysisParamsGUI.lowBandFreqVal.setValue(np.round(self.imgInfoStruct.lowBandFreq/1000000, decimals=2))
            self.analysisParamsGUI.upBandFreqVal.setValue(np.round(self.imgInfoStruct.upBandFreq/1000000, decimals=2))
            self.analysisParamsGUI.samplingFreqVal.setValue(np.round(self.imgInfoStruct.samplingFrequency/1000000, decimals=2))
            self.analysisParamsGUI.setFilenameDisplays(self.imagePathInput.text().split('/')[-1], self.phantomPathInput.text().split('/')[-1])
            self.analysisParamsGUI.lastGui = self
            self.analysisParamsGUI.plotRoiPreview()
            self.analysisParamsGUI.show()
            self.hide()
    
<<<<<<< HEAD
    def addRectPoint(self, x_coord, y_coord):
        try:
            if self.imgInfoStruct.numSamplesDrOut == 1400:
                # Preset 1 boundaries for 20220831121844_IQ.bin
                leftSlope = (500 - 0)/(154.22 - 148.76)
                pointSlopeLeft = (y_coord - 0) / (x_coord - 148.76)
                if pointSlopeLeft <= 0 or leftSlope < pointSlopeLeft:
                    return

                bottomSlope = (386.78 - 358.38) / (716 - 0)
                pointSlopeBottom = (y_coord - 358.38) / (x_coord - 0)
                rightSlope = (500 - 0) / (509.967 - 572.47)
                pointSlopeRight = (y_coord - 0) / (x_coord - 572.47)

            elif self.imgInfoStruct.numSamplesDrOut == 1496:
                # Preset 2 boundaries for 20220831121752_IQ.bin
                leftSlope = (500 - 0) / (120.79 - 146.9)
                pointSlopeLeft = (y_coord - 0) / (x_coord - 146.9)
                if pointSlopeLeft > leftSlope and pointSlopeLeft <= 0:
                    return

                bottomSlope = (500 - 462.41) / (644.76 - 0)
                pointSlopeBottom = (y_coord - 462.41) / (x_coord - 0)
                rightSlope = (500 - 0) / (595.84 - 614.48)
                pointSlopeRight = (y_coord - 0) / (x_coord - 614.48)

            else:
                print("Preset not found!")
                return

            if pointSlopeBottom > bottomSlope:
                    return
            if pointSlopeRight >= 0 or pointSlopeRight < rightSlope:
                return
        except:
            pass

        self.curPointsPlottedX.append(int(x_coord))
        self.curPointsPlottedY.append(int(y_coord))
        # self.scatteredPoints.append(self.ax.scatter(self.curPointsPlottedX[-1], self.curPointsPlottedY[-1], marker="o", s=0.5, c="red", zorder=500))
        for i in range(len(self.curPointsPlottedX)):
            self.maskCoverImg[self.curPointsPlottedY[i]-2:self.curPointsPlottedY[i]+3, \
                                self.curPointsPlottedX[i]-2:self.curPointsPlottedX[i]+3] = [0,0,255, 255]

        assert(len(self.curPointsPlottedX) == len(self.curPointsPlottedY))

        if len(self.curPointsPlottedX) == 1:
            pass
        elif len(self.curPointsPlottedX) == 2:
            self.closeRect()
        else:
            print("Whoops, wrong number of rectangle points. This shouldn't have happened.")
            assert(False)

        self.plotOnCanvas()

    # def updateSpline(self):
    #     self.maskCoverImg.fill(0)
    #     if len(self.curPointsPlottedX) > 0:            
    #         if len(self.curPointsPlottedX) > 1:
    #             xSpline, ySpline = calculateSpline(self.curPointsPlottedX, self.curPointsPlottedY)
    #             spline = [(int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))]
    #             spline = np.array([*set(spline)])
    #             xSpline, ySpline = np.transpose(spline)
    #             xSpline = np.clip(xSpline, a_min=round(self.xBorderMin - 400)+1, a_max=720 + round(self.xBorderMax - 1121))
    #             ySpline = np.clip(ySpline, a_min=round(self.yBorderMin - 170)+1, a_max=500 + round(self.yBorderMax - 671))
    #             for i in range(len(xSpline)):
    #                 self.maskCoverImg[ySpline[i]-1:ySpline[i]+2, xSpline[i]-1:xSpline[i]+2] = [255, 255, 0, 255]

    #         for i in range(len(self.curPointsPlottedX)):
    #             self.maskCoverImg[self.curPointsPlottedY[i]-2:self.curPointsPlottedY[i]+3, \
    #                                 self.curPointsPlottedX[i]-2:self.curPointsPlottedX[i]+3] = [0,0,255, 255]

    def closeRect(self):
        if len(self.curPointsPlottedX) != 2:
            print("Whoops, wrong number of rectangle points. How did this happen?")
            assert(False)
        if len(self.curPointsPlottedX) != len(self.curPointsPlottedY):
            print("Mismatching rectangle coordinates. How did this happen?")
            assert(False)

        # draw rectangle
=======
    def acceptRect(self):
        if not len(self.curPointsPlottedX) == 2 and len(self.curPointsPlottedY) == 2:
            print("Can't accept because wrong number of points.")
            assert(False)
>>>>>>> 26f306db3fd746efd9f22f176306475dbce85142
        if self.curPointsPlottedX[0] == self.curPointsPlottedX[1]:
            self.curPointsPlottedX[1] += 1
        if self.curPointsPlottedY[0] == self.curPointsPlottedY[1]:
            self.curPointsPlottedY[1] += 1
<<<<<<< HEAD
        # Draw horizontal lines for the top and bottom edges
        top_left_x = min(self.curPointsPlottedX)
        top_left_y = min(self.curPointsPlottedY)
        bottom_right_x = max(self.curPointsPlottedX)
        bottom_right_y = max(self.curPointsPlottedY)
        border_color = [255, 255, 0, 255]

        for x in range(top_left_x, bottom_right_x + 1):
            self.maskCoverImg[top_left_y-2:top_left_y+3, x] = border_color
            self.maskCoverImg[bottom_right_y-2:bottom_right_y+3, x] = border_color

        # Draw vertical lines for the left and right edges
        for y in range(top_left_y, bottom_right_y + 1):
            self.maskCoverImg[y, top_left_x-2:top_left_x+3] = border_color
            self.maskCoverImg[y, bottom_right_x-2:bottom_right_x+3] = border_color

        # try:
        #     if self.imgInfoStruct.numSamplesDrOut == 1400:
        #         # Preset 1 boundaries for 20220831121844_IQ.bin
        #         self.ax.plot([148.76, 154.22], [0, 500], c="purple") # left boundary
        #         self.ax.plot([0, 716], [358.38, 386.78], c="purple") # bottom boundary
        #         self.ax.plot([572.47, 509.967], [0, 500], c="purple") # right boundary

        #     elif self.imgInfoStruct.numSamplesDrOut == 1496:
        #         # Preset 2 boundaries for 20220831121752_IQ.bin
        #         self.ax.plot([146.9, 120.79], [0, 500], c="purple") # left boundary
        #         self.ax.plot([0, 644.76], [462.41, 500], c="purple") # bottom boundary
        #         self.ax.plot([614.48, 595.84], [0, 500], c="purple") # right boundary

        #     else:
        #         print("No preset found!")
        # except:
            pass

        self.plotOnCanvas()
        self.ROIDrawn = True
        self.drawRoiButton.setChecked(False)
        self.drawRoiButton.setCheckable(False)
        self.closeRoiButton.setHidden(True)
        self.undoLastPtButton.clicked.disconnect()
        self.plotOnCanvas()

    def clearRect(self):
        self.curPointsPlottedX = []
        self.curPointsPlottedY = []
        self.scatteredPoints = []
        self.drawRectButton.setChecked(False)
        self.drawRectButton.setCheckable(True)
        self.undoLastPtButton.clicked.connect(self.undoLastPt)
        self.plotOnCanvas()

    def acceptRect(self):
        if not len(self.curPointsPlottedX) == 2 and len(self.curPointsPlottedY) == 2:
            print("Can't accept because wrong number of points.")
            assert(False)
        # if len(self.curPointsPlottedX) > 1 and self.curPointsPlottedX[-1] == self.curPointsPlottedX[0]:
        #     del self.analysisParamsGUI
=======
        
        del self.analysisParamsGUI
>>>>>>> 26f306db3fd746efd9f22f176306475dbce85142

        if self.multipleFrames:
            imData = np.array(self.imArray[self.frame]).reshape(self.arHeight, self.arWidth)
        else:
            imData = self.imArray
        imData = np.flipud(imData)
        imData = np.require(imData, np.uint8, 'C')
        bytesLine = imData.strides[0]
        arHeight = imData.shape[0]
        arWidth = imData.shape[1]
        savedIm = QImage(imData, arWidth, arHeight, bytesLine, QImage.Format_Grayscale8).scaled(self.widthScale, self.depthScale)

<<<<<<< HEAD
        if self.curPointsPlottedX[0] == self.curPointsPlottedX[1]:
            self.curPointsPlottedX[1] += 1
        if self.curPointsPlottedY[0] == self.curPointsPlottedY[1]:
            self.curPointsPlottedY[1] += 1

        savedIm.mirrored().save(os.path.join("Junk", "bModeImRaw.png"))
        savedIm.mirrored().save(os.path.join("Junk", "bModeIm.png"))
        self.analysisParamsGUI = AnalysisParamsGUI()
=======
        savedIm.mirrored().save(os.path.join("Junk", "bModeImRaw.png"))
        savedIm.mirrored().save(os.path.join("Junk", "bModeIm.png"))
        self.analysisParamsGUI = AnalysisParamsGUI()

>>>>>>> 26f306db3fd746efd9f22f176306475dbce85142
        self.analysisParamsGUI.oneWindow = [min(self.curPointsPlottedX), max(self.curPointsPlottedX), min(self.curPointsPlottedY), max(self.curPointsPlottedY)]        
        self.analysisParamsGUI.curPointsPlottedX = self.curPointsPlottedX[:-1]
        self.analysisParamsGUI.curPointsPlottedY = self.curPointsPlottedY[:-1]
        self.analysisParamsGUI.lastGui = self
        self.analysisParamsGUI.imArray = self.imData
        self.analysisParamsGUI.dataFrame = self.dataFrame
        self.analysisParamsGUI.setFilenameDisplays(self.imagePathInput.text().split('/')[-1], self.phantomPathInput.text().split('/')[-1])
        self.analysisParamsGUI.plotRoiPreview()
        self.analysisParamsGUI.show()
<<<<<<< HEAD
=======
        # self.editImageDisplayGUI.hide()
>>>>>>> 26f306db3fd746efd9f22f176306475dbce85142
        self.hide()

def calculateSpline(xpts, ypts): # 2D spline interpolation
    cv = []
    for i in range(len(xpts)):
        cv.append([xpts[i], ypts[i]])
    cv = np.array(cv)
    if len(xpts) == 2:
        tck, u_ = interpolate.splprep(cv.T, s=0.0, k=1)
    elif len(xpts) == 3:
        tck, u_ = interpolate.splprep(cv.T, s=0.0, k=2)
    else:
        tck, u_ = interpolate.splprep(cv.T, s=0.0, k=3)
    x,y = np.array(interpolate.splev(np.linspace(0, 1, 1000), tck))
    return x, y

def removeDuplicates(ar):
        # Credit: https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
        seen = set()
        seen_add = seen.add
        return [x for x in ar if not (tuple(x) in seen or seen_add(tuple(x)))]