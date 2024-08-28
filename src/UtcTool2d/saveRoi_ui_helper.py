import os
import re
import pickle

from PyQt5.QtWidgets import QWidget, QFileDialog

from src.UtcTool2d.saveRoi_ui import Ui_saveRoi


class SaveRoiGUI(Ui_saveRoi, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.fileNameErrorLabel.setHidden(True)
        self.dataSavedSuccessfullyLabel.setHidden(True)
        self.rfAnalysisGUI = None

        self.chooseFolderButton.clicked.connect(self.chooseFolder)
        self.clearFolderButton.clicked.connect(self.clearFolder)
        self.saveRoiButton.clicked.connect(self.saveRoi)

    def chooseFolder(self):
        folderName = QFileDialog.getExistingDirectory(None, "Select Directory")
        if folderName != "":
            self.newFolderPathInput.setText(folderName)

    def clearFolder(self):
        self.newFolderPathInput.clear()

    def saveRoi(self):
        if os.path.exists(self.newFolderPathInput.text()):
            if not (
                self.newFileNameInput.text().endswith(".pkl")
                and (not bool(re.search(r"\s", self.newFileNameInput.text())))
            ):
                self.fileNameWarningLabel.setHidden(True)
                self.fileNameErrorLabel.setHidden(False)
                return
            with open(
                os.path.join(
                    self.newFolderPathInput.text(), self.newFileNameInput.text()
                ),
                mode="wb",
            ) as pklfile:
                pickle.dump(self.rfAnalysisGUI.AnalysisInfo, pklfile, protocol=pickle.HIGHEST_PROTOCOL)
              
            self.dataSavedSuccessfullyLabel.setHidden(False)
            self.newFileNameInput.setHidden(True)
            self.newFileNameLabel.setHidden(True)
            self.newFolderPathInput.setHidden(True)
            self.saveRoiLabel.setHidden(True)
            self.newFileNameLabel.setHidden(True)
            self.fileNameErrorLabel.setHidden(True)
            self.roiFolderPathLabel.setHidden(True)
            self.fileNameWarningLabel.setHidden(True)
            self.saveRoiButton.setHidden(True)
            self.clearFolderButton.setHidden(True)
            self.chooseFolderButton.setHidden(True)
