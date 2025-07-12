
import os
from pathlib import Path

import pandas as pd
from PyQt6.QtWidgets import QWidget, QApplication, QHeaderView, QTableWidgetItem, QFileDialog
from PyQt6.QtCore import Qt

from src.CeusMcTool2d.selectImage_ui import Ui_selectImage
from src.CeusMcTool2d.roiSelection_ui_helper import RoiSelectionGUI


class SelectImageGUI_CeusMcTool2d(Ui_selectImage, QWidget):
    def __init__(self):
        # self.selectImage = QWidget()
        super().__init__()
        self.setupUi(self)

        self.imageFilenameDisplay.setHidden(True)
        self.selectImageErrorMsg.setHidden(True)
        self.imagesScrollArea.setHidden(True)
        self.undoSpreadsheetButton.setHidden(True)
        self.generateImageButton.setHidden(True)
        self.selectDataLabel.setHidden(True)
        self.chooseSpreadsheetFileButton.setHidden(True)
        self.clearSpreadsheetFileButton.setHidden(True)
        self.spreadsheetPath.setHidden(True)
        self.selectSpreadsheeetLabel.setHidden(True)
        self.findImagesButton.setHidden(True)
        self.selectNiftiBmodeLabel.setHidden(True)
        self.selectNiftiCeLabel.setHidden(True)
        self.niftiBmodeInput.setHidden(True)
        self.niftiCeInput.setHidden(True)
        self.chooseNiftiBmodeButton.setHidden(True)
        self.chooseNiftiCeButton.setHidden(True)
        self.clearNiftiBmodeButton.setHidden(True)
        self.clearNiftiCeButton.setHidden(True)
        self.aviPath.setHidden(True)
        self.clearAviButton.setHidden(True)
        self.chooseAviButton.setHidden(True)
        self.selectAviLabel.setHidden(True)

        self.format = None

        header = self.imagesScrollArea.horizontalHeader()
        # header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setStyleSheet(
            """
        QHeaderView::section{
            background-color: white;
            font-size: 15px;
            color: black;
        }"""
        )
        self.imagesScrollArea.verticalHeader().setStyleSheet(
            """
        QHeaderView::section{
            background-color: white;
            font-size: 15px;
            color: black;
        }
        QHeaderView::section::selected{
            background-color: pink;
            font-size: 14px;
            color: black
            font-weight: bold;
        }"""
        )

        self.imageNifti = 0

        self.roiSelectionGui = None
        self.welcomeGui = None

        self.generateImageButton.clicked.connect(self.moveToRoiSelection)
        self.chooseSpreadsheetFileButton.clicked.connect(self.getSpreadsheetPath)
        self.clearSpreadsheetFileButton.clicked.connect(self.clearSpreadsheetPath)
        self.backButton.clicked.connect(self.backToWelcomeScreen)
        self.undoSpreadsheetButton.clicked.connect(self.undoSpreadsheetEntry)
        self.niftiButton.clicked.connect(self.niftiSelected)
        self.dicomExcelButton.clicked.connect(self.dicomExcelSelected)
        self.dicomDirectButton.clicked.connect(self.dicomDirectSelected)
        self.aviButton.clicked.connect(self.aviSelected)
        self.clearAviButton.clicked.connect(self.aviPath.clear)
        self.visualsonicsXmlButton.clicked.connect(self.visualsonicsXmlSelected)

    def moveToFileChoice(self):
        self.selectFormatLabel.setHidden(True)
        self.niftiButton.setHidden(True)
        self.dicomExcelButton.setHidden(True)
        self.aviButton.setHidden(True)
        self.dicomDirectButton.setHidden(True)
        self.visualsonicsXmlButton.setHidden(True)

        self.selectDataLabel.setHidden(False)
        self.findImagesButton.setHidden(False)

    def niftiSelected(self):
        self.moveToFileChoice()
        self.selectNiftiBmodeLabel.setHidden(False)
        self.selectNiftiCeLabel.setHidden(False)
        self.niftiBmodeInput.setHidden(False)
        self.niftiCeInput.setHidden(False)
        self.chooseNiftiBmodeButton.setHidden(False)
        self.chooseNiftiCeButton.setHidden(False)
        self.clearNiftiBmodeButton.setHidden(False)
        self.clearNiftiCeButton.setHidden(False)

        self.format = "Nifti"

        self.chooseNiftiBmodeButton.clicked.connect(self.getNiftiBmodePath)
        self.chooseNiftiCeButton.clicked.connect(self.getNiftiCePath)
        self.clearNiftiBmodeButton.clicked.connect(self.niftiBmodeInput.clear)
        self.clearNiftiCeButton.clicked.connect(self.niftiCeInput.clear)
        self.findImagesButton.clicked.connect(self.moveToRoiSelection)

    def aviSelected(self):
        self.moveToFileChoice()
        self.aviPath.setHidden(False)
        self.clearAviButton.setHidden(False)
        self.chooseAviButton.setHidden(False)
        self.selectAviLabel.setHidden(False)
        self.findImagesButton.setText("Open Image")

        self.format = "Avi"

        self.chooseAviButton.clicked.connect(self.getAviPath)
        self.clearNiftiBmodeButton.clicked.connect(self.aviPath.clear)
        self.findImagesButton.clicked.connect(self.moveToRoiSelection)

    def dicomExcelSelected(self):
        self.moveToFileChoice()
        self.chooseSpreadsheetFileButton.setHidden(False)
        self.clearSpreadsheetFileButton.setHidden(False)
        self.spreadsheetPath.setHidden(False)
        self.selectSpreadsheeetLabel.setHidden(False)

        self.format = "DicomExcel"
        self.findImagesButton.clicked.connect(self.listImages)
        
    def visualsonicsXmlSelected(self):
        self.moveToFileChoice()
        self.aviPath.setHidden(False)
        self.clearAviButton.setHidden(False)
        self.chooseAviButton.setHidden(False)
        self.selectAviLabel.setHidden(False)
        self.findImagesButton.setText("Open Image")
        self.selectAviLabel.setText("Select Visualsonics XML File (.xml)")
        
        self.format = "VisualsonicsXml"
        self.chooseAviButton.clicked.connect(self.getXmlPath)
        self.clearAviButton.clicked.connect(self.aviPath.clear)
        self.findImagesButton.clicked.connect(self.moveToRoiSelection)

    def dicomDirectSelected(self):
        self.moveToFileChoice()
        self.chooseSpreadsheetFileButton.setHidden(False)
        self.clearSpreadsheetFileButton.setHidden(False)
        self.spreadsheetPath.setHidden(False)
        self.selectSpreadsheeetLabel.setHidden(False)
        self.selectSpreadsheeetLabel.setText("Select DICOM Image")

        self.format = "DicomDirect"
        self.findImagesButton.clicked.connect(self.moveToRoiSelection)

    def undoSpreadsheetEntry(self):
        self.imagesScrollArea.clearContents()
        self.imagesScrollArea.setHidden(True)
        self.spreadsheetPath.clear()
        self.spreadsheetPath.setHidden(False)
        self.chooseSpreadsheetFileButton.setHidden(False)
        self.clearSpreadsheetFileButton.setHidden(False)
        self.findImagesButton.setHidden(False)
        self.generateImageButton.setHidden(True)
        self.undoSpreadsheetButton.setHidden(True)
        self.selectSpreadsheeetLabel.setHidden(False)

    def listImages(self):
        if len(self.spreadsheetPath.text()):
            # wb = openpyxl.load_workbook(self.spreadsheetPath.text())
            # ws = wb.get_sheet_by_name('Sheet1')

            # hiddenCols = []
            # for colLetter, colDimension in ws.column_dimensions.items():
            #     if colDimension.hidden:
            #         hiddenCols.append(colLetter)

            # self.df = pd.read_excel(self.spreadsheetPath.text())
            # unhidden = list(set(self.df.columns) - set(hiddenCols))
            # self.df = self.df[unhidden]

            self.df = pd.read_excel(self.spreadsheetPath.text(), "Sheet1")
            patients = self.df["patient_code"].to_string(index=False)
            scans = self.df["cleaned_path"]
            patients = patients.splitlines()
            self.patients = []
            self.scans = []
            self.xcelIndices = []
            for i in range(len(scans)):
                path = str(scans[i]).split("/")
                try:
                    fileName = path[-1]
                    folder = path[-2]
                    if fileName.endswith(".dcm") and folder == "DICOM_cine":
                        self.patients.append(patients[i])
                        self.scans.append(fileName[:-4])
                        self.xcelIndices.append(i)
                except (AttributeError, NameError, IndexError):
                    continue

            self.imagesScrollArea.setHidden(False)
            self.selectSpreadsheeetLabel.setHidden(True)
            self.spreadsheetPath.setHidden(True)
            self.chooseSpreadsheetFileButton.setHidden(True)
            self.clearSpreadsheetFileButton.setHidden(True)
            self.findImagesButton.setHidden(True)
            self.undoSpreadsheetButton.setHidden(False)
            self.generateImageButton.setHidden(False)

            self.imagesScrollArea.setRowCount(len(self.patients))
            self.imagesScrollArea.setVerticalHeaderLabels(self.patients)

            for i in range(len(self.patients)):
                item = QTableWidgetItem(self.scans[i])
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.imagesScrollArea.setItem(i, 0, item)

    def backToWelcomeScreen(self):
        self.welcomeGui.show()
        self.hide()

    def getNiftiBmodePath(self):
        fileName, _ = QFileDialog.getOpenFileName(
            None, "Open File", filter="*.nii *.nii.gz"
        )
        if fileName != "":
            self.niftiBmodeInput.setText(fileName)

    def getNiftiCePath(self):
        fileName, _ = QFileDialog.getOpenFileName(
            None, "Open File", filter="*.nii *.nii.gz"
        )
        if fileName != "":
            self.niftiCeInput.setText(fileName)

    def getAviPath(self):
        fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter="*.avi")
        if fileName != "":
            self.aviPath.setText(fileName)
            
    def getXmlPath(self):
        fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter="*.xml")
        if fileName != "":
            self.aviPath.setText(fileName)

    def getSpreadsheetPath(self):
        if self.format == "DicomExcel":
            fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter="*.xlsx")
        else:
            fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter="*.dcm *.DCM *")
        if fileName != "":
            self.spreadsheetPath.setText(fileName)

    def clearSpreadsheetPath(self):
        self.spreadsheetPath.setText("")

    def moveToRoiSelection(self):
        if (
            (
                len(self.spreadsheetPath.text()) > 0
                and len(self.imagesScrollArea.selectedIndexes()) == 1
            )
            or (
                len(self.niftiBmodeInput.text()) > 0
                and len(self.niftiCeInput.text()) > 0
            )
            or (len(self.aviPath.text()) > 0)
            or (
                os.path.exists(self.spreadsheetPath.text())
            )
        ):
            del self.roiSelectionGui
            self.roiSelectionGui = RoiSelectionGUI()
            if self.format == "DicomExcel":
                xcel_dir = Path(self.spreadsheetPath.text())
                xcel_dir = xcel_dir.parent.absolute()
                self.roiSelectionGui.df = self.df
                self.roiSelectionGui.xcelIndices = self.xcelIndices
                index = self.imagesScrollArea.selectedIndexes()[0].row()
                self.roiSelectionGui.setFilenameDisplays(self.scans[index])
                self.roiSelectionGui.openDicomImage(index, xcel_dir)
            elif self.format == "DicomDirect":
                self.roiSelectionGui.setFilenameDisplays(self.spreadsheetPath.text())
                self.roiSelectionGui.openDicomImage(-1, self.spreadsheetPath.text())
            elif self.format == "Nifti":
                self.roiSelectionGui.setFilenameDisplays(self.niftiBmodeInput.text())
                self.roiSelectionGui.openNiftiImage(
                    self.niftiBmodeInput.text(), self.niftiCeInput.text()
                )
            elif self.format == "VisualsonicsXml":
                self.roiSelectionGui.setFilenameDisplays(self.aviPath.text())
                self.roiSelectionGui.openVisualsonicsXmlImage(self.aviPath.text())
            else:
                self.roiSelectionGui.setFilenameDisplays(self.aviPath.text())
                self.roiSelectionGui.openAviImage(self.aviPath.text())
            self.roiSelectionGui.lastGui = self
            self.roiSelectionGui.show()
            self.hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = SelectImageGUI_CeusMcTool2d()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())
