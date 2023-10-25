from UtcTool2dIQ.selectImage_ui import *
from UtcTool2dIQ.roiSelection_ui_helper import *
import os
import shutil

from PyQt5.QtWidgets import QWidget, QApplication
import platform

system = platform.system()

def selectImageHelper(pathInput, fileExts):
    if not os.path.exists(pathInput.text()): # check if file path is manually typed
        # NOTE: .bin is currently not supported
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = fileExts)
        if fileName != '': # If valid file is chosen
            pathInput.setText(fileName)
        else:
            return


class SelectImageGUI_UtcTool2dIQ(Ui_selectImage, QWidget):
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
            self.imageFilenameDisplay.setStyleSheet("""QLabel {
                font-size: 11px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
            }""")
            self.phantomFilenameDisplay.setStyleSheet("""QLabel {
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

        self.welcomeGui = None
        self.roiSelectionGUI = None
        self.dataFrame = None
        self.machine = None
        self.fileExts = None
        
        self.canonButton.clicked.connect(self.canonClicked)
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
        if os.path.exists(self.imagePathInput.text()) and os.path.exists(self.phantomPathInput.text()):
            # if self.imagePathInput.text().endswith('.rfd') and self.phantomPathInput.text().endswith('.rfd'):
            #     imageName = self.imagePathInput.text().split('/')[-1]
            #     phantomName = self.phantomPathInput.text().split('/')[-1]
            #     vIm = imageName.split("SpV")[1]
            #     vIm = vIm.split("_")[0]
            #     fIm = imageName.split("VpF")[1]
            #     fIm = fIm.split("_")[0]
            #     aIm = imageName.split("FpA")[1]
            #     aIm = aIm.split("_")[0]
            #     vPhant = phantomName.split("SpV")[1]
            #     vPhant = vPhant.split("_")[0]
            #     fPhant = phantomName.split("VpF")[1]
            #     fPhant = fPhant.split("_")[0]
            #     aPhant = phantomName.split("FpA")[1]
            #     aPhant = aPhant.split("_")[0]
                
            #     if aPhant < aIm or vPhant < vIm or fPhant < fPhant:
            #         self.selectImageErrorMsg.setHidden(False)
            #         return

            if self.roiSelectionGUI != None:
                plt.close(self.roiSelectionGUI.figure)
            del self.roiSelectionGUI
            self.roiSelectionGUI = RoiSelectionGUI()
            self.roiSelectionGUI.setFilenameDisplays(self.imagePathInput.text().split('/')[-1], self.phantomPathInput.text().split('/')[-1])
            if self.machine == "Verasonics":
                self.roiSelectionGUI.openImageVerasonics(self.imagePathInput.text(), self.phantomPathInput.text())
            elif self.machine == "Canon":
                self.roiSelectionGUI.openImageCanon(self.imagePathInput.text(), self.phantomPathInput.text())
            else:
                print("ERROR: Machine match not found")
                return
            self.roiSelectionGUI.show()
            self.roiSelectionGUI.machine = self.machine
            self.roiSelectionGUI.dataFrame = self.dataFrame
            self.roiSelectionGUI.lastGui = self
            self.hide()
        
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

    def canonClicked(self): # Move user to screen to select individual files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabelCanon.setHidden(False)
        self.phantomPathLabelCanon.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.machine = 'Canon'
        self.fileExts = '*.bin'

    def verasonicsClicked(self): # Move user to screen to select individual files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabelVerasonics.setHidden(False)
        self.phantomPathLabelVerasonics.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.machine = 'Verasonics'
        self.fileExts = '*.mat'

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