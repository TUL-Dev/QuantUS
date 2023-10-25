from UtcTool2d.editImageDisplay_ui import *
from PyQt5.QtWidgets import QWidget, QApplication

class EditImageDisplayGUI(Ui_editBmode, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.contrastValDisplay.setTextVisible(False)
        self.brightnessValDisplay.setTextVisible(False)
        self.sharpnessValDisplay.setTextVisible(False)
    