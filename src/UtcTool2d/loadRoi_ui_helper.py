import os
import pickle
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QFileDialog
from src.UtcTool2d.loadRoi_ui import Ui_loadRoi
import src.UtcTool2d.roiSelection_ui_helper as RoiSelectionSection

class LoadRoiGUI(Ui_loadRoi, QWidget):
    def __init__(self, imagePath: Path):
        super().__init__()
        self.setupUi(self)
        self.chooseRoiGUI: RoiSelectionSection.RoiSelectionGUI

        self.wrongImageWarning.hide()
        self.startingDirectory = str(imagePath.parent)
        self.chooseFileButton.clicked.connect(self.chooseFile)
        self.clearFileButton.clicked.connect(self.clearFile)
        self.openRoiButton.clicked.connect(self.getRoiPath)
        self.backButton.clicked.connect(self.backToChoice)

    def backToChoice(self):
        self.wrongImageWarning.hide()
        self.hide()
        self.chooseRoiGUI.show()

    def chooseFile(self):
        fileName, _ = QFileDialog.getOpenFileName(None, "Open file", filter="*.pkl", directory=self.startingDirectory)
        if fileName != "":
            self.roiPathInput.setText(fileName)

    def clearFile(self):
        self.roiPathInput.clear()

    def getRoiPath(self):
        if os.path.exists(self.roiPathInput.text()):
            with open(self.roiPathInput.text(), "rb") as f:
                roiInfo = pickle.load(f)

            if (Path(self.chooseRoiGUI.imagePathInput.text()).stem != Path(roiInfo["Image Name"]).stem or 
                self.chooseRoiGUI.phantomPathInput.text() != roiInfo["Phantom Name"]): 
                print("Selected ROI for wrong image")
                self.wrongImageWarning.show()
                return
            
            self.chooseRoiGUI.utcData.splineX = roiInfo["Spline X"]
            self.chooseRoiGUI.utcData.splineY = roiInfo["Spline Y"]
            self.chooseRoiGUI.plotOnCanvas()
            self.chooseRoiGUI.hideInitialButtons()
            self.chooseRoiGUI.showLoadedRoiButtons()

            self.hide()
            self.chooseRoiGUI.show()
