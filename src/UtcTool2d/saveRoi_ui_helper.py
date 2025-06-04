from hmac import new
import os
from pathlib import Path
import re
import pickle
from typing import List

import numpy as np
from PyQt6.QtWidgets import QWidget, QFileDialog

from src.UtcTool2d.saveRoi_ui import Ui_saveRoi


class SaveRoiGUI(Ui_saveRoi, QWidget):
    def __init__(self, imagePath: Path):
        super().__init__()
        self.setupUi(self)
        self.dataSavedSuccessfullyLabel.setHidden(True)
        
        self.imName: str
        self.phantomName: str
        self.splineX: np.ndarray
        self.splineY: np.ndarray
        self.frame: int
        self.startingDirectory = str(imagePath.parent)
        
        startingRoiName = imagePath.stem
        self.newFileNameInput.setText(startingRoiName)
        self.newFolderPathInput.setText(self.startingDirectory)
        self.chooseFolderButton.clicked.connect(self.chooseFolder)
        self.clearFolderButton.clicked.connect(self.clearFolder)
        self.saveRoiButton.clicked.connect(self.saveRoi)

    def chooseFolder(self):
        folderName = QFileDialog.getExistingDirectory(None, "Select Directory", directory=self.startingDirectory)
        if folderName != "":
            self.newFolderPathInput.setText(folderName)

    def clearFolder(self):
        self.newFolderPathInput.clear()

    def saveRoi(self):
        if os.path.exists(self.newFolderPathInput.text()):
            newFileName = self.newFileNameInput.text() + '.pkl'
            output = {"Image Name": self.imName, "Phantom Name": self.phantomName,
                      "Spline X": self.splineX, "Spline Y": self.splineY,
                      "Frame": self.frame}
            
            with open(os.path.join(
                    self.newFolderPathInput.text(), newFileName
                ),mode="wb") as pklfile:
                pickle.dump(output, pklfile, protocol=pickle.HIGHEST_PROTOCOL)
              
            self.dataSavedSuccessfullyLabel.setHidden(False)
            self.newFileNameInput.setHidden(True)
            self.newFileNameLabel.setHidden(True)
            self.newFolderPathInput.setHidden(True)
            self.saveRoiLabel.setHidden(True)
            self.newFileNameLabel.setHidden(True)
            self.roiFolderPathLabel.setHidden(True)
            self.fileNameWarningLabel.setHidden(True)
            self.saveRoiButton.setHidden(True)
            self.clearFolderButton.setHidden(True)
            self.chooseFolderButton.setHidden(True)
