from UtcTool2d.roiSelection_ui import *
from UtcTool2d.editImageDisplay_ui_helper import *
from UtcTool2d.rfAnalysis_ui import *
from Utils.roiFuncs import *
from UtcTool2d.exportData_ui_helper import *
from UtcTool2d.saveRoi_ui_helper import *
from UtcTool2d.psGraphDisplay_ui_helper import *

import os
import numpy as np
from PIL import Image, ImageEnhance
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib
import scipy.interpolate as interpolate
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout

import platform
system = platform.system()


class RfAnalysisGUI(QWidget, Ui_rfAnalysis):
    def __init__(self, splineX, splineY, ow = None): #ow = oneWindow
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
            self.avMbfLabel.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.avSsLabel.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.avSiLabel.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.avMbfVal.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.avSsVal.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.avSiVal.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.indMbfLabel.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.indMbfVal.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.indSsLabel.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.indSsVal.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.indSiVal.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")
            self.indSiLabel.setStyleSheet("""QLabel {
                font-size: 14px;
                color: white;
	            background-color: rgba(0,0,0,0);
            }""")

            
        global roisLeft, roisRight, roisTop, roisBottom, mbf, ss, si, minMBF, minSS, minSI, windowNPSs, windowFreqs, mbfPoint, \
        maxMBF, maxSS, maxSI, curDisp, cmap, tempROISelected, selectedROI, indMBF, indSI, indSS, scanConverted, PsGraphDisplayGUI
        roisLeft = []
        roisRight = []
        roisTop = []
        roisBottom = []
        mbf = []
        ss = []
        si = []
        minMBF = 0
        minSS = 0
        minSI = 0
        maxMBF = 0
        maxSS = 0
        maxSI = 0
        curDisp = ""
        cmap = []
        tempROISelected = False
        selectedROI = -1
        indMBF = None
        indSI = None
        indSS = None
        scanConverted = False
        PsGraphDisplayGUI = PsGraphDisplay()
        mbfPoint = None

        self.splineX = splineX
        self.splineY = splineY
        self.imgDataStruct = None
        self.imgInfoStruct = None
        self.refDataStruct = None
        self.refInfoStruct = None
        self.frame = None
        self.dataFrame = None
        self.exportDataGUI = None
        self.newData = None
        self.curPointsPlottedX = None
        self.curPointsPlottedY = None
        self.widthScale = None
        self.depthScale = None

        self.axialWinSize = None
        self.lateralWinSize = None
        self.axialOverlap = None
        self.lateralOverlap = None
        self.windowThreshold = None
        self.minFrequency = None
        self.maxFrequency = None
        self.samplingFreq = None
        self.lowBandFreq = None
        self.upBandFreq = None
        self.lastGui = None
        self.saveRoiGUI = SaveRoiGUI()

        self.indMbfVal.setText("")
        self.indSiVal.setText("")
        self.indSsVal.setText("")

        indMBF = self.indMbfVal
        indSS = self.indSsVal
        indSI = self.indSiVal

        # Display B-Mode
        self.horizontalLayout = QHBoxLayout(self.imDisplayFrame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.figure = plt.figure()
        self.figure.patch.set_alpha(0)
        self.canvas = FigureCanvas(self.figure)
        self.horizontalLayout.addWidget(self.canvas)

        self.editImageDisplayGUI = EditImageDisplayGUI()
        self.editImageDisplayButton.clicked.connect(self.openImageEditor)

        self.oneWindow = ow

        self.chooseWindowButton.setCheckable(True)
        self.displayMbfButton.setCheckable(True)
        self.displaySiButton.setCheckable(True)
        self.displaySsButton.setCheckable(True)

        self.displayMbfButton.clicked.connect(self.mbfChecked)
        self.displaySsButton.clicked.connect(self.ssChecked)
        self.displaySiButton.clicked.connect(self.siChecked)
        self.chooseWindowButton.clicked.connect(self.chooseWindow)
        # self.editImageDisplayGUI.contrastVal.valueChanged.connect(self.changeContrast)
        # self.editImageDisplayGUI.brightnessVal.valueChanged.connect(self.changeBrightness)
        # self.editImageDisplayGUI.sharpnessVal.valueChanged.connect(self.changeSharpness)
        self.editImageDisplayGUI.contrastVal.setValue(1)
        self.editImageDisplayGUI.brightnessVal.setValue(1)
        self.editImageDisplayGUI.sharpnessVal.setValue(1)
        
        # Prepare heatmap legend plot
        self.horizLayoutLeg = QHBoxLayout(self.legend)
        self.horizLayoutLeg.setObjectName("horizLayoutLeg")
        self.figLeg = plt.figure()
        self.canvasLeg = FigureCanvas(self.figLeg)
        self.horizLayoutLeg.addWidget(self.canvasLeg)
        self.canvasLeg.draw()
        self.backButton.clicked.connect(self.backToLastScreen)
        self.exportDataButton.clicked.connect(self.moveToExport)
        self.saveDataButton.clicked.connect(self.saveData)
        self.saveRoiButton.clicked.connect(self.saveRoi)
        self.displayNpsButton.clicked.connect(self.displayNps)
        self.displayNpsButton.setCheckable(True)

    def displayNps(self):
        global PsGraphDisplayGUI
        if self.displayNpsButton.isChecked():
            PsGraphDisplayGUI.show()
        else:
            PsGraphDisplayGUI.hide()

    def saveRoi(self):
        self.saveRoiGUI.rfAnalysisGUI = self
        self.saveRoiGUI.show()

    def moveToExport(self):
        if len(self.dataFrame):
            del self.exportDataGUI
            self.exportDataGUI = ExportDataGUI()
            self.exportDataGUI.dataFrame = self.dataFrame
            self.exportDataGUI.lastGui = self
            self.exportDataGUI.setFilenameDisplays(self.imagePathInput.text(), self.phantomPathInput.text())
            self.exportDataGUI.show()
            self.hide()

    def saveData(self):
        if self.newData is None:
            self.newData = {"Patient": self.imagePathInput.text(), "Phantom": self.phantomPathInput.text(), \
                    "Midband Fit (MBF)": np.average(mbf), "Spectral Slope (SS)": np.average(ss), "Spectral Intercept (SI)": np.average(si)}
            self.dataFrame = self.dataFrame.append(self.newData, ignore_index=True)

    def backToLastScreen(self):
        global PsGraphDisplayGUI
        self.lastGui.dataFrame = self.dataFrame
        PsGraphDisplayGUI.hide()
        del PsGraphDisplayGUI
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

    def cleanStructs(self): # Discard windows outside of scan-converted ultrasound image
        splineList = [self.roiWindowSplinesStruct.top, self.roiWindowSplinesStruct.bottom, self.roiWindowSplinesStruct.left, self.roiWindowSplinesStruct.right]
        if not scanConverted:
            splineListPreSC = [self.roiWindowSplinesStructPreSC.top, self.roiWindowSplinesStructPreSC.bottom, self.roiWindowSplinesStructPreSC.left, self.roiWindowSplinesStructPreSC.right]
        else: 
            splineListPreSC = splineList
        numWindows = len(splineList[0])
        bottom = None
        left = None
        right = None
        for i in range(numWindows - 1, -1, -1):
            axes = [0, 0, 1, 1]
            vals1 = [splineList[0][i], splineList[1][i], splineList[2][i], splineList[3][i]]
            vals2 = [splineListPreSC[0][i], splineListPreSC[1][i], splineListPreSC[2][i], splineListPreSC[3][i]]
            if not (self.inBounds(vals1, vals2, axes, bottom, left, right)):
                for j in range(4):
                    splineList[j].pop(i)
                    splineListPreSC[j].pop(i)
        self.roiWindowSplinesStruct.top = splineList[0]
        self.roiWindowSplinesStruct.bottom = splineList[1]
        self.roiWindowSplinesStruct.left = splineList[2]
        self.roiWindowSplinesStruct.right = splineList[3]
        
        if not scanConverted:
            self.roiWindowSplinesStructPreSC.top = splineListPreSC[0]
            self.roiWindowSplinesStructPreSC.bottom = splineListPreSC[1]
            self.roiWindowSplinesStructPreSC.left = splineListPreSC[2]
            self.roiWindowSplinesStructPreSC.right = splineListPreSC[3]
        else:
            self.roiWindowSplinesStructPreSC = self.roiWindowSplinesStruct


    def inBounds(self, vals1, vals2, axes, bottom, left, right):
        if (len(vals2) != len(axes)):
            return False
        for i in range(len(vals2)):
            if not (vals2[i] > 0 and vals2[i] < self.imgDataStruct.rf.shape[axes[i]]):
                return False
        return True
    
    def plotOnCanvas(self): # Plot current image on GUI
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        im = plt.imread(os.path.join("Junk", "bModeIm.png"))
        self.ax.imshow(im, cmap='Greys_r')
        self.ax.axis('off')

        if self.oneWindow == None:
            self.ax.plot(self.splineX, self.splineY, color = "cyan", zorder=1, linewidth=0.75)
        self.figure.subplots_adjust(left=0,right=1, bottom=0,top=1, hspace=0.2,wspace=0.2)
        self.cursor = matplotlib.widgets.Cursor(self.ax, color="gold", linewidth=0.4, useblit=True)
        self.cursor.set_active(False)
        plt.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
        self.canvas.draw() # Refresh canvas

    def updateBModeSettings(self): # Updates background photo when image settings are modified
        self.cvIm = Image.open(os.path.join("Junk", "bModeImRaw.png"))
        contrast = ImageEnhance.Contrast(self.cvIm)
        hi = self.editImageDisplayGUI.contrastVal.value()
        imOutput = contrast.enhance(self.editImageDisplayGUI.contrastVal.value())
        brightness = ImageEnhance.Brightness(imOutput)
        hi = self.editImageDisplayGUI.brightnessVal.value()
        imOutput = brightness.enhance(self.editImageDisplayGUI.brightnessVal.value())
        sharpness = ImageEnhance.Sharpness(imOutput)
        hi = self.editImageDisplayGUI.sharpnessVal.value()
        imOutput = sharpness.enhance(self.editImageDisplayGUI.sharpnessVal.value())
        imOutput.save(os.path.join("Junk", "bModeIm.png"))
        self.plotOnCanvas()

    def mbfChecked(self):
        global curDisp
        if self.displayMbfButton.isChecked():
            if self.displaySsButton.isChecked() or self.displaySiButton.isChecked():
                self.displaySsButton.setChecked(False)
                self.displaySiButton.setChecked(False)
            curDisp = "MBF"
        else:
            curDisp = "clear"
        updateWindows(self.ax)
        self.updateLegend()

    def ssChecked(self):
        global curDisp
        if self.displaySsButton.isChecked():
            if self.displayMbfButton.isChecked() or self.displaySiButton.isChecked():
                self.displayMbfButton.setChecked(False)
                self.displaySiButton.setChecked(False)
            curDisp = "SS"
        else:
            curDisp = "clear"
        updateWindows(self.ax)
        self.updateLegend()

    def siChecked(self):
        global curDisp
        if self.displaySiButton.isChecked():
            if self.displayMbfButton.isChecked() or self.displaySsButton.isChecked():
                self.displayMbfButton.setChecked(False)
                self.displaySsButton.setChecked(False)
            curDisp = "SI"
        else:
            curDisp = "clear"
        updateWindows(self.ax)
        self.updateLegend()

    def computeROIWindows(self): 
        # Compute ROI windows
        global scanConverted
        if self.oneWindow != None:
            self.roiWindowSplinesStruct = RoiPositionsStruct()
            self.roiWindowSplinesStruct.left = [self.oneWindow[0]]
            self.roiWindowSplinesStruct.right = [self.oneWindow[1]]
            self.roiWindowSplinesStruct.top = [self.oneWindow[2]]
            self.roiWindowSplinesStruct.bottom = [self.oneWindow[3]]
            self.roiWindowSplinesStructPreSC = self.roiWindowSplinesStruct
            return
        try:
            self.roiWindowSplinesStruct, self.roiWindowSplinesStructPreSC = roiWindowsGenerator(self.splineX, self.splineY, self.imgDataStruct.scBmode.shape[0], self.imgDataStruct.scBmode.shape[1], self.axialWinSize, self.lateralWinSize, self.imgInfoStruct.axialRes, self.imgInfoStruct.lateralRes, self.axialOverlap, self.lateralOverlap, self.windowThreshold, self.imgDataStruct.scRF.xmap, self.imgDataStruct.scRF.ymap)
            scanConverted = False
            self.cleanStructs()
        except:
            xScale = self.cvIm.width/(self.imgDataStruct.widthPixels)
            yScale = self.cvIm.height/(self.imgDataStruct.depthPixels)
            x = self.splineX/xScale
            y = self.splineY/yScale
            self.roiWindowSplinesStruct = roiWindowsGenerator(x, y, self.imgDataStruct.depthPixels, self.imgDataStruct.widthPixels, self.axialWinSize, self.lateralWinSize, self.imgInfoStruct.axialRes, self.imgInfoStruct.lateralRes, self.axialOverlap, self.lateralOverlap, self.windowThreshold)
            self.roiWindowSplinesStructPreSC = self.roiWindowSplinesStruct
            scanConverted = True

    def displayROIWindows(self):
        if self.oneWindow == None:
            self.splineX = np.clip(self.splineX, a_min=0, a_max=self.cvIm.width)
            self.splineY = np.clip(self.splineY, a_min=0, a_max=self.cvIm.height)
        self.computeROIWindows()
        if len(self.roiWindowSplinesStruct.left) > 0:
            global roisLeft, roisRight, roisTop, roisBottom
            # Prepare ROI window coordinate arrays for graphing
            # Global variables important for matplotlib functions

            if not scanConverted:
                roisLeft = self.roiWindowSplinesStruct.left 
                roisRight = self.roiWindowSplinesStruct.right
                roisTop = self.roiWindowSplinesStruct.top
                roisBottom = self.roiWindowSplinesStruct.bottom
            else:
                xScale = self.cvIm.width/self.imgDataStruct.widthPixels
                yScale = self.cvIm.height/self.imgDataStruct.depthPixels
                for i in range(len(self.roiWindowSplinesStruct.left)):
                    roisLeft.append(self.roiWindowSplinesStruct.left[i]*xScale)#4.2969)
                    roisRight.append(self.roiWindowSplinesStruct.right[i]*xScale)#4.2969)
                    roisTop.append(self.roiWindowSplinesStruct.top[i]*yScale)#/2.79)
                    roisBottom.append(self.roiWindowSplinesStruct.bottom[i]*yScale)#/2.79)
            # self.frame = None
            # computeSpecWindows(self.imgDataStruct.rf,self.refDataStruct.rf, self.roiWindowSplinesStructPreSC.top, self.roiWindowSplinesStructPreSC.bottom, self.roiWindowSplinesStructPreSC.left, self.roiWindowSplinesStructPreSC.right, self.minFrequency, self.maxFrequency, self.lowBandFreq, self.upBandFreq, self.samplingFreq, self.frame)
            # return
            self.computeWindowSpec()

            # Populate parameters in av. spectral parameter textbox
            imMBF = str(int(np.average(mbf)*10)/10)
            imSS = str(int(np.average(ss)*100000000)/100)
            imSI = str(int(np.average(si)*10)/10)
            self.avMbfVal.setText("{0}".format(imMBF))
            self.avSsVal.setText("{0}".format(imSS))
            self.avSiVal.setText("{0}".format(imSI))

            updateWindows(self.ax)
            self.updateLegend()
        # else:
            # self.invalidPath.setText("No statistically significant windows have been found in the\ncurrently drawn ROI.")
        self.plotOnCanvas()
        self.figure.subplots_adjust(left=0,right=1, bottom=0,top=1, hspace=0.2,wspace=0.2)
        plt.tick_params(bottom=False, left=False)
        self.canvas.draw()

    def computeWindowSpec(self):
        global mbf, ss, si, minMBF, maxMBF, minSS, maxSS, minSI, maxSI, windowNPSs, windowFreqs, PsGraphDisplayGUI, mbfPoint
        if not scanConverted:
            self.winTopBottomDepth, self.winLeftRightWidth, mbf, ss, si, windowFreqs, windowNPSs = computeSpecWindows(self.imgDataStruct.rf,self.refDataStruct.rf, self.roiWindowSplinesStructPreSC.top, self.roiWindowSplinesStructPreSC.bottom, self.roiWindowSplinesStructPreSC.left, self.roiWindowSplinesStructPreSC.right, self.minFrequency, self.maxFrequency, self.lowBandFreq, self.upBandFreq, self.samplingFreq, None)
        else:
            if self.imagePathInput.text().endswith('.rfd'):
                self.winTopBottomDepth, self.winLeftRightWidth, mbf, ss, si, windowFreqs, windowNPSs = computeSpecWindows(self.imgDataStruct.rf,self.refDataStruct.rf, self.roiWindowSplinesStructPreSC.top, self.roiWindowSplinesStructPreSC.bottom, self.roiWindowSplinesStructPreSC.left, self.roiWindowSplinesStructPreSC.right, self.minFrequency, self.maxFrequency, self.lowBandFreq, self.upBandFreq, self.samplingFreq, self.frame, self.refInfoStruct.filename)
            else:
                self.winTopBottomDepth, self.winLeftRightWidth, mbf, ss, si, windowFreqs, windowNPSs = computeSpecWindows(self.imgDataStruct.rf,self.refDataStruct.rf, self.roiWindowSplinesStructPreSC.top, self.roiWindowSplinesStructPreSC.bottom, self.roiWindowSplinesStructPreSC.left, self.roiWindowSplinesStructPreSC.right, self.minFrequency, self.maxFrequency, self.lowBandFreq, self.upBandFreq, self.samplingFreq, None)
        minMBF = min(mbf)
        maxMBF = max(mbf)
        minSS = min(ss)
        maxSS = max(ss)
        minSI = min(si)
        maxSI = max(si)
        a = np.average(ss)
        b = np.average(si)
        x = np.linspace(min(windowFreqs), max(windowFreqs), 100)
        y = a*x + b
        median = round((min(windowFreqs)+max(windowFreqs))/2)
        avMBF = a*median + b
        windowFreqs /= 1000000 # Hz -> MHz
        x /= 1000000 # Hz -> MHz
        PsGraphDisplayGUI.ax.vlines([self.imgInfoStruct.lowBandFreq/1000000, self.imgInfoStruct.upBandFreq/1000000], ymin=np.amin(windowNPSs), ymax=np.amax(windowNPSs), colors='purple', label="Band Lims")
        for i in range(len(windowNPSs)):
            PsGraphDisplayGUI.ax.plot(windowFreqs, windowNPSs[i], c='blue', alpha=0.2, zorder=1)
        PsGraphDisplayGUI.ax.plot(windowFreqs, np.mean(windowNPSs, axis=0), c='red', zorder=10, label="NPS")
        PsGraphDisplayGUI.ax.plot(x, y, c='orange', zorder=11, label= "LOBF")
        mbfPoint = PsGraphDisplayGUI.ax.scatter(median/1000000, avMBF, marker="o", zorder=12, c="green", label="MBF")
        PsGraphDisplayGUI.figure.subplots_adjust(left=0.11,right=0.97, bottom=0.2,top=0.96)
        PsGraphDisplayGUI.figure.legend()
        PsGraphDisplayGUI.canvas.draw()

    def updateLegend(self):
        self.figLeg.clear()
        a = np.array([[0,1]])
        self.figLeg = plt.figure()
        if curDisp == "MBF":
            img = plt.imshow(a, cmap='viridis')
            plt.gca().set_visible(False)
            cax = plt.axes([0,0.1,0.35, 0.8])
            # cax = plt.axes([0, 0.1, 0.25, 0.8])
            cbar = plt.colorbar(orientation='vertical', cax=cax)
            plt.text(2.1,0.21,"Midband Fit", rotation = 270, size=9)
            plt.tick_params('y',labelsize=7,pad=0.5)
            # plt.text(3, 0.17, "Midband Fit", rotation=270, size=5) 
            # plt.tick_params('y', labelsize=5, pad=0.7)
            cax.set_yticks([0,0.25, 0.5, 0.75, 1])
            cax.set_yticklabels([int(minMBF*10)/10,int((((maxMBF-minMBF)/4)+minMBF)*10)/10,int((((maxMBF - minMBF)/2)+minMBF)*10)/10,int(((3*(maxMBF-minMBF)/4)+minMBF)*10)/10,int(maxMBF*10)/10])
        elif curDisp == "SS":
            img = plt.imshow(a, cmap='magma')
            plt.gca().set_visible(False)
            cax = plt.axes([0,0.1,0.35,0.8])
            # cax = plt.axes([0, 0.1, 0.25, 0.8])
            cbar = plt.colorbar(orientation='vertical', cax=cax)
            plt.text(2.2,0,"Spectral Slope (1e-6)", rotation = 270, size=6)
            plt.tick_params('y',labelsize=7,pad=0.7)
            # plt.text(3, 0.02, "Spectral Slope (1e-6)", rotation=270, size=4)
            # plt.tick_params('y', labelsize=4, pad=0.3)
            cax.set_yticks([0,0.25, 0.5, 0.75, 1])
            cax.set_yticklabels([int(minSS*100000000)/100,int((((maxSS-minSS)/4)+minSS)*10000000)/100,int((((maxSS - minSS)/2)+minSS)*100000000)/100,int(((3*(maxSS-minSS)/4)+minSS)*100000000)/100,int(maxSS*100000000)/100])
        elif curDisp == "SI":
            img = plt.imshow(a, cmap='plasma')
            plt.gca().set_visible(False)
            cax = plt.axes([0,0.1,0.35,0.8])
            # cax = plt.axes([0, 0.1, 0.25, 0.8])
            cbar = plt.colorbar(orientation='vertical', cax=cax)
            plt.text(2.2, 0.09, 'Spectral Intercept', rotation=270, size = 6)
            plt.tick_params('y', labelsize=7, pad=0.7)
            # plt.text(3, 0, "Spectral Intercept", rotation=270, size=5)
            # plt.tick_params('y', labelsize=5, pad=0.7)
            cax.set_yticks([0,0.25, 0.5, 0.75, 1])
            cax.set_yticklabels([int(minSI*10)/10,int((((maxSI-minSI)/4)+minSI)*10)/10,int((((maxSI - minSI)/2)+minSI)*10)/10,int(((3*(maxSI-minSI)/4)+minSI)*10)/10,int(maxSI*10)/10])
        elif curDisp == "" or curDisp == "clear":
            self.figLeg.set_visible(False)
        self.horizLayoutLeg.removeWidget(self.canvasLeg)
        self.canvasLeg = FigureCanvas(self.figLeg)
        self.horizLayoutLeg.addWidget(self.canvasLeg)
        self.canvasLeg.draw()

    def chooseWindow(self): # select previously computed ROI window to run analysis on
        global tempROISelected, PsGraphDisplayGUI, mbfPoint
        if self.chooseWindowButton.isChecked():
            image, =self.ax.plot([], [], marker="o",markersize=3, markerfacecolor="red")
            self.cid = image.figure.canvas.mpl_connect('button_press_event', onSelect)
            if (selectedROI != -1):
                tempROISelected = True
                updateWindows(self.ax)
        else:
            image, = self.ax.plot([], [], marker="o", markersize=3, markerfacecolor="red")
            
            [PsGraphDisplayGUI.ax.lines.pop() for i in range(2)]
            mbfPoint.remove()
            PsGraphDisplayGUI.figure.legend().remove()

            a = np.average(ss)
            b = np.average(si)
            x = np.linspace(min(windowFreqs*1000000), max(windowFreqs*1000000), 100)
            y = a*x + b
            median = round((min(windowFreqs*1000000)+max(windowFreqs*1000000))/2)
            avMBF = a*median + b
            x /= 1000000 # Hz -> MHz
            PsGraphDisplayGUI.ax.plot()
            PsGraphDisplayGUI.ax.plot(windowFreqs, np.mean(windowNPSs, axis=0), c='red', zorder=10, label="NPS")
            PsGraphDisplayGUI.ax.plot(x, y, c='orange', zorder=11, label= "LOBF")
            mbfPoint = PsGraphDisplayGUI.ax.scatter(median/1000000, avMBF, marker="o", zorder=12, c="green", label="MBF")

            PsGraphDisplayGUI.figure.legend()
            PsGraphDisplayGUI.canvas.draw()

            if curDisp != "clear" and curDisp != "" and selectedROI != -1:
                self.ax.patches.pop()
            self.canvas.draw()
            self.indMbfVal.setText("")
            self.indSsVal.setText("")
            self.indSiVal.setText("")
            tempROISelected = False
            image.figure.canvas.mpl_disconnect(self.cid)
    
    
def onSelect(event): # Update ROI window selected after computation
    global curDisp, coloredROI, tempROISelected, selectedROI, indMBF, indSI, indSS, PsGraphDisplayGUI, mbfPoint
    temp = curDisp
    curDisp = "clear"
    updateWindows(event.inaxes)
    curDisp = temp
    coloredROI = None
    # Find top window selected
    for i in range(len(roisLeft)-1, -1, -1): 
        p = matplotlib.path.Path([(roisLeft[i], roisBottom[i]), (roisLeft[i], roisTop[i]), (roisRight[i], roisTop[i]), (roisRight[i], roisBottom[i])])
        if p.contains_points([(event.xdata, event.ydata)]):
            if curDisp == "MBF":
                if minMBF == maxMBF:
                    coloredROI = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, facecolor=cmap[125], edgecolor='white')
                else:
                    coloredROI = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, facecolor=cmap[int((255/(maxMBF-minMBF))*(mbf[i]-minMBF))], edgecolor='white')
            elif curDisp == "SS":
                if minSS == maxSS:
                    coloredROI = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, facecolor=cmap[125], edgecolor='white')
                else:
                    coloredROI = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, facecolor=cmap[int((255/(maxSS-minSS))*(ss[i]-minSS))], edgecolor='white')
            elif curDisp == "SI":
                if minSI == maxSI:
                    coloredROI = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, facecolor=cmap[125], edgecolor='white')
                else:
                    coloredROI = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, facecolor=cmap[int((255/(maxSI-minSI))*(si[i]-minSI))], edgecolor='white')
            selectedROI = i
            indMBF.setText("{0}".format(round(mbf[i], 2)))
            indSS.setText("{0}".format(round(ss[i]*1000000, 2)))
            indSI.setText("{0}".format(round(si[i], 2)))
            tempROISelected = True
            break
    
    # Display all ROI windows
    for i in range(len(roisLeft)):
        if curDisp == "MBF":
            if maxMBF == minMBF:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[125])
            else:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[int((255/(maxMBF-minMBF))*(mbf[i]-minMBF))])
            event.inaxes.add_patch(rect)
        elif curDisp == "SS":
            if maxSS == minSS:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[125])
            else:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[int((255/(maxSS-minSS))*(ss[i]-minSS))])
            event.inaxes.add_patch(rect)
        elif curDisp == "SI":
            if maxSI == minSI:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[125])
            else:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[int((255/(maxSI-minSI))*(si[i]-minSI))])
            event.inaxes.add_patch(rect)
    if coloredROI is not None:
        event.inaxes.add_patch(coloredROI)
        [PsGraphDisplayGUI.ax.lines.pop() for i in range(2)]
        mbfPoint.remove()
        a = ss[selectedROI]
        b = si[selectedROI]
        x = windowFreqs * 1000000
        y = a*x + b
        x /= 1000000
        mid = mbf[selectedROI]
        nps = windowNPSs[selectedROI]
        PsGraphDisplayGUI.ax.plot(windowFreqs, nps, c='red', zorder=10, label="NPS")
        PsGraphDisplayGUI.ax.plot(x, y, c='orange', zorder=11, label="LOBF")
        mbfPoint = PsGraphDisplayGUI.ax.scatter(windowFreqs[round(len(windowFreqs)/2)], mid, marker='o', zorder=12, label="MBF", c="green")
        PsGraphDisplayGUI.figure.legend().remove()
        PsGraphDisplayGUI.figure.legend()
        PsGraphDisplayGUI.canvas.draw()

    event.inaxes.figure.canvas.draw()

def updateWindows(curAx):
    global cmap
    if curDisp == "":
        return
    # Initialize correct spectral parameter heatmap
    if len(curAx.patches) != 0:
        for i in range(len(curAx.patches)):
            curAx.patches.pop()
    if curDisp == "clear":
        curAx.figure.canvas.draw()
        return
    # Prepare correct spectral parameter colormap
    if curDisp == "MBF":
        cmapStruct = plt.get_cmap('viridis')
    elif curDisp == "SS":
        cmapStruct = plt.get_cmap('magma')
    elif curDisp == "SI":
        cmapStruct = plt.get_cmap('plasma')
    cmap = cmapStruct.colors
    for i in range(len(roisLeft)):
        # Create a Rectangle patch (format of bottom-left anchor, width, height)
        if curDisp == "MBF":
            if maxMBF == minMBF:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[125])
            else:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[int((255/(maxMBF-minMBF))*(mbf[i]-minMBF))])
        elif curDisp == "SS":
            if maxSS == minSS:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[125])
            else:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[int((255/(maxSS-minSS))*(ss[i]-minSS))])
        elif curDisp == "SI":
            if maxSI == minSI:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[125])
            else:
                rect = matplotlib.patches.Rectangle((roisLeft[i], roisBottom[i]), (roisRight[i]-roisLeft[i]), (roisTop[i]-roisBottom[i]), linewidth=1, fill = True, color=cmap[int((255/(maxSI-minSI))*(si[i]-minSI))])
        curAx.add_patch(rect)
    if tempROISelected: # Highlight selected ROI
        global coloredROI
        if curDisp == "MBF":
            if maxMBF == minMBF:
                coloredROI = matplotlib.patches.Rectangle((roisLeft[selectedROI], roisBottom[selectedROI]), (roisRight[selectedROI]-roisLeft[selectedROI]), (roisTop[selectedROI]-roisBottom[selectedROI]), linewidth=1, fill = True, facecolor=cmap[125], edgecolor='white')
            else:
                coloredROI = matplotlib.patches.Rectangle((roisLeft[selectedROI], roisBottom[selectedROI]), (roisRight[selectedROI]-roisLeft[selectedROI]), (roisTop[selectedROI]-roisBottom[selectedROI]), linewidth=1, fill = True, facecolor=cmap[int((255/(maxMBF-minMBF))*(mbf[selectedROI]-minMBF))], edgecolor='white')
        elif curDisp == "SS":
            if maxSS == minSS:
                coloredROI = matplotlib.patches.Rectangle((roisLeft[selectedROI], roisBottom[selectedROI]), (roisRight[selectedROI]-roisLeft[selectedROI]), (roisTop[selectedROI]-roisBottom[selectedROI]), linewidth=1, fill = True, facecolor=cmap[125], edgecolor='white')
            else:
                coloredROI = matplotlib.patches.Rectangle((roisLeft[selectedROI], roisBottom[selectedROI]), (roisRight[selectedROI]-roisLeft[selectedROI]), (roisTop[selectedROI]-roisBottom[selectedROI]), linewidth=1, fill = True, facecolor=cmap[int((255/(maxSS-minSS))*(ss[selectedROI]-minSS))], edgecolor='white')
        elif curDisp == "SI":
            if maxSI == minSI:
                coloredROI = matplotlib.patches.Rectangle((roisLeft[selectedROI], roisBottom[selectedROI]), (roisRight[selectedROI]-roisLeft[selectedROI]), (roisTop[selectedROI]-roisBottom[selectedROI]), linewidth=1, fill = True, facecolor=cmap[125], edgecolor='white')
            else:
                coloredROI = matplotlib.patches.Rectangle((roisLeft[selectedROI], roisBottom[selectedROI]), (roisRight[selectedROI]-roisLeft[selectedROI]), (roisTop[selectedROI]-roisBottom[selectedROI]), linewidth=1, fill = True, facecolor=cmap[int((255/(maxSI-minSI))*(si[selectedROI]-minSI))], edgecolor='white')
        curAx.add_patch(coloredROI)
    curAx.figure.canvas.draw()

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