from UtcTool2d.loadRoi_ui import *
import os
import csv
from PyQt5.QtWidgets import QWidget, QApplication, QFileDialog

class LoadRoiGUI(Ui_loadRoi, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.chooseRoiGUI = None

        self.chooseFileButton.clicked.connect(self.chooseFile)
        self.clearFileButton.clicked.connect(self.clearFile)
        self.openRoiButton.clicked.connect(self.getRoiPath)
        self.backButton.clicked.connect(self.backToChoice)

    def backToChoice(self):
        self.hide()
        self.chooseRoiGUI.show()

    def chooseFile(self):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open file', filter = '*.csv')
        if fileName != '':
            self.roiPathInput.setText(fileName)

    def clearFile(self):
        self.roiPathInput.clear()

    def getRoiPath(self):
        if os.path.exists(self.roiPathInput.text()):
            imageName = ''
            with open(self.roiPathInput.text(), mode='r') as csvfile:
                reader = csv.reader(csvfile)
                line_count = 0
                for row in reader:
                    if line_count == 1:
                        imageName = row[0]
                        self.chooseRoiGUI.curPointsPlottedX = row[1][1:-1].split(',')
                        self.chooseRoiGUI.curPointsPlottedX = [int(num) for num in self.chooseRoiGUI.curPointsPlottedX]
                        self.chooseRoiGUI.curPointsPlottedY = row[2][1:-1].split(',')
                        self.chooseRoiGUI.curPointsPlottedY = [int(num) for num in self.chooseRoiGUI.curPointsPlottedY]
                        try:
                            self.chooseRoiGUI.frame = int(row[3])
                            self.chooseRoiGUI.curFrameSlider.setValue(self.chooseRoiGUI.frame)
                            self.chooseRoiGUI.curFrameChanged()
                        except:
                            self.chooseRoiGUI.frame = None
                        break
                    line_count += 1
            if imageName != self.chooseRoiGUI.imagePathInput.text():
                self.chooseRoiGUI.curPointsPlottedX = []
                self.chooseRoiGUI.curPointsPlottedY = []
                print("Selected ROI for wrong image")
                return
            self.chooseRoiGUI.closeInterpolation()
            self.chooseRoiGUI.acceptLoadedRoiButton.setHidden(False)
            self.chooseRoiGUI.undoLoadedRoiButton.setHidden(False)
            self.chooseRoiGUI.newRoiButton.setHidden(True)
            self.chooseRoiGUI.loadRoiButton.setHidden(True)
            self.chooseRoiGUI.drawRoiButton.setChecked(True)
            self.chooseRoiGUI.drawRoiButton.setCheckable(True)
            self.chooseRoiGUI.redrawRoiButton.setHidden(True)
            self.hide()
            self.chooseRoiGUI.show()