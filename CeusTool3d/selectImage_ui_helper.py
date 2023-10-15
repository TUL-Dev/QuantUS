from CeusTool3d.selectImage_ui import *
from CeusTool3d.voiSelection_ui_helper import *

import os
import shutil
import Utils.utils as ut

from PyQt5.QtWidgets import QWidget, QApplication

import platform
system = platform.system()

def selectImageHelper(pathInput):
    if not os.path.exists(pathInput.text()): # check if file path is manually typed
        # NOTE: .bin is currently not supported
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = '*.rf *.mat')
        if fileName != '': # If valid file is chosen
            pathInput.setText(fileName)
        else:
            return


class SelectImageGUI_CeusTool3d(Ui_selectImage, QWidget):
    def __init__(self):
        # self.selectImage = QWidget()
        super().__init__()
        self.setupUi(self)

        if system == 'Windows':
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
            self.imageFilenameDisplay.setStyleSheet("""QLabel {
                font-size: 11px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
            }""")
            self.roiSidebarLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }""")
            self.analysisParamsLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight:bold;
            }""")
            self.ticAnalysisLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }""")
            self.rfAnalysisLabel.setStyleSheet("""QLabel {
                font-size: 18px;
                color: rgb(255, 255, 255);
                background-color: rgba(255, 255, 255, 0);
                border: 0px;
                font-weight: bold;
            }""")

        self.xmlImagePathInput.setHidden(True)
        self.imageFilenameDisplay.setHidden(True)
        self.niftiImagePathInput.setHidden(True)
        self.niftiImageDestinationButton.setHidden(True)
        self.niftiImageDestinationPath.setHidden(True)
        self.clearNiftiImageDestinationButton.setHidden(True)
        self.clearNiftiImageFileButton.setHidden(True)
        self.clearXmlImageFolderButton.setHidden(True)
        self.chooseXmlImageFolderButton.setHidden(True)
        self.chooseNiftiImageFileButton.setHidden(True)
        self.imageBackButton.setHidden(True)
        self.selectImageErrorMsg.setHidden(True)
        self.selectNiftiImageLabel.setHidden(True)
        self.selectXmlFolderImageLabel.setHidden(True)
        self.niftiDestinationImageLabel.setHidden(True)

        self.imageNifti = 0

        self.voiSelectionGui = None
        self.welcomeGui = None
        self.dataFrame = None

        self.selectNiftiImageOptionButton.clicked.connect(self.selectNiftiImageOption)
        self.selectXmlFolderImageOptionButton.clicked.connect(self.selectXmlImageOption)
        self.generateImageButton.clicked.connect(self.moveToVoiSelection)
        self.chooseXmlImageFolderButton.clicked.connect(self.getXmlImageDestinationPath)
        self.chooseNiftiImageFileButton.clicked.connect(self.getNiftiImagePath)
        self.niftiImageDestinationButton.clicked.connect(self.getNiftiImageDestinationPath)
        self.clearNiftiImageFileButton.clicked.connect(self.clearNiftiImagePath)
        self.clearNiftiImageDestinationButton.clicked.connect(self.clearNiftiImageDestinationPath)
        self.clearXmlImageFolderButton.clicked.connect(self.clearXmlImageDestinationPath)
        self.backButton.clicked.connect(self.backToWelcomeScreen)

    def backToWelcomeScreen(self):
        self.welcomeGui.ceus3dData = self.dataFrame
        self.welcomeGui.show()
        self.hide()

    def getNiftiImagePath(self):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = '*.nii *.nii.gz')
        if fileName != '':
            self.niftiImagePathInput.setText(fileName)

    def clearNiftiImagePath(self):
        self.niftiImagePathInput.setText('')

    def getNiftiImageDestinationPath(self):
        fileName = QFileDialog.getExistingDirectory(None, 'Select Directory')
        if fileName != '':
            self.niftiImageDestinationPath.setText(fileName)

    def clearNiftiImageDestinationPath(self):
        self.niftiImageDestinationPath.setText('')

    def getXmlImageDestinationPath(self):
        fileName = QFileDialog.getExistingDirectory(None, 'Select Directory')
        if fileName != '':
            self.xmlImagePathInput.setText(fileName)

    def clearXmlImageDestinationPath(self):
        self.xmlImagePathInput.setText('')
        

    def backFromNiftiImage(self):
        self.selectNiftiImageOptionButton.setHidden(False)
        self.selectXmlFolderImageOptionButton.setHidden(False)

        self.selectNiftiImageLabel.setHidden(True)
        self.chooseNiftiImageFileButton.setHidden(True)
        self.clearNiftiImageFileButton.setHidden(True)
        self.niftiImagePathInput.setHidden(True)
        self.imageBackButton.setHidden(True)

        self.imageBackButton.clicked.disconnect()

        self.imageNifti = 0

    def backFromXmlImage(self):
        self.selectNiftiImageOptionButton.setHidden(False)
        self.selectXmlFolderImageOptionButton.setHidden(False)

        self.chooseXmlImageFolderButton.setHidden(True)
        self.clearXmlImageFolderButton.setHidden(True)
        self.xmlImagePathInput.setHidden(True)
        self.niftiImageDestinationButton.setHidden(True)
        self.clearNiftiImageDestinationButton.setHidden(True)
        self.niftiImageDestinationPath.setHidden(True)
        self.imageBackButton.setHidden(True)
        self.selectXmlFolderImageLabel.setHidden(True)
        self.niftiDestinationImageLabel.setHidden(True)

        self.imageBackButton.clicked.disconnect()

        self.imageNifti = 0
    
    def selectNiftiImageOption(self):
        self.selectNiftiImageOptionButton.setHidden(True)
        self.selectXmlFolderImageOptionButton.setHidden(True)

        self.selectNiftiImageLabel.setHidden(False)
        self.chooseNiftiImageFileButton.setHidden(False)
        self.clearNiftiImageFileButton.setHidden(False)
        self.niftiImagePathInput.setHidden(False)
        self.imageBackButton.setHidden(False)

        self.imageBackButton.clicked.connect(self.backFromNiftiImage)

        self.imageNifti = 1 # NIFTI image already exists

    def selectXmlImageOption(self):
        self.selectNiftiImageOptionButton.setHidden(True)
        self.selectXmlFolderImageOptionButton.setHidden(True)

        self.chooseXmlImageFolderButton.setHidden(False)
        self.clearXmlImageFolderButton.setHidden(False)
        self.xmlImagePathInput.setHidden(False)
        self.niftiImageDestinationButton.setHidden(False)
        self.clearNiftiImageDestinationButton.setHidden(False)
        self.niftiImageDestinationPath.setHidden(False)
        self.imageBackButton.setHidden(False)
        self.selectXmlFolderImageLabel.setHidden(False)
        self.niftiDestinationImageLabel.setHidden(False)

        self.imageBackButton.clicked.connect(self.backFromXmlImage)

        self.imageNifti = 2 # NIFTI image doesn't exist yet


    def moveToVoiSelection(self):
        if self.imageNifti:
            imagePath = ""
            if self.imageNifti == 1 and os.path.exists(self.niftiImagePathInput.text()):
                imagePath = self.niftiImagePathInput.text()
            if self.imageNifti == 2 and os.path.exists(self.niftiImageDestinationPath.text()) and os.path.isdir(self.niftiImageDestinationPath.text()) and os.path.exists(self.xmlImagePathInput.text()):
                imagePath = ut.xml2nifti(self.xmlImagePathInput.text(), self.niftiImageDestinationPath.text())
            if imagePath != "":
                del self.voiSelectionGui
                self.voiSelectionGui = VoiSelectionGUI()
                self.voiSelectionGui.dataFrame = self.dataFrame
                self.voiSelectionGui.setFilenameDisplays(imagePath)
                self.voiSelectionGui.openImage()
                self.voiSelectionGui.lastGui = self
                self.voiSelectionGui.show()
                self.hide()
            else:
                return
        
    def clearImagePath(self):
        self.imagePathInput.clear()

    def clearPhantomPath(self):
        self.phantomPathInput.clear()

    def chooseImagePrep(self):
        self.selectFoldersButton.setHidden(True)
        self.selectIndFilesButton.setHidden(True)
        self.imagePathInput.setHidden(False)
        self.phantomPathInput.setHidden(False)
        self.clearImagePathButton.setHidden(False)
        self.clearPhantomPathButton.setHidden(False)
        self.generateImageButton.setHidden(False)
        self.selectImageMethodLabel.setHidden(True)

    def fileOptionSelected(self): # Move user to screen to select individual files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.imagePathLabel.setHidden(False)
        self.phantomPathLabel.setHidden(False)
        self.chooseImageFileButton.setHidden(False)
        self.choosePhantomFileButton.setHidden(False)

        self.choosingIndividualFiles = True

    def folderOptionSelected(self): 
        # Move user to screen to select folders to find compatible files to generate image
        self.chooseImagePrep()
        self.selectDataLabel.setHidden(False)
        self.chooseImageFolderButton.setHidden(False)
        self.choosePhantomFolderButton.setHidden(False)
        self.imagePathFolderLabel.setHidden(False)
        self.phantomPathFolderLabel.setHidden(False)

        self.validPairs = []

    def selectImageFile(self):
        if not self.choosingIndividualFiles:
            return

        # Create folder to store ROI drawings
        if os.path.exists("imROIs"):
            shutil.rmtree("imROIs")
        os.mkdir("imROIs")

        selectImageHelper(self.imagePathInput)

    def selectPhantomFile(self):
        if not self.choosingIndividualFiles:
            return
        selectImageHelper(self.phantomPathInput)




if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = SelectImageGUI_CeusTool3d()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())