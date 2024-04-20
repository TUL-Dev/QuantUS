from UtcTool2d.selectImage_ui import Ui_selectImage
from UtcTool2d.roiSelection_ui_helper import RoiSelectionGUI
from Parsers.canonBinParser import findPreset
import Parsers.siemensRfdParser as rfdParser

from PyQt5.QtWidgets import QWidget, QApplication, QFileDialog
from PyQt5.QtGui import QImage, QPixmap
import shutil
import os
import matplotlib.pyplot as plt
import platform
import numpy as np

system = platform.system()


def selectImageHelper(pathInput, fileExts):
    if not os.path.exists(pathInput.text()):  # check if file path is manually typed
        # NOTE: .bin is currently not supported
        fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter=fileExts)
        if fileName != "":  # If valid file is chosen
            pathInput.setText(fileName)
        else:
            return


class SelectImageGUI_UtcTool2dIQ(Ui_selectImage, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        if system == "Windows":
            self.roiSidebarLabel.setStyleSheet(
                """QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }"""
            )
            self.imageSelectionLabelSidebar.setStyleSheet(
                """QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }"""
            )
            self.imageLabel.setStyleSheet(
                """QLabel {
                font-size: 13px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }"""
            )
            self.phantomLabel.setStyleSheet(
                """QLabel {
                font-size: 13px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }"""
            )
            self.imageFilenameDisplay.setStyleSheet(
                """QLabel {
                font-size: 11px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
            }"""
            )
            self.phantomFilenameDisplay.setStyleSheet(
                """QLabel {
                font-size: 11px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
            }"""
            )
            self.analysisParamsLabel.setStyleSheet(
                """QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }"""
            )
            self.rfAnalysisLabel.setStyleSheet(
                """QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }"""
            )
            self.exportResultsLabel.setStyleSheet(
                """QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }"""
            )

        self.chooseImageFileButton.setHidden(True)
        self.choosePhantomFileButton.setHidden(True)
        self.chooseImageFolderButton.setHidden(True)
        self.choosePhantomFolderButton.setHidden(True)
        self.clearImagePathButton.setHidden(True)
        self.clearPhantomPathButton.setHidden(True)
        self.selectImageErrorMsg.setHidden(True)
        self.generateImageButton.setHidden(True)
        self.imagePathInput.setHidden(True)
        self.phantomPathInput.setHidden(True)
        self.selectDataLabel.setHidden(True)
        self.imageFilenameDisplay.setHidden(True)
        self.phantomFilenameDisplay.setHidden(True)
        self.imagePathLabelCanon.setHidden(True)
        self.phantomPathLabelCanon.setHidden(True)
        self.imagePathLabelVerasonics.setHidden(True)
        self.phantomPathLabelVerasonics.setHidden(True)
        self.imagePathLabel.setHidden(True)
        self.phantomPathLabel.setHidden(True)
        self.acceptFrameButton.setHidden(True)
        self.totalFramesLabel.setHidden(True)
        self.ofFramesLabel.setHidden(True)
        self.curFrameSlider.setHidden(True)
        self.curFrameLabel.setHidden(True)
        self.imPreview.setHidden(True)
        self.selectFrameLabel.setHidden(True)

        self.welcomeGui = None
        self.roiSelectionGUI = None
        self.dataFrame = None
        self.machine = None
        self.fileExts = None
        self.frame = 0

        self.terasonButton.clicked.connect(self.terasonClicked)
        self.philipsButton.clicked.connect(self.philipsClicked)
        self.canonButton.clicked.connect(self.canonClicked)
        self.siemensButton.clicked.connect(self.siemensClicked)
        self.verasonicsButton.clicked.connect(self.verasonicsClicked)
        self.chooseImageFileButton.clicked.connect(self.selectImageFile)
        self.choosePhantomFileButton.clicked.connect(self.selectPhantomFile)
        self.clearImagePathButton.clicked.connect(self.clearImagePath)
        self.clearPhantomPathButton.clicked.connect(self.clearPhantomPath)
        self.generateImageButton.clicked.connect(self.moveToRoiSelection)
        self.backButton.clicked.connect(self.backToWelcomeScreen)

    def backToWelcomeScreen(self):
        self.welcomeGui.utc2dIqData = self.dataFrame
        self.welcomeGui.show()
        self.hide()

    def moveToRoiSelection(self):
        if self.machine == "Verasonics":
            self.phantomPathInput.setText(self.imagePathInput.text())
        if os.path.exists(self.imagePathInput.text()) and os.path.exists(
            self.phantomPathInput.text()
        ):
            if self.roiSelectionGUI is not None:
                plt.close(self.roiSelectionGUI.figure)
            del self.roiSelectionGUI
            self.roiSelectionGUI = RoiSelectionGUI()
            self.roiSelectionGUI.setFilenameDisplays(
                self.imagePathInput.text().split("/")[-1],
                self.phantomPathInput.text().split("/")[-1],
            )
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
                    self.selectImageErrorMsg.setHidden(False)
                    return
            elif self.machine == "Terason":
                self.roiSelectionGUI.openImageTerason(
                    self.imagePathInput.text(), self.phantomPathInput.text()
                )
            elif self.machine == "Philips":
                self.qIms, self.widthScale, self.depthScale = np.transpose(list(self.roiSelectionGUI.openPhilipsImage(
                    self.imagePathInput.text(), self.phantomPathInput.text()
                )))
                self.widthScale = self.widthScale[0]
                self.depthScale = self.depthScale[0]
                self.numFrames = self.qIms.shape[0]
                self.showFrameSlider()
            elif self.machine == "Siemens":
                self.qIm, self.widthScale, self.depthScale, self.numFrames = self.roiSelectionGUI.openSiemensImage(
                    self.imagePathInput.text(), self.phantomPathInput.text()
                )
                self.showFrameSlider()
                # self.openSiemensImage()
                return
            else:
                print("ERROR: Machine match not found")
                return
            # self.roiSelectionGUI.show()
            self.roiSelectionGUI.dataFrame = self.dataFrame
            self.roiSelectionGUI.lastGui = self
            self.selectImageErrorMsg.setHidden(True)
            # self.hide()

    # def openSiemensImage(self):
    #     imageFilePath = self.imagePathInput.text()
    #     phantomFilePath = self.phantomPathInput.text()

    #     tmpLocation = imageFilePath.split("/")
    #     dataFileName = tmpLocation[-1]
    #     dataFileLocation = imageFilePath[:len(imageFilePath)-len(dataFileName)]
    #     tmpPhantLocation = phantomFilePath.split("/")
    #     phantFileName = tmpPhantLocation[-1]
    #     phantFileLocation = phantomFilePath[:len(phantomFilePath)-len(phantFileName)]


    #     self.imArray, self.imgDataStruct, self.imgInfoStruct, self.refDataStruct, self.refInfoStruct = rfdParser.getImage(dataFileName, dataFileLocation, phantFileName, phantFileLocation)
    #     self.initialImgRf = self.imgDataStruct.rf
    #     self.initialRefRf = self.refDataStruct.rf
    #     self.frame = 0
    #     self.imData = np.array(self.imArray[self.frame]).reshape(self.imArray.shape[1], self.imArray.shape[2])
    #     self.imData = np.require(self.imData,np.uint8,'C')
    #     self.bytesLine = self.imData.strides[0]
    #     self.arHeight = self.imData.shape[0]
    #     self.arWidth = self.imData.shape[1]
    #     self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8)

    #     quotient = self.imgInfoStruct.width / self.imgInfoStruct.depth
    #     if quotient > (721/501):
    #         self.widthScale = 721
    #         self.depthScale = self.widthScale / (self.imgInfoStruct.width/self.imgInfoStruct.depth)
    #     else:
    #         self.widthScale = 501 * quotient
    #         self.depthScale = 501
    #     self.yBorderMin = 110 + ((501 - self.depthScale)/2)
    #     self.yBorderMax = 611 - ((501 - self.depthScale)/2)
    #     self.xBorderMin = 410 + ((721 - self.widthScale)/2)
    #     self.xBorderMax = 1131 - ((721 - self.widthScale)/2)

    def showFrameSlider(self):
        self.imPreview.setPixmap(QPixmap.fromImage(self.qIms[0]).scaled(self.widthScale, self.depthScale))

        self.totalFramesLabel.setHidden(False)
        self.ofFramesLabel.setHidden(False)
        self.curFrameSlider.setHidden(False)
        self.curFrameLabel.setHidden(False)
        self.imPreview.setHidden(False)
        self.selectFrameLabel.setHidden(False)
        self.imagePathInput.setHidden(True)
        self.phantomPathInput.setHidden(True)
        self.clearImagePathButton.setHidden(True)
        self.clearPhantomPathButton.setHidden(True)
        self.generateImageButton.setHidden(True)
        self.selectImageMethodLabel.setHidden(True)
        self.canonButton.setHidden(True)
        self.verasonicsButton.setHidden(True)
        self.terasonButton.setHidden(True)
        self.philipsButton.setHidden(True)
        self.siemensButton.setHidden(True)
        self.chooseImageFileButton.setHidden(True)
        self.choosePhantomFileButton.setHidden(True)
        self.imagePathLabel.setHidden(True)
        self.phantomPathLabel.setHidden(True)
        self.selectDataLabel.setHidden(True)
        self.acceptFrameButton.setHidden(False)

        self.curFrameSlider.setMinimum(0)
        self.curFrameSlider.setMaximum(self.numFrames-1)
        self.curFrameLabel.setText("0")
        self.totalFramesLabel.setText(str(self.numFrames-1))
        self.curFrameSlider.valueChanged.connect(self.frameChanged)
        self.acceptFrameButton.clicked.connect(self.acceptFrame)

        self.update()    
    
    def frameChanged(self):
        self.frame = self.curFrameSlider.value()
        self.curFrameLabel.setText(str(self.frame))
        self.plotPreviewFrame()

    def acceptFrame(self):
        self.imgDataStruct.bMode = self.imData
        self.imgDataStruct.rf = self.initialImgRf[self.frame]
        self.refDataStruct.rf = self.initialRefRf[0]
        self.roiSelectionGUI.processImage(self.imData, self.imgDataStruct, self.refDataStruct, self.imgInfoStruct, self.refInfoStruct)
        self.roiSelectionGUI.lastGui = self
        self.roiSelectionGUI.show()
        self.hide()

    def plotPreviewFrame(self):
        # self.imData = np.array(self.imArray[self.frame]).reshape(self.imArray.shape[1], self.imArray.shape[2])
        # self.imData = np.require(self.imData,np.uint8,'C')
        # self.qIm = QImage(self.imData, self.arWidth, self.arHeight, self.bytesLine, QImage.Format_Grayscale8)
        self.imPreview.setPixmap(QPixmap.fromImage(self.qIms[self.frame]).scaled(self.widthScale, self.depthScale))
        self.update()

    def clearImagePath(self):
        self.imagePathInput.clear()

    def clearPhantomPath(self):
        self.phantomPathInput.clear()

    def chooseImagePrep(self):
        self.imagePathInput.setHidden(False)
        self.phantomPathInput.setHidden(False)
        self.clearImagePathButton.setHidden(False)
        self.clearPhantomPathButton.setHidden(False)
        self.generateImageButton.setHidden(False)
        self.selectImageMethodLabel.setHidden(True)
        self.canonButton.setHidden(True)
        self.verasonicsButton.setHidden(True)
        self.terasonButton.setHidden(True)
        self.philipsButton.setHidden(True)
        self.siemensButton.setHidden(True)

    def philipsClicked(self):
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabel.setHidden(False)
        self.phantomPathLabel.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.imagePathLabel.setText("Input Path to Image file\n (.rf, .mat)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.rf, .mat)")

        self.machine = "Philips"
        self.fileExts = "*.rf *.mat"

    def terasonClicked(self):
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabel.setHidden(False)
        self.phantomPathLabel.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.imagePathLabel.setText("Input Path to Image file\n (.mat)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.mat)")

        self.machine = "Terason"
        self.fileExts = "*.mat"

    def siemensClicked(self):
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabel.setHidden(False)
        self.phantomPathLabel.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.imagePathLabel.setText("Input Path to Image file\n (.rfd)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.rfd)")

        self.machine = "Siemens"
        self.fileExts = "*.rfd"

    def canonClicked(
        self,
    ):  # Move user to screen to select individual files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabelCanon.setHidden(False)
        self.phantomPathLabelCanon.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.machine = "Canon"
        self.fileExts = "*.bin"

    def verasonicsClicked(
        self,
    ):  # Move user to screen to select individual files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabelVerasonics.setHidden(False)
        self.chooseImageFileButton.setHidden(False)

        self.phantomPathInput.setHidden(True)
        self.clearPhantomPathButton.setHidden(True)

        imagePathLabelPos = self.imagePathLabelCanon.pos()
        imagePathLabelPos.setX(625)
        self.imagePathLabelVerasonics.move(imagePathLabelPos)
        chooseImageFilePos = self.chooseImageFileButton.pos()
        chooseImageFilePos.setX(625)
        self.chooseImageFileButton.move(chooseImageFilePos)
        clearImagePathPos = self.clearImagePathButton.pos()
        clearImagePathPos.setX(765)
        self.clearImagePathButton.move(clearImagePathPos)
        imagePathPos = self.imagePathInput.pos()
        imagePathPos.setX(655)
        self.imagePathInput.move(imagePathPos)

        self.machine = "Verasonics"
        self.fileExts = "*.mat"

    def selectImageFile(self):
        # Create folder to store ROI drawings
        if os.path.exists("Junk"):
            shutil.rmtree("Junk")
        os.mkdir("Junk")

        selectImageHelper(self.imagePathInput, self.fileExts)
        self.selectImageErrorMsg.setHidden(True)

    def selectPhantomFile(self):
        selectImageHelper(self.phantomPathInput, self.fileExts)
        self.selectImageErrorMsg.setHidden(True)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    ui = SelectImageGUI_UtcTool2dIQ()
    ui.show()
    sys.exit(app.exec_())

