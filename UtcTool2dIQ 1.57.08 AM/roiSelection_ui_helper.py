import Parsers.verasonicsMatParser as vera
import Parsers.canonBinParser as canon
from UtcTool2dIQ.roiSelection_ui import *
from UtcTool2dIQ.editImageDisplay_ui_helper import *
from UtcTool2dIQ.analysisParamsSelection_ui_helper import *
from UtcTool2dIQ.loadRoi_ui_helper import *

import pydicom
import os
import numpy as np
from PIL import Image, ImageEnhance
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib
import scipy.interpolate as interpolate

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QImage

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


        self.imagePathInput.setHidden(True)
        self.phantomPathInput.setHidden(True)
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
        self.pointsPlottedX = []
        self.pointsPlottedY = []

        # Prepare B-Mode display plot
        self.horizontalLayout = QHBoxLayout(self.imDisplayFrame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.horizontalLayout.addWidget(self.canvas)

        self.editImageDisplayGUI = EditImageDisplayGUI()
        self.editImageDisplayGUI.contrastVal.valueChanged.connect(self.changeContrast)
        self.editImageDisplayGUI.brightnessVal.valueChanged.connect(self.changeBrightness)    
        self.editImageDisplayGUI.sharpnessVal.valueChanged.connect(self.changeSharpness)

        self.analysisParamsGUI = AnalysisParamsGUI()

        self.scatteredPoints = []
        self.dataFrame = None
        self.lastGui = None

        self.redrawRoiButton.setHidden(True)
        
        self.editImageDisplayButton.clicked.connect(self.openImageEditor)
        self.drawRoiButton.clicked.connect(self.recordDrawROIClicked)
        self.undoLastPtButton.clicked.connect(self.undoLastPt)
        self.closeRoiButton.clicked.connect(self.closeInterpolation)
        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.acceptRoiButton.clicked.connect(self.acceptROI)
        self.backButton.clicked.connect(self.backToWelcomeScreen)
        self.newRoiButton.clicked.connect(self.drawNewRoi)
        self.loadRoiButton.clicked.connect(self.openLoadRoiWindow)

        self.rectRoiButton.clicked.connect(self.drawRectRoi)
        self.drawRectButton.clicked.connect(self.recordDrawRectClicked)
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

    def backToWelcomeScreen(self):
        self.lastGui.dataFrame = self.dataFrame
        self.lastGui.show()
        self.hide()

    def changeContrast(self):
        self.editImageDisplayGUI.contrastValDisplay.setValue(int(self.editImageDisplayGUI.contrastVal.value()*10))
        self.updateBModeSettings()

    def changeBrightness(self):
        self.editImageDisplayGUI.brightnessValDisplay.setValue(int(self.editImageDisplayGUI.brightnessVal.value()*10))
        self.updateBModeSettings()

    def changeSharpness(self):
        self.editImageDisplayGUI.sharpnessValDisplay.setValue(int(self.editImageDisplayGUI.sharpnessVal.value()*10))
        self.updateBModeSettings()

    def openImageEditor(self):
        if self.editImageDisplayGUI.isVisible():
            self.editImageDisplayGUI.hide()
        else:
            self.editImageDisplayGUI.show()

    def setFilenameDisplays(self, imageName, phantomName):
        self.imagePathInput.setHidden(False)
        self.phantomPathInput.setHidden(False)
        self.imagePathInput.setText(imageName)
        self.phantomPathInput.setText(phantomName)
    
    def plotOnCanvas(self): # Plot current image on GUI
        self.ax.clear()
        im = plt.imread(os.path.join("Junk", "bModeIm.png"))
        self.ax.imshow(im, cmap='Greys_r')

        if len(self.pointsPlottedX) > 0:
            self.scatteredPoints.append(self.ax.scatter(self.pointsPlottedX[-1], self.pointsPlottedY[-1], marker="o", s=0.5, c="red", zorder=500))
            if len(self.pointsPlottedX) > 1:
                xSpline, ySpline = calculateSpline(self.pointsPlottedX, self.pointsPlottedY)
                self.spline = self.ax.plot(xSpline, ySpline, color = "cyan", zorder=1, linewidth=0.75)
        
        try:
            if self.imgInfoStruct.numSamplesDrOut == 1400:
                # Preset 1 boundaries for 20220831121844_IQ.bin
                self.ax.plot([148.76, 154.22], [0, 500], c="purple") # left boundary
                self.ax.plot([0, 716], [358.38, 386.78], c="purple") # bottom boundary
                self.ax.plot([572.47, 509.967], [0, 500], c="purple") # right boundary

            elif self.imgInfoStruct.numSamplesDrOut == 1496:
                # Preset 2 boundaries for 20220831121752_IQ.bin
                self.ax.plot([146.9, 120.79], [0, 500], c="purple") # left boundary
                self.ax.plot([0, 644.76], [462.41, 500], c="purple") # bottom boundary
                self.ax.plot([614.48, 595.84], [0, 500], c="purple") # right boundary
            
            else:
                print("No preset found!")
        except:
            pass

        self.figure.subplots_adjust(left=0,right=1, bottom=0,top=1, hspace=0.2,wspace=0.2)
        self.cursor = matplotlib.widgets.Cursor(self.ax, color="gold", linewidth=0.4, useblit=True)
        self.cursor.set_active(False)
        plt.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
        self.canvas.draw() # Refresh canvas


    def openImageVerasonics(self, imageFilePath, phantomFilePath): # Open initial image given data and phantom files previously inputted
        tmpLocation = imageFilePath.split("/")
        dataFileName = tmpLocation[-1]
        dataFileLocation = imageFilePath[:len(imageFilePath)-len(dataFileName)]
        tmpPhantLocation = phantomFilePath.split("/")
        phantFileName = tmpPhantLocation[-1]
        phantFileLocation = phantomFilePath[:len(phantomFilePath)-len(phantFileName)]

        imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = vera.getImage(dataFileName, dataFileLocation, phantFileName, phantFileLocation)
        self.arHeight = imArray.shape[0]
        self.arWidth = imArray.shape[1]
        self.imData = np.array(imArray).reshape(self.arHeight, self.arWidth)
        self.imData = np.flipud(self.imData) #flipud
        self.imData = np.require(self.imData,np.uint8,'C')
        self.bytesLine = self.imData.strides[0]
        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8).scaled(721, 501)

        self.qIm.mirrored().save(os.path.join("Junk", "bModeImRaw.png")) # Save as .png file

        self.editImageDisplayGUI.contrastVal.setValue(1)
        self.editImageDisplayGUI.brightnessVal.setValue(1)
        self.editImageDisplayGUI.sharpnessVal.setValue(1)

        self.analysisParamsGUI.axWinSizeVal.setValue(10)
        self.analysisParamsGUI.latWinSizeVal.setValue(10)
        self.analysisParamsGUI.axOverlapVal.setValue(50)
        self.analysisParamsGUI.latOverlapVal.setValue(50)
        # self.analysisParamsGUI.minFreqVal.setValue(3)
        # self.analysisParamsGUI.maxFreqVal.setValue(4.5)
        # self.analysisParamsGUI.clipFactorVal.setValue(95)
        # self.analysisParamsGUI.samplingFreqVal.setValue(20)

        # Implement correct previously assigned image display settings

        self.cvIm = Image.open(os.path.join("Junk", "bModeImRaw.png"))
        enhancer = ImageEnhance.Contrast(self.cvIm)

        imOutput = enhancer.enhance(self.editImageDisplayGUI.contrastVal.value())
        bright = ImageEnhance.Brightness(imOutput)
        imOutput = bright.enhance(self.editImageDisplayGUI.brightnessVal.value())
        sharp = ImageEnhance.Sharpness(imOutput)
        imOutput = sharp.enhance(self.editImageDisplayGUI.sharpnessVal.value())
        imOutput.save(os.path.join("Junk", "bModeIm.png"))

        self.plotOnCanvas()

    def openImageCanon(self, imageFilePath, phantomFilePath): # Open initial image given data and phantom files previously inputted
        tmpLocation = imageFilePath.split("/")
        dataFileName = tmpLocation[-1]
        dataFileLocation = imageFilePath[:len(imageFilePath)-len(dataFileName)]
        tmpPhantLocation = phantomFilePath.split("/")
        phantFileName = tmpPhantLocation[-1]
        phantFileLocation = phantomFilePath[:len(phantomFilePath)-len(phantFileName)]

        imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = canon.getImage(dataFileName, dataFileLocation, phantFileName, phantFileLocation)
        if self.imgInfoStruct.depth != self.refInfoStruct.depth:
            print("Presets don't match! Analysis not possible")
            exit()
        self.arHeight = imArray.shape[0]
        self.arWidth = imArray.shape[1]
        self.imData = np.array(imArray).reshape(self.arHeight, self.arWidth)
        self.imData = np.flipud(self.imData) #flipud
        self.imData = np.require(self.imData,np.uint8,'C')
        refData = np.array(self.refDataStruct.scBmode)
        refData = np.flipud(refData)
        refData = np.require(refData, np.uint8, 'C')
        self.bytesLine = self.imData.strides[0]
        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8).scaled(721, 501)
        self.qImPhant = QImage(refData, refData.shape[1], refData.shape[0], refData.strides[0], QImage.Format_Grayscale8).scaled(721, 501)

        self.qIm.mirrored().save(os.path.join("Junk", "bModeImRaw.png")) # Save as .png file
        self.qImPhant.mirrored().save(os.path.join("Junk", "phantImRaw.png"))

        self.editImageDisplayGUI.contrastVal.setValue(1)
        self.editImageDisplayGUI.brightnessVal.setValue(0.75)
        self.editImageDisplayGUI.sharpnessVal.setValue(3)

        self.analysisParamsGUI.axWinSizeVal.setValue(self.imgInfoStruct.depth/100)#7#1#1480/20000000*10000 # must be at least 10 times wavelength
        self.analysisParamsGUI.latWinSizeVal.setValue(self.imgInfoStruct.width/100)#7#1#1480/20000000*10000 # must be at least 10 times wavelength

        speedOfSoundInTissue = 1540 #m/s
        waveLength = (speedOfSoundInTissue/self.imgInfoStruct.centerFrequency)*1000 #mm
        self.analysisParamsGUI.axWinSizeVal.setMinimum(10*waveLength) # must be at least 10 times wavelength
        self.analysisParamsGUI.latWinSizeVal.setMinimum(10*waveLength) # must be at least 10 times wavelength

        self.analysisParamsGUI.axOverlapVal.setValue(50)
        self.analysisParamsGUI.latOverlapVal.setValue(50)
        self.analysisParamsGUI.windowThresholdVal.setValue(95)
        self.analysisParamsGUI.minFreqVal.setValue(np.round(self.imgInfoStruct.minFrequency/1000000, decimals=2))
        self.analysisParamsGUI.maxFreqVal.setValue(np.round(self.imgInfoStruct.maxFrequency/1000000, decimals=2))
        self.analysisParamsGUI.lowBandFreqVal.setValue(np.round(self.imgInfoStruct.lowBandFreq/1000000, decimals=2))
        self.analysisParamsGUI.upBandFreqVal.setValue(np.round(self.imgInfoStruct.upBandFreq/1000000, decimals=2))
        self.analysisParamsGUI.samplingFreqVal.setValue(np.round(self.imgInfoStruct.samplingFrequency/1000000, decimals=2))
        self.analysisParamsGUI.imageDepthVal.setText(str(np.round(self.imgInfoStruct.depth, decimals=1)))
        self.analysisParamsGUI.imageWidthVal.setText(str(np.round(self.imgInfoStruct.width, decimals=1)))
        self.physicalDepthVal.setText(str(np.round(self.imgInfoStruct.depth, decimals=2)))
        self.physicalWidthVal.setText(str(np.round(self.imgInfoStruct.width, decimals=2)))
        self.pixelWidthVal.setText(str(self.arWidth))
        self.pixelDepthVal.setText(str(self.arHeight))

        # Hough transform
        # import cv2
        # image = Image.open(os.path.join("Junk", "phantIm.png"))
        # filtered = cv2.blur(image, (7,7))
        # filtered = cv2.filter2D(src=gray_arr, ddepth=-1, kernel=filter)
        # thresh1 = 35
        # thresh2 = 60
        # cv2.Canny(filtered, thresh1, thresh2)
        # cv2.HoughLines(edges, 1, np.pi/180, threshold, min_theta=angle1, max_theta=angle2)

        # Implement correct previously assigned image display settings

        self.cvIm = Image.open(os.path.join("Junk", "bModeImRaw.png"))
        enhancer = ImageEnhance.Contrast(self.cvIm)

        imOutput = enhancer.enhance(self.editImageDisplayGUI.contrastVal.value())
        bright = ImageEnhance.Brightness(imOutput)
        imOutput = bright.enhance(self.editImageDisplayGUI.brightnessVal.value())
        sharp = ImageEnhance.Sharpness(imOutput)
        imOutput = sharp.enhance(self.editImageDisplayGUI.sharpnessVal.value())
        imOutput.save(os.path.join("Junk", "bModeIm.png"))

        self.plotOnCanvas()

    def recordDrawROIClicked(self):
        if self.drawRoiButton.isChecked(): # Set up b-mode to be drawn on
            # image, =self.ax.plot([], [], marker="o",markersize=3, markerfacecolor="red")
            # self.cid = image.figure.canvas.mpl_connect('button_press_event', self.interpolatePoints)
            self.cid = self.figure.canvas.mpl_connect('button_press_event', self.interpolatePoints)
            self.cursor.set_active(True)
        else: # No longer let b-mode be drawn on
            self.cid = self.figure.canvas.mpl_disconnect(self.cid)
            self.cursor.set_active(False)
        self.canvas.draw()

    def undoLastPt(self): # When drawing ROI, undo last point plotted
        if len(self.pointsPlottedX) > 0:
            self.scatteredPoints[-1].remove()
            self.scatteredPoints.pop()
            self.pointsPlottedX.pop()
            self.pointsPlottedY.pop()
            if len(self.pointsPlottedX) > 0:
                oldSpline = self.spline.pop(0)
                oldSpline.remove()
                if len(self.pointsPlottedX) > 1:
                    self.finalSplineX, self.finalSplineY = calculateSpline(self.pointsPlottedX, self.pointsPlottedY)
                    self.spline = self.ax.plot(self.finalSplineX, self.finalSplineY, color = "cyan", linewidth=0.75)
            self.canvas.draw()
            self.drawRoiButton.setChecked(True)
            self.recordDrawROIClicked()

    def closeInterpolation(self): # Finish drawing ROI
        if len(self.pointsPlottedX) > 2:
            self.ax.clear()
            im = plt.imread(os.path.join("Junk", "bModeIm.png"))
            plt.imshow(im, cmap='Greys_r')
            self.pointsPlottedX.append(self.pointsPlottedX[0])
            self.pointsPlottedY.append(self.pointsPlottedY[0])
            self.finalSplineX, self.finalSplineY = calculateSpline(self.pointsPlottedX, self.pointsPlottedY)

            try:
                if self.imgInfoStruct.numSamplesDrOut == 1400:
                    self.finalSplineX = np.clip(self.finalSplineX, a_min=148, a_max=573)
                    self.finalSplineY = np.clip(self.finalSplineY, a_min=0.5, a_max=387)
                elif self.imgInfoStruct.numSamplesDrOut == 1496:
                    self.finalSplineX = np.clip(self.finalSplineX, a_min=120, a_max=615)
                    self.finalSplineY = np.clip(self.finalSplineY, a_min=0.5, a_max=645)
                else:
                    print("Preset not found!")
                    return
            except:
                pass
            
            self.ax.plot(self.finalSplineX, self.finalSplineY, color = "cyan", linewidth=0.75)
            try:
                image, =self.ax.plot([], [], marker="o",markersize=3, markerfacecolor="red")
                image.figure.canvas.mpl_disconnect(self.cid)
            except:
                image = 0 # do nothing. Means we're loading ROI

            
            try:
                if self.imgInfoStruct.numSamplesDrOut == 1400:
                    # Preset 1 boundaries for 20220831121844_IQ.bin
                    self.ax.plot([148.76, 154.22], [0, 500], c="purple") # left boundary
                    self.ax.plot([0, 716], [358.38, 386.78], c="purple") # bottom boundary
                    self.ax.plot([572.47, 509.967], [0, 500], c="purple") # right boundary

                elif self.imgInfoStruct.numSamplesDrOut == 1496:
                    # Preset 2 boundaries for 20220831121752_IQ.bin
                    self.ax.plot([146.9, 120.79], [0, 500], c="purple") # left boundary
                    self.ax.plot([0, 644.76], [462.41, 500], c="purple") # bottom boundary
                    self.ax.plot([614.48, 595.84], [0, 500], c="purple") # right boundary
                
                else:
                    print("No preset found!")
            except:
                pass

            self.figure.subplots_adjust(left=0,right=1, bottom=0,top=1, hspace=0.2,wspace=0.2)
            plt.tick_params(bottom=False, left=False)
            self.canvas.draw()
            self.ROIDrawn = True
            self.drawRoiButton.setChecked(False)
            self.drawRoiButton.setCheckable(False)
            self.redrawRoiButton.setHidden(False)
            self.closeRoiButton.setHidden(True)
            self.cursor.set_active(False)
            self.undoLastPtButton.clicked.disconnect()
            self.canvas.draw()

    def undoLastRoi(self): # Remove previously drawn roi and prepare user to draw a new one
        self.finalSplineX = []
        self.finalSplineY = []
        self.pointsPlottedX = []
        self.pointsPlottedY = []
        self.drawRoiButton.setChecked(False)
        self.drawRoiButton.setCheckable(True)
        self.closeRoiButton.setHidden(False)
        self.redrawRoiButton.setHidden(True)
        self.undoLastPtButton.clicked.connect(self.undoLastPt)
        self.plotOnCanvas()
    
    def recordDrawRectClicked(self):
        if self.drawRectButton.isChecked(): # Set up b-mode to be drawn on
            # image, =self.ax.plot([], [], marker="o",markersize=3, markerfacecolor="red")
            # self.cid = image.figure.canvas.mpl_connect('button_press_event', self.interpolatePoints)
            self.cid = self.figure.canvas.mpl_connect('button_press_event', self.addRectPoint)
            self.cursor.set_active(True)
        else: # No longer let b-mode be drawn on
            self.cid = self.figure.canvas.mpl_disconnect(self.cid)
            self.cursor.set_active(False)
        self.canvas.draw()
    
    def addRectPoint(self, event):
        try:
            if self.imgInfoStruct.numSamplesDrOut == 1400:
                # Preset 1 boundaries for 20220831121844_IQ.bin
                leftSlope = (500 - 0)/(154.22 - 148.76)
                pointSlopeLeft = (event.ydata - 0) / (event.xdata - 148.76)
                if pointSlopeLeft <= 0 or leftSlope < pointSlopeLeft:
                    return
                
                bottomSlope = (386.78 - 358.38) / (716 - 0)
                pointSlopeBottom = (event.ydata - 358.38) / (event.xdata - 0)
                rightSlope = (500 - 0) / (509.967 - 572.47)
                pointSlopeRight = (event.ydata - 0) / (event.xdata - 572.47)

            elif self.imgInfoStruct.numSamplesDrOut == 1496:
                # Preset 2 boundaries for 20220831121752_IQ.bin
                leftSlope = (500 - 0) / (120.79 - 146.9)
                pointSlopeLeft = (event.ydata - 0) / (event.xdata - 146.9)
                if pointSlopeLeft > leftSlope and pointSlopeLeft <= 0:
                    return
                
                bottomSlope = (500 - 462.41) / (644.76 - 0)
                pointSlopeBottom = (event.ydata - 462.41) / (event.xdata - 0)
                rightSlope = (500 - 0) / (595.84 - 614.48)
                pointSlopeRight = (event.ydata - 0) / (event.xdata - 614.48)
            
            else:
                print("Preset not found!")
                return

            if pointSlopeBottom > bottomSlope:
                    return
            if pointSlopeRight >= 0 or pointSlopeRight < rightSlope:
                return
        except:
            pass

        self.pointsPlottedX.append(int(event.xdata))
        self.pointsPlottedY.append(int(event.ydata))
        self.scatteredPoints.append(self.ax.scatter(self.pointsPlottedX[-1], self.pointsPlottedY[-1], marker="o", s=0.5, c="red", zorder=500))

        assert(len(self.pointsPlottedX) == len(self.pointsPlottedY))

        if len(self.pointsPlottedX) == 1:
            pass
        elif len(self.pointsPlottedX) == 2:
            self.closeRect()
        else:
            print("Whoops, wrong number of rectangle points. This shouldn't have happened.")
            assert(False)

        self.canvas.draw()
    
    def closeRect(self):
        if len(self.pointsPlottedX) != 2:
            print("Whoops, wrong number of rectangle points. How did this happen?")
            assert(False)
        if len(self.pointsPlottedX) != len(self.pointsPlottedY):
            print("Mismatching rectangle coordinates. How did this happen?")
            assert(False)
        
        self.ax.clear()
        im = plt.imread(os.path.join("Junk", "bModeIm.png"))
        plt.imshow(im, cmap='Greys_r')
        self.pointsPlottedX.append(self.pointsPlottedX[0])
        self.pointsPlottedY.append(self.pointsPlottedY[0])

        # draw rectangle
        if self.pointsPlottedX[0] == self.pointsPlottedX[1]:
            self.pointsPlottedX[1] += 1
        if self.pointsPlottedY[0] == self.pointsPlottedY[1]:
            self.pointsPlottedY[1] += 1
        rectXs = [min(self.pointsPlottedX), max(self.pointsPlottedX), max(self.pointsPlottedX), min(self.pointsPlottedX), min(self.pointsPlottedX)]
        rectYs = [min(self.pointsPlottedY), min(self.pointsPlottedY), max(self.pointsPlottedY), max(self.pointsPlottedY), min(self.pointsPlottedY)]
        self.ax.plot(rectXs, rectYs, color = "cyan", linewidth=0.75)
        
        try:
            image, =self.ax.plot([], [], marker="o",markersize=3, markerfacecolor="red")
            image.figure.canvas.mpl_disconnect(self.cid)
        except:
            image = 0 # do nothing. Means we're loading ROI

        
        try:
            if self.imgInfoStruct.numSamplesDrOut == 1400:
                # Preset 1 boundaries for 20220831121844_IQ.bin
                self.ax.plot([148.76, 154.22], [0, 500], c="purple") # left boundary
                self.ax.plot([0, 716], [358.38, 386.78], c="purple") # bottom boundary
                self.ax.plot([572.47, 509.967], [0, 500], c="purple") # right boundary

            elif self.imgInfoStruct.numSamplesDrOut == 1496:
                # Preset 2 boundaries for 20220831121752_IQ.bin
                self.ax.plot([146.9, 120.79], [0, 500], c="purple") # left boundary
                self.ax.plot([0, 644.76], [462.41, 500], c="purple") # bottom boundary
                self.ax.plot([614.48, 595.84], [0, 500], c="purple") # right boundary
            
            else:
                print("No preset found!")
        except:
            pass

        self.figure.subplots_adjust(left=0,right=1, bottom=0,top=1, hspace=0.2,wspace=0.2)
        plt.tick_params(bottom=False, left=False)
        self.canvas.draw()
        self.ROIDrawn = True
        self.drawRoiButton.setChecked(False)
        self.drawRoiButton.setCheckable(False)
        self.closeRoiButton.setHidden(True)
        self.cursor.set_active(False)
        self.undoLastPtButton.clicked.disconnect()
        self.canvas.draw()
    
    def clearRect(self):
        self.pointsPlottedX = []
        self.pointsPlottedY = []
        self.scatteredPoints = []
        self.drawRectButton.setChecked(False)
        self.drawRectButton.setCheckable(True)
        self.undoLastPtButton.clicked.connect(self.undoLastPt)
        self.plotOnCanvas()
    
    def acceptRect(self):
        if not len(self.pointsPlottedX) == 2 and len(self.pointsPlottedY) == 2:
            print("Can't accept because wrong number of points.")
            assert(False)
        if self.pointsPlottedX[0] == self.pointsPlottedX[1]:
            self.pointsPlottedX[1] += 1
        if self.pointsPlottedY[0] == self.pointsPlottedY[1]:
            self.pointsPlottedY[1] += 1
        
        self.analysisParamsGUI.oneWindow = [min(self.pointsPlottedX), max(self.pointsPlottedX), min(self.pointsPlottedY), max(self.pointsPlottedY)]        
        self.analysisParamsGUI.curPointsPlottedX = self.pointsPlottedX[:-1]
        self.analysisParamsGUI.curPointsPlottedY = self.pointsPlottedY[:-1]
        self.analysisParamsGUI.lastGui = self
        self.analysisParamsGUI.imArray = self.imData
        self.analysisParamsGUI.dataFrame = self.dataFrame
        self.analysisParamsGUI.setFilenameDisplays(self.imagePathInput.text().split('/')[-1], self.phantomPathInput.text().split('/')[-1])
        self.analysisParamsGUI.plotRoiPreview()
        self.analysisParamsGUI.show()
        self.editImageDisplayGUI.hide()
        self.hide()

    def updateBModeSettings(self): # Updates background photo when image settings are modified
        self.cvIm = Image.open(os.path.join("Junk", "bModeImRaw.png"))
        contrast = ImageEnhance.Contrast(self.cvIm)
        imOutput = contrast.enhance(self.editImageDisplayGUI.contrastVal.value())
        brightness = ImageEnhance.Brightness(imOutput)
        imOutput = brightness.enhance(self.editImageDisplayGUI.brightnessVal.value())
        sharpness = ImageEnhance.Sharpness(imOutput)
        imOutput = sharpness.enhance(self.editImageDisplayGUI.sharpnessVal.value())
        imOutput.save(os.path.join("Junk", "bModeIm.png"))
        self.plotOnCanvas()
    
    def interpolatePoints(self, event): # Update ROI being drawn using spline using 2D interpolation
        try:
            if self.imgInfoStruct.numSamplesDrOut == 1400:
                # Preset 1 boundaries for 20220831121844_IQ.bin
                leftSlope = (500 - 0)/(154.22 - 148.76)
                pointSlopeLeft = (event.ydata - 0) / (event.xdata - 148.76)
                if pointSlopeLeft <= 0 or leftSlope < pointSlopeLeft:
                    return
                
                bottomSlope = (386.78 - 358.38) / (716 - 0)
                pointSlopeBottom = (event.ydata - 358.38) / (event.xdata - 0)
                rightSlope = (500 - 0) / (509.967 - 572.47)
                pointSlopeRight = (event.ydata - 0) / (event.xdata - 572.47)

            elif self.imgInfoStruct.numSamplesDrOut == 1496:
                # Preset 2 boundaries for 20220831121752_IQ.bin
                leftSlope = (500 - 0) / (120.79 - 146.9)
                pointSlopeLeft = (event.ydata - 0) / (event.xdata - 146.9)
                if pointSlopeLeft > leftSlope and pointSlopeLeft <= 0:
                    return
                
                bottomSlope = (500 - 462.41) / (644.76 - 0)
                pointSlopeBottom = (event.ydata - 462.41) / (event.xdata - 0)
                rightSlope = (500 - 0) / (595.84 - 614.48)
                pointSlopeRight = (event.ydata - 0) / (event.xdata - 614.48)
            
            else:
                print("Preset not found!")
                return

            if pointSlopeBottom > bottomSlope:
                    return
            if pointSlopeRight >= 0 or pointSlopeRight < rightSlope:
                return
        except:
            pass

        self.pointsPlottedX.append(int(event.xdata))
        self.pointsPlottedY.append(int(event.ydata))
        plottedPoints = len(self.pointsPlottedX)

        if plottedPoints > 1:
            if plottedPoints > 2:
                oldSpline = self.spline.pop(0)
                oldSpline.remove()

            xSpline, ySpline = calculateSpline(self.pointsPlottedX, self.pointsPlottedY)
            self.spline = self.ax.plot(xSpline, ySpline, color = "cyan", zorder=1, linewidth=0.75)
            plt.subplots_adjust(left=0,right=1, bottom=0,top=1, hspace=0.2,wspace=0.2)
            plt.tick_params(bottom=False, left=False)
        self.scatteredPoints.append(self.ax.scatter(self.pointsPlottedX[-1], self.pointsPlottedY[-1], marker="o", s=0.5, c="red", zorder=500))
        self.canvas.draw()

    def acceptROI(self):
        if len(self.pointsPlottedX) > 1 and self.pointsPlottedX[0] == self.pointsPlottedX[-1]:
            self.analysisParamsGUI.finalSplineX = self.finalSplineX
            self.analysisParamsGUI.finalSplineY = self.finalSplineY
            self.analysisParamsGUI.curPointsPlottedX = self.pointsPlottedX[:-1]
            self.analysisParamsGUI.curPointsPlottedY = self.pointsPlottedY[:-1]
            self.analysisParamsGUI.lastGui = self
            self.analysisParamsGUI.imArray = self.imData
            self.analysisParamsGUI.dataFrame = self.dataFrame
            self.analysisParamsGUI.setFilenameDisplays(self.imagePathInput.text().split('/')[-1], self.phantomPathInput.text().split('/')[-1])
            self.analysisParamsGUI.plotRoiPreview()
            self.analysisParamsGUI.show()
            self.editImageDisplayGUI.hide()
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