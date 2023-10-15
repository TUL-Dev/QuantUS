from CeusMcTool2d.selectImage_ui import *
from CeusMcTool2d.roiSelection_ui_helper import *

import os
from pathlib import Path
import Utils.utils as ut
import pandas as pd
import openpyxl

from PyQt5.QtWidgets import QWidget, QApplication, QHeaderView, QTableWidgetItem

import platform
system = platform.system()

class SelectImageGUI_CeusMcTool2d(Ui_selectImage, QWidget):
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

        self.format = None

        header = self.imagesScrollArea.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setStyleSheet("""
        QHeaderView::section{
            background-color: white;
            font-size: 15px;
            color: black;
        }""")
        self.imagesScrollArea.verticalHeader().setStyleSheet("""
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
        }""")

        self.imageNifti = 0

        self.roiSelectionGui = None
        self.welcomeGui = None
        self.dataFrame = None

        self.generateImageButton.clicked.connect(self.moveToRoiSelection)
        self.chooseSpreadsheetFileButton.clicked.connect(self.getSpreadsheetPath)
        self.clearSpreadsheetFileButton.clicked.connect(self.clearSpreadsheetPath)
        self.backButton.clicked.connect(self.backToWelcomeScreen)
        self.undoSpreadsheetButton.clicked.connect(self.undoSpreadsheetEntry)
        self.niftiButton.clicked.connect(self.niftiSelected)
        self.dicomButton.clicked.connect(self.dicomSelected)
    
    def moveToFileChoice(self):
        self.selectFormatLabel.setHidden(True)
        self.niftiButton.setHidden(True)
        self.dicomButton.setHidden(True)

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

        self.format = 'Nifti'

        self.chooseNiftiBmodeButton.clicked.connect(self.getNiftiBmodePath)
        self.chooseNiftiCeButton.clicked.connect(self.getNiftiCePath)
        self.clearNiftiBmodeButton.clicked.connect(self.niftiBmodeInput.clear)
        self.clearNiftiCeButton.clicked.connect(self.niftiCeInput.clear)
        self.findImagesButton.clicked.connect(self.moveToRoiSelection)

    def dicomSelected(self):
        self.moveToFileChoice()
        self.chooseSpreadsheetFileButton.setHidden(False)
        self.clearSpreadsheetFileButton.setHidden(False)
        self.spreadsheetPath.setHidden(False)
        self.selectSpreadsheeetLabel.setHidden(False)

        self.format = 'Dicom'
        self.findImagesButton.clicked.connect(self.listImages)

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

            self.df = pd.read_excel(self.spreadsheetPath.text(), 'Sheet1')
            patients = self.df['patient_code'].to_string(index=False)
            scans = self.df['cleaned_path']
            patients = patients.splitlines()
            self.patients = []
            self.scans = []
            self.xcelIndices = []
            for i in range(len(scans)):
                path = str(scans[i]).split('/')
                try:
                    fileName = path[-1]
                    folder = path[-2]
                    if fileName.endswith('.dcm') and folder == 'DICOM_cine':
                        self.patients.append(patients[i])
                        self.scans.append(fileName[:-4])
                        self.xcelIndices.append(i)
                except:
                    continue
            # self.scans = [str(scan).split('/')[-1][:-4] for scan in scans]

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
        self.welcomeGui.ceus2dMcData = self.dataFrame
        self.welcomeGui.show()
        self.hide()

    def getNiftiBmodePath(self):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = '*.nii *.nii.gz')
        if fileName != '':
            self.niftiBmodeInput.setText(fileName)

    def getNiftiCePath(self):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = '*.nii *.nii.gz')
        if fileName != '':
            self.niftiCeInput.setText(fileName)

    def getSpreadsheetPath(self):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = '*.xlsx')
        if fileName != '':
            self.spreadsheetPath.setText(fileName)

    def clearSpreadsheetPath(self):
        self.spreadsheetPath.setText('')

    def moveToRoiSelection(self):
        if (len(self.spreadsheetPath.text()) > 0 and len(self.imagesScrollArea.selectedIndexes()) == 1) or (len(self.niftiBmodeInput.text()) > 0 and len(self.niftiCeInput.text()) > 0):
            del self.roiSelectionGui
            self.roiSelectionGui = RoiSelectionGUI()
            self.roiSelectionGui.dataFrame = self.dataFrame
            if self.format == 'Dicom':
                xcel_dir = Path(self.spreadsheetPath.text())
                xcel_dir = xcel_dir.parent.absolute()
                self.roiSelectionGui.df = self.df
                self.roiSelectionGui.xcelIndices = self.xcelIndices
                index = self.imagesScrollArea.selectedIndexes()[0].row()
                self.roiSelectionGui.setFilenameDisplays(self.scans[index])
                self.roiSelectionGui.openDicomImage(index, xcel_dir)
            else:
                self.roiSelectionGui.setFilenameDisplays(self.niftiBmodeInput.text())
                self.roiSelectionGui.openNiftiImage(self.niftiBmodeInput.text(), self.niftiCeInput.text())
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