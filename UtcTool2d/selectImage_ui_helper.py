from UtcTool2d.selectImage_ui import *
from UtcTool2d.roiSelection_ui_helper import *
import os
import shutil
from PyQt5.QtWidgets import QWidget, QApplication, QFileDialog

import platform
system = platform.system()


class SelectImageGUI_UtcTool2d(Ui_selectImage, QWidget):
    def __init__(self):
        # self.selectImage = QWidget()
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
        self.clearImagePathButton.setHidden(True)
        self.clearPhantomPathButton.setHidden(True)
        self.selectImageErrorMsg.setHidden(True)
        self.generateImageButton.setHidden(True)
        self.imagePathInput.setHidden(True)
        self.phantomPathInput.setHidden(True)
        self.imagePathLabel.setHidden(True)
        self.phantomPathLabel.setHidden(True)
        self.selectDataLabel.setHidden(True)
        self.imageFilenameDisplay.setHidden(True)
        self.phantomFilenameDisplay.setHidden(True)

        self.welcomeGui = None
        self.roiSelectionGUI = None
        self.dataFrame = None
        self.selectedMachine = None
        self.selectFileFilter = None
        
        self.philipsButton.clicked.connect(self.philipsSelected)
        self.siemensButton.clicked.connect(self.siemensSelected)
        self.terasonButton.clicked.connect(self.terasonSelected)
        self.chooseImageFileButton.clicked.connect(self.selectImageFile)
        self.choosePhantomFileButton.clicked.connect(self.selectPhantomFile)
        self.clearImagePathButton.clicked.connect(self.clearImagePath)
        self.clearPhantomPathButton.clicked.connect(self.clearPhantomPath)
        self.generateImageButton.clicked.connect(self.moveToRoiSelection)
        self.backButton.clicked.connect(self.backToWelcomeScreen)

    def philipsSelected(self):
        self.selectedMachine = "Philips"
        self.selectFileFilter = "*.rf *.mat"
        self.imagePathLabel.setText("Input Path to Image file\n (.rf,  .mat)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.rf,  .mat)")
        self.fileOptionSelected()

    def siemensSelected(self):
        self.selectedMachine = "Siemens"
        self.selectFileFilter = "*.rfd"
        self.imagePathLabel.setText("Input Path to Image file\n (.rfd)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.rfd)")
        self.fileOptionSelected()

    def terasonSelected(self):
        self.selectedMachine = "Terason"
        self.selectFileFilter = "*.mat"
        self.imagePathLabel.setText("Input Path to Image file\n (.mat)")
        self.phantomPathLabel.setText("Input Path to Phantom file\n (.mat)")
        self.fileOptionSelected()

    def backToWelcomeScreen(self):
        self.welcomeGui.utc2dRfData = self.dataFrame
        self.welcomeGui.show()
        self.hide()

    def moveToRoiSelection(self):
        if os.path.exists(self.imagePathInput.text()) and os.path.exists(self.phantomPathInput.text()) and self.selectedMachine != None:
            if self.imagePathInput.text().endswith('.rfd') and self.phantomPathInput.text().endswith('.rfd'):
                imageName = self.imagePathInput.text().split('/')[-1]
                phantomName = self.phantomPathInput.text().split('/')[-1]
                vIm = imageName.split("SpV")[1]
                vIm = vIm.split("_")[0]
                fIm = imageName.split("VpF")[1]
                fIm = fIm.split("_")[0]
                aIm = imageName.split("FpA")[1]
                aIm = aIm.split("_")[0]
                vPhant = phantomName.split("SpV")[1]
                vPhant = vPhant.split("_")[0]
                fPhant = phantomName.split("VpF")[1]
                fPhant = fPhant.split("_")[0]
                aPhant = phantomName.split("FpA")[1]
                aPhant = aPhant.split("_")[0]
                
                if aPhant < aIm or vPhant < vIm or fPhant < fPhant:
                    self.selectImageErrorMsg.setHidden(False)
                    return

    
            del self.roiSelectionGUI
            self.roiSelectionGUI = RoiSelectionGUI()
            self.roiSelectionGUI.setFilenameDisplays(self.imagePathInput.text().split('/')[-1], self.phantomPathInput.text().split('/')[-1])
            if self.selectedMachine == "Philips":
                self.roiSelectionGUI.openPhilipsImage(self.imagePathInput.text(), self.phantomPathInput.text())
            elif self.selectedMachine == "Siemens":
                self.roiSelectionGUI.openSiemensImage(self.imagePathInput.text(), self.phantomPathInput.text())
            elif self.selectedMachine == "Terason":
                self.roiSelectionGUI.openTerasonImage(self.imagePathInput.text(), self.phantomPathInput.text())
            else:
                print("ERROR: Machine not selected properly")
                return
            self.roiSelectionGUI.show()
            self.roiSelectionGUI.lastGui = self
            self.roiSelectionGUI.dataFrame = self.dataFrame
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
        self.philipsButton.setHidden(True)
        self.siemensButton.setHidden(True)
        self.terasonButton.setHidden(True)
        self.transducerBrandLabel.setHidden(True)

    def fileOptionSelected(self): # Move user to screen to select individual files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabel.setHidden(False)
        self.phantomPathLabel.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

    def selectImageFile(self):
        # Create folder to store ROI drawings
        if os.path.exists("Junk"):
            shutil.rmtree("Junk")
        os.mkdir("Junk")

        self.selectImageHelper(self.imagePathInput)
        self.selectImageErrorMsg.setHidden(True)

    def selectPhantomFile(self):
        self.selectImageHelper(self.phantomPathInput)
        self.selectImageErrorMsg.setHidden(True)

    def selectImageHelper(self, pathInput):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = self.selectFileFilter)
        if fileName != '': # If valid file is chosen
            pathInput.setText(fileName)
        else:
            return




if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = SelectImageGUI_UtcTool2d()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())