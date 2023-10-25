from UtcTool2d.psGraphDisplay_ui import *
import os
import csv
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QFileDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class PsGraphDisplay(Ui_psGraphWidget, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Display PS Graph
        self.horizontalLayout = QHBoxLayout(self.psGraphFrame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Frequency (MHz)", fontsize=8)
        self.ax.set_ylabel("Power (dB)", fontsize=8)
        self.horizontalLayout.addWidget(self.canvas)