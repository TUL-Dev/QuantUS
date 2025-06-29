import os
import re

from PyQt6.QtWidgets import QWidget, QFileDialog

from src.UtcTool3d.saveVoi_ui import Ui_saveVoi

class SaveVoiGUI(Ui_saveVoi, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.fileNameErrorLabel.setHidden(True)
        self.dataSavedSuccessfullyLabel.setHidden(True)
        self.voiSelectionGUI = None

        self.chooseFolderButton.clicked.connect(self.chooseFolder)
        self.clearFolderButton.clicked.connect(self.clearFolder)
        self.saveVoiButton.clicked.connect(self.saveVoi)

    def chooseFolder(self):
        folderName = QFileDialog.getExistingDirectory(None, "Select Directory")
        if folderName != "":
            self.newFolderPathInput.setText(folderName)

    def clearFolder(self):
        self.newFolderPathInput.clear()

    def saveVoi(self):
        if os.path.exists(self.newFolderPathInput.text()):
            if not (
                self.newFileNameInput.text().endswith(".nii.gz")
                and (not bool(re.search(r"\s", self.newFileNameInput.text())))
            ):
                self.fileNameWarningLabel.setHidden(True)
                self.fileNameErrorLabel.setHidden(False)
                return
            self.voiSelectionGUI.saveVoi(
                self.newFolderPathInput.text(),
                self.newFileNameInput.text(),
                self.voiSelectionGUI.curSliceIndex,
            )
            self.dataSavedSuccessfullyLabel.setHidden(False)
            self.newFileNameInput.setHidden(True)
            self.newFileNameLabel.setHidden(True)
            self.newFolderPathInput.setHidden(True)
            self.saveVoiLabel.setHidden(True)
            self.newFileNameLabel.setHidden(True)
            self.fileNameErrorLabel.setHidden(True)
            self.voiFolderPathLabel.setHidden(True)
            self.fileNameWarningLabel.setHidden(True)
            self.saveVoiButton.setHidden(True)
            self.clearFolderButton.setHidden(True)
            self.chooseFolderButton.setHidden(True)
