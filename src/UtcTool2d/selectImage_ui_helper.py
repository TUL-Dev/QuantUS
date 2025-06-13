import os
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog

from pyquantus.parse.canon import findPreset
from pyquantus.parse.philipsMat import philips2dRfMatParser
from pyquantus.parse.philipsRf import philipsRfParser
from pyquantus.parse.siemens import siemensRfParser
from pyquantus.parse.clarius import ClariusTarUnpacker, clariusRfParser
from pyquantus.utc import UtcData
from pyquantus.parse.objects import ScConfig
from src.UtcTool2d.loadingScreen_ui_helper import LoadingScreenGUI
from src.UtcTool2d.selectImage_ui import Ui_selectImage
from src.UtcTool2d.roiSelection_ui_helper import RoiSelectionGUI
import src.Parsers.philips3dRf as phil3d


def selectImageHelper(pathInput, fileExts, startDir):
    if not Path(startDir).exists():
        startDir = str(Path.home())
    fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter=fileExts, directory=startDir)
    if fileName != "":  # If valid file is chosen
        pathInput.setText(fileName)
    else:
        return


class SelectImageGUI_UtcTool2dIQ(Ui_selectImage, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setLayout(self.fullScreenLayout)
        self.restartChoice()

        self.welcomeGui: QWidget
        self.roiSelectionGUI = None
        self.machine = None
        self.fileExts = None
        self.frame = 0
        self.imArray: np.ndarray
        self.loadingScreen = LoadingScreenGUI()

        self.terasonButton.clicked.connect(self.terasonClicked)
        self.philipsButton.clicked.connect(self.philipsClicked)
        self.canonButton.clicked.connect(self.canonClicked)
        self.clariusButton.clicked.connect(self.clariusClicked)
        self.siemensButton.clicked.connect(self.siemensClicked)
        # self.verasonicsButton.clicked.connect(self.verasonicsClicked)
        self.chooseImageFileButton.clicked.connect(self.selectImageFile)
        self.choosePhantomFileButton.clicked.connect(self.selectPhantomFile)
        self.clearImagePathButton.clicked.connect(self.clearImagePath)
        self.clearPhantomPathButton.clicked.connect(self.clearPhantomPath)
        self.generateImageButton.clicked.connect(self.moveToRoiSelection)
        self.backButton.clicked.connect(self.backToWelcomeScreen)
        self.backToImgSelButton.clicked.connect(self.restartChoice)
        
    def restartChoice(self):
        self.fullScreenLayout.removeItem(self.imgSelectionLayout)
        self.hideImgSelectionLayout()
        self.fullScreenLayout.removeItem(self.framePreviewLayout)
        self.hideFramePreviewLayout()
        if self.parserOptionsLayout in [self.fullScreenLayout.itemAt(i) for i in range(self.fullScreenLayout.count())]:
            self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.fullScreenLayout.addItem(self.parserOptionsLayout)
        self.showParserOptionsLayout()
        self.fullScreenLayout.setStretchFactor(self.sidebarLayout, 1)
        self.fullScreenLayout.setStretchFactor(self.parserOptionsLayout, 10)

    def backToWelcomeScreen(self):
        self.welcomeGui.show()
        self.welcomeGui.resize(self.size())
        self.hide()
        
    def backToChoice(self):
        self.frame = 0
        if self.framePreviewLayout in [self.fullScreenLayout.itemAt(i) for i in range(self.fullScreenLayout.count())]:
            self.fullScreenLayout.removeItem(self.framePreviewLayout)
        self.hideFramePreviewLayout()
        if self.imgSelectionLayout in [self.fullScreenLayout.itemAt(i) for i in range(self.fullScreenLayout.count())]:
            self.fullScreenLayout.removeItem(self.imgSelectionLayout)
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.showImgSelectionLayout()
        self.philips3dCheckBox.hide()
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.generateImageButton.setText("Generate Image")
        self.selectImageErrorMsg.hide()
        
    def hideParserOptionsLayout(self):
        self.canonButton.hide()
        self.clariusButton.hide()
        self.verasonicsButton.hide()
        self.terasonButton.hide()
        self.philipsButton.hide()
        self.siemensButton.hide()
        self.selectImageMethodLabel.hide()
        
    def showParserOptionsLayout(self):
        self.canonButton.show()
        self.clariusButton.show()
        self.verasonicsButton.show()
        self.terasonButton.show()
        self.philipsButton.show()
        self.siemensButton.show()
        self.selectImageMethodLabel.show()
        
    def hideImgSelectionLayout(self):
        self.generateImageButton.hide()
        self.choosePhantomFileButton.hide()
        self.clearPhantomPathButton.hide()
        self.phantomPathInput.hide()
        self.phantomPathLabel.hide()
        self.chooseImageFileButton.hide()
        self.clearImagePathButton.hide()
        self.imagePathInput.hide()
        self.imagePathLabel.hide()
        self.philips3dCheckBox.hide()
        self.selectDataLabel.hide()
        self.selectImageErrorMsg.hide()
    
    def showImgSelectionLayout(self):
        self.generateImageButton.show()
        self.choosePhantomFileButton.show()
        self.clearPhantomPathButton.show()
        self.phantomPathInput.show()
        self.phantomPathLabel.show()
        self.chooseImageFileButton.show()
        self.clearImagePathButton.show()
        self.imagePathInput.show()
        self.imagePathLabel.show()
        self.philips3dCheckBox.show()
        self.selectDataLabel.show()
        
    def hideFramePreviewLayout(self):
        self.totalFramesLabel.hide()
        self.ofFramesLabel.hide()
        self.curFrameSlider.hide()
        self.curFrameLabel.hide()
        self.acceptFrameButton.hide()
        self.backFromFramesButton.hide()
        self.imPreview.hide()
        self.selectFrameLabel.hide()
        
    def showFramePreviewLayout(self):
        self.totalFramesLabel.show()
        self.ofFramesLabel.show()
        self.curFrameSlider.show()
        self.curFrameLabel.show()
        self.acceptFrameButton.show()
        self.backFromFramesButton.show()
        self.imPreview.show()
        self.selectFrameLabel.show()

    def moveToRoiSelection(self):
        if self.machine == "Verasonics":
            self.phantomPathInput.setText(self.imagePathInput.text())
        if os.path.exists(self.imagePathInput.text()) and os.path.exists(
            self.phantomPathInput.text()
        ):
            self.loadingScreen.show()
            QApplication.processEvents()
            if self.roiSelectionGUI is not None:
                plt.close(self.roiSelectionGUI.figure)
            del self.roiSelectionGUI
            self.roiSelectionGUI = RoiSelectionGUI()
            self.roiSelectionGUI.utcData = UtcData()
            self.roiSelectionGUI.setFilenameDisplays(
                self.imagePathInput.text().split("/")[-1],
                self.phantomPathInput.text().split("/")[-1],
            )
            self.roiSelectionGUI.imagePath = Path(self.imagePathInput.text()).absolute()
            if self.machine == "Verasonics":
                self.roiSelectionGUI.openImageVerasonics(
                    self.imagePathInput.text(), self.phantomPathInput.text()
                )
            elif self.machine == "Canon":
                preset1 = findPreset(self.imagePathInput.text())
                preset2 = findPreset(self.phantomPathInput.text())
                if preset1 == preset2:
                    self.roiSelectionGUI.openImageCanon(
                        self.imagePathInput.text(), self.phantomPathInput.text()
                    )
                else:
                    self.selectImageErrorMsg.setText("ERROR: Presets don't match")
                    self.selectImageErrorMsg.show()
                    return
            elif self.machine == "Clarius":
                self.openClariusImage()
                return
            elif self.machine == "Terason":
                self.roiSelectionGUI.openImageTerason(
                    self.imagePathInput.text(), self.phantomPathInput.text()
                )
            elif self.machine == "Philips":
                self.openPhilipsImage()
                return
            elif self.machine == "Siemens":
                self.openSiemensImage()
                return
            else:
                print("ERROR: Machine match not found")
                return
            self.roiSelectionGUI.show()
            self.roiSelectionGUI.lastGui = self
            self.selectImageErrorMsg.hide()
            self.loadingScreen.hide()
            self.roiSelectionGUI.resize(self.size())
            self.hide()

    def openSiemensImage(self):
        imageFilePath = self.imagePathInput.text()
        phantomFilePath = self.phantomPathInput.text()

        self.imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = siemensRfParser(
            imageFilePath, phantomFilePath)
        self.initialImgRf = self.imgDataStruct.rf
        self.initialRefRf = self.refDataStruct.rf

        if self.imArray.shape[0] == 1:
            self.acceptSiemensFrame()
        else:
            self.acceptFrameButton.clicked.connect(self.acceptSiemensFrame)
            self.backFromFramesButton.clicked.connect(self.backToChoice)
            self.displaySlidingFrames()
        
    def openClariusImage(self):
        if self.imagePathInput.text().endswith(".tar"):
            ClariusTarUnpacker(self.imagePathInput.text(), "single_tar")
            unpackedTarFolder = Path(self.imagePathInput.text().replace(".tar", "_extracted"))
            imageRfPath = ""; imageTgcPath = ""; imageInfoPath = ""
            for file in unpackedTarFolder.iterdir():
                if file.name.endswith("_rf.raw"):
                    imageRfPath = str(file)
                elif file.name.endswith("_env.tgc.yml"):
                    imageTgcPath = str(file)
                elif file.name.endswith("_rf.yml"):
                    imageInfoPath = str(file)
            if imageRfPath == "" or imageInfoPath == "":
                raise Exception("Missing files in tar")
            if imageTgcPath == "":
                imageTgcPath = None
        else:
            imageRfPath = self.imagePathInput.text()
            imageInfoPath = imageRfPath.replace(".raw", ".yml")
            imageTgcPath = imageRfPath.replace("_rf.raw", "_env.tgc.yml")
        if self.phantomPathInput.text().endswith(".tar"):
            ClariusTarUnpacker(self.phantomPathInput.text(), "single_tar")
            unpackedTarFolder = Path(self.phantomPathInput.text().replace(".tar", "_extracted"))
            phantomRfPath = ""; phantomTgcPath = ""; phantomInfoPath = ""
            for file in unpackedTarFolder.iterdir():            
                if file.name.endswith("_rf.raw"):
                    phantomRfPath = str(file.absolute())
                elif file.name.endswith("_env.tgc.yml"):
                    phantomTgcPath = str(file.absolute())
                elif file.name.endswith("_rf.yml"):
                    phantomInfoPath = str(file.absolute())
            if phantomRfPath == "" or phantomInfoPath == "":
                raise Exception("Missing files in tar")
            if phantomTgcPath == "":
                phantomTgcPath = None
        else:
            phantomRfPath = self.phantomPathInput.text()
            phantomInfoPath = phantomRfPath.replace(".raw", ".yml")
            phantomTgcPath = phantomRfPath.replace("_rf.raw", "_env.tgc.yml")
            
            if not Path(imageTgcPath).exists():
                imageTgcPath = None
            if not Path(phantomTgcPath).exists():
                phantomTgcPath = None

        self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct, scanConverted = clariusRfParser(
            imageRfPath, imageTgcPath, imageInfoPath,
            phantomRfPath, phantomTgcPath, phantomInfoPath,
            visualize=False, use_tgc=True
        )
        
        utcData = UtcData()
        
        if scanConverted:
            self.imArray = self.imgDataStruct.scBmode
            scConfig = ScConfig()
            scConfig.width = self.imgInfoStruct.width1
            scConfig.tilt = self.imgInfoStruct.tilt1
            scConfig.startDepth = self.imgInfoStruct.startDepth1
            scConfig.endDepth = self.imgInfoStruct.endDepth1
            utcData.scConfig = scConfig
            self.roiSelectionGUI.ultrasoundImage.xmap = self.imgDataStruct.scBmodeStruct.xmap
            self.roiSelectionGUI.ultrasoundImage.ymap = self.imgDataStruct.scBmodeStruct.ymap
        else:
            self.imArray = self.imgDataStruct.bMode
            
        self.initialImgRf = self.imgDataStruct.rf
        self.initialRefRf = self.refDataStruct.rf
        self.roiSelectionGUI.utcData = utcData

        if self.imArray.shape[0] == 1:
            self.acceptClariusFrame()
        else:
            self.acceptFrameButton.clicked.connect(self.acceptClariusFrame)
            self.backFromFramesButton.clicked.connect(self.backToChoice)
            self.displaySlidingFrames()

    def openPhilipsImage(self):
        imageFilePath = Path(self.imagePathInput.text())
        phantomFilePath = Path(self.phantomPathInput.text())
        
        if self.philips3dCheckBox.isChecked():
            if imageFilePath.suffix != '.rf' or phantomFilePath.suffix != '.rf':
                raise Exception("Please select .rf files for Philips 3D")
            self.imgDataStruct, self.imgInfoStruct = phil3d.getVolume(imageFilePath)
            self.refDataStruct, self.refInfoStruct = phil3d.getVolume(phantomFilePath)
            self.imArray = self.imgDataStruct.bMode
            self.initialImgRf = self.imgDataStruct.rf
            self.initialRefRf = self.refDataStruct.rf
            self.displaySlidingFrames()
            return
        
        imageFile = open(imageFilePath, 'rb')
        imageSig = list(imageFile.read(8))
        phantomFile = open(phantomFilePath, 'rb')
        phantomSig = list(phantomFile.read(8))
        
        if imageFilePath.suffix == '.rf':
            assert imageSig == [0,0,0,0,255,255,0,0]
            destImgFilePath = Path(imageFilePath.__str__().replace('.rf', '.mat'))
            philipsRfParser(imageFilePath.__str__())
            
        if phantomFilePath.suffix == '.rf':
            assert phantomSig == [0,0,0,0,255,255,0,0]
            destPhantomFilePath = Path(phantomFilePath.__str__().replace('.rf', '.mat'))
            philipsRfParser(phantomFilePath.__str__())
        
        if imageFilePath.suffix == '.mat':
            destImgFilePath = imageFilePath
        if phantomFilePath.suffix == '.mat':
            destPhantomFilePath = phantomFilePath

        self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = philips2dRfMatParser(
            destImgFilePath, destPhantomFilePath, self.frame)
        self.imData = self.imgDataStruct.bMode
        self.initialImgRf = [self.imgDataStruct.rf]
        self.initialRefRf = [self.refDataStruct.rf]
        
        scConfig = ScConfig()
        scConfig.width = self.imgInfoStruct.width1
        scConfig.tilt = self.imgInfoStruct.tilt1
        scConfig.startDepth = self.imgInfoStruct.startDepth1
        scConfig.endDepth = self.imgInfoStruct.endDepth1

        utcData = UtcData()
        utcData.scConfig = scConfig
        self.roiSelectionGUI.utcData = utcData
        self.roiSelectionGUI.ultrasoundImage.bmode = self.imgDataStruct.bMode
        self.roiSelectionGUI.ultrasoundImage.scBmode = self.imgDataStruct.scBmodeStruct.scArr
        self.roiSelectionGUI.ultrasoundImage.xmap = self.imgDataStruct.scBmodeStruct.xmap
        self.roiSelectionGUI.ultrasoundImage.ymap = self.imgDataStruct.scBmodeStruct.ymap
        self.roiSelectionGUI.ultrasoundImage.axialResRf = self.imgInfoStruct.depth / self.imgDataStruct.rf.shape[0]
        self.roiSelectionGUI.ultrasoundImage.lateralResRf = self.roiSelectionGUI.ultrasoundImage.axialResRf * (
            self.imgDataStruct.rf.shape[0]/self.imgDataStruct.rf.shape[1]
        ) # placeholder
        self.acceptFrame()

    def displaySlidingFrames(self):
        self.imData = np.array(self.imArray[self.frame]).reshape(self.imArray.shape[1], self.imArray.shape[2])
        self.imData = np.require(self.imData,np.uint8,'C')
        self.bytesLine = self.imData.strides[0]
        self.arHeight = self.imData.shape[0]
        self.arWidth = self.imData.shape[1]
        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format.Format_Grayscale8)
        self.imPreview.setPixmap(QPixmap.fromImage(self.qIm).scaled(self.imPreview.width(), self.imPreview.height(), Qt.AspectRatioMode.IgnoreAspectRatio))

        self.fullScreenLayout.removeItem(self.imgSelectionLayout)
        self.hideImgSelectionLayout()
        self.fullScreenLayout.addItem(self.framePreviewLayout)
        self.showFramePreviewLayout()
        self.fullScreenLayout.setStretchFactor(self.framePreviewLayout, 10)
        self.totalFramesLabel.setText(str(self.imArray.shape[0]-1))
        self.curFrameSlider.setMinimum(0)
        self.curFrameSlider.setMaximum(self.imArray.shape[0]-1)
        self.curFrameSlider.valueChanged.connect(self.frameChanged)
        self.curFrameLabel.setText("0")
        self.loadingScreen.hide()
        self.update()
    
    def frameChanged(self):
        self.frame = self.curFrameSlider.value()
        self.curFrameLabel.setText(str(self.frame))
        self.plotPreviewFrame()

    def acceptSiemensFrame(self):
        self.roiSelectionGUI.ultrasoundImage.bmode = self.imgDataStruct.bMode[self.frame]
        self.roiSelectionGUI.ultrasoundImage.axialResRf = self.imgInfoStruct.depth / self.initialImgRf.shape[1]
        self.roiSelectionGUI.ultrasoundImage.lateralResRf = self.roiSelectionGUI.ultrasoundImage.axialResRf * (
            self.initialImgRf.shape[1]/self.initialImgRf.shape[2]
        ) # placeholder
        self.imgDataStruct.rf = self.initialImgRf[self.frame]
        self.refDataStruct.rf = self.initialRefRf[0]
        self.acceptFrame()
        
        self.roiSelectionGUI.editImageDisplayGUI.contrastVal.setValue(1)
        self.roiSelectionGUI.editImageDisplayGUI.brightnessVal.setValue(1)
        self.roiSelectionGUI.editImageDisplayGUI.sharpnessVal.setValue(1)

    def acceptClariusFrame(self):
        if hasattr(self.imgDataStruct, 'scBmode'):
            self.roiSelectionGUI.ultrasoundImage.scBmode = self.imgDataStruct.scBmode[self.frame]
        self.roiSelectionGUI.ultrasoundImage.bmode = self.imgDataStruct.bMode[self.frame]
        self.roiSelectionGUI.ultrasoundImage.axialResRf = self.imgInfoStruct.depth / self.initialImgRf.shape[1]
        self.roiSelectionGUI.ultrasoundImage.lateralResRf = self.roiSelectionGUI.ultrasoundImage.axialResRf * (
            self.initialImgRf.shape[1]/self.initialImgRf.shape[2]
        )
        self.imgDataStruct.rf = self.initialImgRf[self.frame]
        self.refDataStruct.rf = self.initialRefRf[self.frame]
        self.acceptFrame()
        
        self.roiSelectionGUI.editImageDisplayGUI.contrastVal.setValue(1)
        self.roiSelectionGUI.editImageDisplayGUI.brightnessVal.setValue(1)
        self.roiSelectionGUI.editImageDisplayGUI.sharpnessVal.setValue(1)

    def acceptFrame(self):
        self.roiSelectionGUI.frame = self.frame
        self.roiSelectionGUI.processImage(self.imgDataStruct, self.refDataStruct, self.imgInfoStruct, self.refInfoStruct)
        self.roiSelectionGUI.lastGui = self
        self.roiSelectionGUI.show()
        self.roiSelectionGUI.resize(self.size())
        self.loadingScreen.hide()
        self.hide()

    def plotPreviewFrame(self):
        self.imData = np.array(self.imArray[self.frame]).reshape(self.imArray.shape[1], self.imArray.shape[2])
        self.imData = np.require(self.imData,np.uint8,'C')
        self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format.Format_Grayscale8)
        self.imPreview.setPixmap(QPixmap.fromImage(self.qIm).scaled(self.imPreview.width(), self.imPreview.height(), Qt.AspectRatioMode.IgnoreAspectRatio))
        self.update()

    def clearImagePath(self):
        self.imagePathInput.clear()

    def clearPhantomPath(self):
        self.phantomPathInput.clear()

    def philipsClicked(self):
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.showImgSelectionLayout()
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)

        self.imagePathLabel.setText("Input Path to Image file\n (.rf, .mat)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.rf, .mat)")

        self.machine = "Philips"
        self.fileExts = "*.rf *.mat"

    def terasonClicked(self):
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.showImgSelectionLayout()
        self.philips3dCheckBox.hide()

        self.imagePathLabel.setText("Input Path to Image file\n (.mat)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.mat)")

        self.machine = "Terason"
        self.fileExts = "*.mat"

    def siemensClicked(self):
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.showImgSelectionLayout()
        self.philips3dCheckBox.hide()

        self.imagePathLabel.setText("Input Path to Image file\n (.rfd)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.rfd)")

        self.machine = "Siemens"
        self.fileExts = "*.rfd"

    def canonClicked(
        self,
    ):  # Move user to screen to select individual files to generate image
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.showImgSelectionLayout()
        self.philips3dCheckBox.hide()
        
        self.imagePathLabel.setText("Input Path to Image file\n (.bin)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.bin)")

        self.machine = "Canon"
        self.fileExts = "*.bin"

    def clariusClicked(self):
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.showImgSelectionLayout()
        self.philips3dCheckBox.hide()
        
        self.imagePathLabel.setText("Input Path to Image file\n (.raw, .tar)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.raw, .tar)")

        self.machine = "Clarius"
        self.fileExts = "*.raw *.tar"

    def verasonicsClicked(
        self,
    ):  # Move user to screen to select individual files to generate image
        self.fullScreenLayout.removeItem(self.parserOptionsLayout)
        self.hideParserOptionsLayout()
        self.fullScreenLayout.addItem(self.imgSelectionLayout)
        self.fullScreenLayout.setStretchFactor(self.imgSelectionLayout, 10)
        self.showImgSelectionLayout()
        self.philips3dCheckBox.hide()
        self.phantomPathInput.hide()
        self.clearPhantomPathButton.hide()
        
        self.imagePathLabel.setText("Input Path to Image file\n (.mat)")

        self.machine = "Verasonics"
        self.fileExts = "*.mat"

    def selectImageFile(self):
        # Create folder to store ROI drawings
        if os.path.exists("Junk"):
            shutil.rmtree("Junk")
        os.mkdir("Junk")

        selectImageHelper(self.imagePathInput, self.fileExts, str(Path(self.imagePathInput.text()).parent))
        self.selectImageErrorMsg.hide()

    def selectPhantomFile(self):
        selectImageHelper(self.phantomPathInput, self.fileExts, str(Path(self.imagePathInput.text()).parent))
        self.selectImageErrorMsg.hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    ui = SelectImageGUI_UtcTool2dIQ()
    ui.show()
    sys.exit(app.exec_())

