import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication, QWidget

from src.CeusTool3d.selectImage_ui_helper import SelectImageGUI_CeusTool3d
from src.CeusMcTool2d.selectImage_ui_helper import SelectImageGUI_CeusMcTool2d
from src.UtcTool3d.selectImage_ui_helper import SelectImageGUI_UtcTool3d
from src.UtcTool2d.selectImage_ui_helper import SelectImageGUI_UtcTool2dIQ
from welcome_ui import Ui_WelcomePage


class WelcomeGui(Ui_WelcomePage, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.utc2dButton.clicked.connect(self.moveToUtc2d)
        self.utc3dButton.clicked.connect(self.moveToUtc3d)
        self.dceus3dButton.clicked.connect(self.moveToDceus3d)
        self.dceus2dButton.clicked.connect(self.moveToDceusMc2d)
        self.nextPage = None
        self.setLayout(self.verticalLayout)
        self.ceus2dMcData = pd.DataFrame(
            columns=[
                "Patient",
                "Area Under Curve (AUC)",
                "Peak Enhancement (PE)",
                "Time to Peak (TP)",
                "Mean Transit Time (MTT)",
                "TMPPV",
                "ROI Area (mm^2)",
                "TIC y vals",
                "TIC t vals",
                "Lognorm y vals"
            ]
        )

    def moveToUtc2d(self):
        del self.nextPage
        self.nextPage = SelectImageGUI_UtcTool2dIQ()
        self.nextPage.show()
        self.nextPage.resize(self.size())
        self.nextPage.welcomeGui = self
        self.hide()

    def moveToUtc3d(self):
        del self.nextPage
        self.nextPage = SelectImageGUI_UtcTool3d()
        self.nextPage.show()
        self.nextPage.resize(self.size())
        self.nextPage.welcomeGui = self
        self.hide()

    def moveToDceus3d(self):
        del self.nextPage
        self.nextPage = SelectImageGUI_CeusTool3d()
        self.nextPage.show()
        self.nextPage.resize(self.size())
        self.nextPage.welcomeGui = self
        self.hide()

    def moveToDceusMc2d(self):
        del self.nextPage
        self.nextPage = SelectImageGUI_CeusMcTool2d()
        self.nextPage.dataFrame = self.ceus2dMcData
        self.nextPage.show()
        self.nextPage.welcomeGui = self
        self.hide()


# -----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    welcomeApp = QApplication(sys.argv)
    welcomeUI = WelcomeGui()
    welcomeUI.show()
    sys.exit(welcomeApp.exec())
