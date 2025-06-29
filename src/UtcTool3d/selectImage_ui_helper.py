import os
import pickle
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog
from pyquantus.utc import UtcData, UltrasoundImage

from src.UtcTool3d.philips3dRf import philipsRfParser3d, getVolume
from src.UtcTool3d.selectImage_ui import Ui_selectImage
from src.UtcTool3d.loadingScreen_ui_helper import LoadingScreenGUI
from src.UtcTool3d.voiSelection_ui_helper import VoiSelectionGUI
import src.Utils.utils as ut
from src.Parsers.philipsSipVolumeParser import sipParser

def selectImageHelper(pathInput, fileExts):
    if not os.path.exists(pathInput.text()):  # check if file path is manually typed
        fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter=fileExts)
        if fileName != "":  # If valid file is chosen
            pathInput.setText(fileName)
        else:
            return

class SelectImageGUI_UtcTool3d(Ui_selectImage, QWidget):
    def __init__(self):
        # self.selectImage = QWidget()
        super().__init__()
        self.setupUi(self)

        self.setLayout(self.fullScreenLayout)
        self.fullScreenLayout.removeItem(self.imgSelectionLayout)
        self.hideImgSelectionLayout()

        self.voiSelectionGui: VoiSelectionGUI | None = None
        self.loadingScreen = LoadingScreenGUI()
        self.welcomeGui = None
        self.fileExts = ""
        self.timeconst = None
        self.backButton.clicked.connect(self.backToWelcomeScreen)
        self.philipsButton.clicked.connect(self.philipsClicked)
        self.chooseImageFileButton.clicked.connect(self.selectImageFile)
        self.clearImagePathButton.clicked.connect(self.clearImagePathInput)
        self.generateImageButton.clicked.connect(self.openPhilipsImage)
        
    def philipsClicked(self):
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.showImgSelectionLayout()
        self.imagePathLabel.setText('Input Path to Image file\n (.rf)')
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.fileExts = "*.rf"
        self.prepareForVoiSelection()
        
    def backToWelcomeScreen(self):
        self.welcomeGui.show()
        self.welcomeGui.resize(self.size())
        self.hide()
        
    def hideParserOptionsLayout(self):
        self.philipsButton.hide()
        self.selectImageMethodLabel.hide()
        
    def showParserOptionsLayout(self):
        self.philipsButton.show()
        self.selectImageMethodLabel.show()
        
    def hideImgSelectionLayout(self):
        self.generateImageButton.hide()
        self.clearImagePathButton.hide()
        self.selectImageErrorMsg.hide()
        self.chooseImageFileButton.hide()
        self.clearImagePathButton.hide()
        self.imagePathInput.hide()
        self.imagePathLabel.hide()
        self.selectDataLabel.hide()
        self.hideFrameRateLabels()
        
    def showImgSelectionLayout(self):
        self.generateImageButton.show()
        self.chooseImageFileButton.show()
        self.clearImagePathButton.show()
        self.imagePathInput.show()
        self.imagePathLabel.show()
        self.selectDataLabel.show()
        
    def hideFrameRateLabels(self):
        self.frameRateLabel.hide()
        self.frameRateValue.hide()
        
    def showFrameRateLabels(self):
        self.frameRateLabel.show()
        self.frameRateValue.show()
        
    def openPhilipsImage(self):
        self.loadingScreen.show()
        QApplication.processEvents()
        
        imageFilePath = Path(self.imagePathInput.text())
        
        if imageFilePath.suffix != '.rf':
            raise Exception("Please select .rf files for Philips 3D")
        
        self.imgDataStruct, self.imgInfoStruct = getVolume(imageFilePath)
        
        self.imgDataStruct.scBmode = np.expand_dims(self.imgDataStruct.scBmode, axis=3)
        self.voiSelectionGui.data4dImg = self.imgDataStruct.scBmode
        self.voiSelectionGui.preScData4dImg = self.imgDataStruct.bMode
        self.voiSelectionGui.rfData4dImg = self.imgDataStruct.rf
        self.voiSelectionGui.samplingFrequency = self.imgInfoStruct.samplingFrequency
        self.voiSelectionGui.centerFrequency = self.imgInfoStruct.centerFrequency
        self.voiSelectionGui.transducerFreqBand = [self.imgInfoStruct.minFrequency, self.imgInfoStruct.maxFrequency]
        self.voiSelectionGui.analysisFreqBand = [self.imgInfoStruct.lowBandFreq, self.imgInfoStruct.upBandFreq]
        self.moveToVoiSelection()
        self.loadingScreen.hide()
        

    def clearImagePathInput(self):
        self.imagePathInput.clear()

    def backFromPhilips(self):
        self.fullScreenLayout.removeItem(self.imgSelectionLayout)
        self.hideImgSelectionLayout()
        self.showParserOptionsLayout()
        self.fullScreenLayout.addItem(self.parserOptionsLayout)
        self.fullScreenLayout.setStretchFactor(self.parserOptionsLayout, 10)
        self.frameRateValue.setValue(0)
            
    def prepareForVoiSelection(self):
        del self.voiSelectionGui
        self.voiSelectionGui = VoiSelectionGUI()
        self.voiSelectionGui.setFilenameDisplays(self.imagePathInput.text())
        
    def moveToVoiSelection(self):
        self.voiSelectionGui.imgDataStruct = self.imgDataStruct
        self.voiSelectionGui.imgInfoStruct = self.imgInfoStruct
        self.voiSelectionGui.imagePath = Path(self.imagePathInput.text())
        self.voiSelectionGui.openImage()
        self.voiSelectionGui.lastGui = self
        self.voiSelectionGui.show()
        self.voiSelectionGui.resize(self.size())
        
        self.hide()
        
    def selectImageFile(self):
        selectImageHelper(self.imagePathInput, self.fileExts)
        self.selectImageErrorMsg.hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    ui = SelectImageGUI_UtcTool3d()
    ui.show()
    sys.exit(app.exec_())
