from CeusMcTool2d.ticAnalysis_ui import *
from CeusMcTool2d.ceusAnalysis_ui_helper import *

import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import numpy as np
import Utils.lognormalFunctions as lf
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class TicAnalysisGUI(Ui_ticEditor, QWidget):
    def __init__(self):
        # self.selectImage = QWidget()
        super().__init__()
        self.setupUi(self)
        self.deSelectLastPointButton.setHidden(True)
        self.removeSelectedPointsButton.setHidden(True)
        self.restoreLastPointsButton.setHidden(True)
        self.acceptTicButton.setHidden(True)
        self.acceptT0Button.setHidden(True)
        self.t0Slider.setHidden(True)

        self.t0Slider.setValue(0)

        self.mcResultsBmode = None
        self.mcResultsCE = None
        self.curFrameIndex = None
        self.xCur = None
        self.yCur = None
        self.sliceArray = None
        self.x = None
        self.y = None
        self.ceusAnalysisGui = None
        self.roiArea = None
        self.x0_bmode = None
        self.y0_bmode = None
        self.w_bmode = None
        self.h_bmode = None
        self.x0_CE = None
        self.y0_CE = None
        self.w_CE = None
        self.h_CE = None
        self.dataFrame = None


        self.bmodeCoverPixmap = QPixmap(231, 211)
        self.bmodeCoverPixmap.fill(Qt.transparent)
        self.bmodeCoverLabel.setPixmap(self.bmodeCoverPixmap)
        self.ceCoverPixmap = QPixmap(231, 211)
        self.ceCoverPixmap.fill(Qt.transparent)
        self.ceCoverLabel.setPixmap(self.ceCoverPixmap)

        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.horizLayout = QHBoxLayout(self.ticFrame)
        self.horizLayout.addWidget(self.canvas)
        self.canvas.draw()
        self.ax = self.fig.add_subplot(111)

        self.selectT0Button.clicked.connect(self.initT0)

        self.t0Index = -1
        self.selectedPoints = []
        self.frontPointsX = []
        self.frontPointsY = []
        self.removedPointsX = []
        self.removedPointsY = []
        self.ceusResultsGui = None
        self.lastGui = None
        self.prevLine = None
        self.timeLine = None
        self.backButton.clicked.connect(self.backToLastScreen)
        self.acceptT0Button.clicked.connect(self.acceptT0)

    def backToLastScreen(self):
        self.lastGui.dataFrame = self.dataFrame
        self.lastGui.show()
        self.hide()

    def findSliceFromTime(self, inputtedTime):
        i = 0
        while i < len(self.sliceArray):
            if inputtedTime < self.sliceArray[i]:
                break
            i += 1
        if i == len(self.sliceArray):
            i -= 1
        elif i > 0:
            if (self.sliceArray[i] - inputtedTime) > (self.sliceArray[i-1] - inputtedTime):
                i -= 1
        if i < 0:
            i = 0
        return i

    def sliceValueChanged(self):
        if not self.t0Slider.isHidden():
            self.curFrameIndex = self.findSliceFromTime(self.t0Slider.value())
        self.updateBmode()
        self.updateCE()
        self.update()
    
    def updateBmode(self):
        self.mcDataBmode = np.require(self.mcResultsBmode[self.curFrameIndex], np.uint8, 'C')
        self.bytesLineMc, _ = self.mcDataBmode[:,:,0].strides
        self.qImgMcBmode = QImage(self.mcDataBmode, self.x, self.y, self.bytesLineMc, QImage.Format_RGB888)
        self.mcBmodeDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMcBmode).scaled(231, 211))
    
    def updateCE(self):
        self.mcDataCE = np.require(self.mcResultsCE[self.curFrameIndex], np.uint8, 'C')
        self.bytesLineMc, _ = self.mcDataCE[:,:,0].strides
        self.qImgMcCE = QImage(self.mcDataCE, self.x, self.y, self.bytesLineMc, QImage.Format_RGB888)
        self.mcCeDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMcCE).scaled(231, 211))

    def initT0(self):
        self.acceptT0Button.setHidden(False)
        self.selectT0Button.setHidden(True)
        self.t0Slider.setHidden(False)

        self.t0Slider.setMinimum(int(min(self.ticX[:,0])))
        self.t0Slider.setMaximum(int(max(self.ticX[:,0])))
        self.t0Slider.valueChanged.connect(self.t0ScrollValueChanged)
        self.t0Slider.setValue(0)
        if self.prevLine != None:
            self.prevLine.remove()
            self.t0Index = -1
        self.prevLine = self.ax.axvline(x = self.t0Slider.value(), color = 'green', label = 'axvline - full height')
        self.canvas.draw()

    def graph(self,x,y):
        global ticX, ticY
        # y -= min(y)
        self.ticX = x
        self.ticY = y
        ticX = self.ticX
        ticY = self.ticY
        self.ax.plot(x[:,0],y, picker=True)
        self.ax.scatter(x[:,0],y,color='r')
        self.ax.set_xlabel("Time (s)", fontsize=11, labelpad=1)
        self.ax.set_ylabel("Signal Amplitude", fontsize=11, labelpad=1)
        self.ax.set_title("Time Intensity Curve (TIC)", fontsize=14, pad=1.5)
        self.ax.tick_params('both', pad=0.3, labelsize=7.2)
        plt.xticks(fontsize=8)
        plt.yticks(fontsize=8)
        plt.xticks(np.arange(0, int(max(self.ticX[:,0]))+10, 10))
        range = max(x[:,0]) - min(x[:,0])
        self.ax.set_xlim(xmin=min(x[:,0])-(0.05*range), xmax=max(x[:,0])+(0.05*range))
        if self.timeLine != None:
            self.ax.add_line(self.timeLine)
        self.fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.1)
        self.fig.canvas.mpl_connect('pick_event', self.selectPoint)

        if self.t0Index > -1:
            self.mask = np.zeros(self.ticX[:,0].shape, dtype=bool)
            self.selector = RectangleSelector(self.ax, self.rect_highlight, useblit=True, props = dict(facecolor='cyan', alpha=0.2))

        self.canvas.draw()

    def t0ScrollValueChanged(self):
        self.prevLine.remove()
        self.prevLine = self.ax.axvline(x = self.t0Slider.value(), color = 'green', label = 'axvline - full height')
        self.sliceValueChanged()
        self.canvas.draw()

    def removeSelectedPoints(self):
        if len(self.selectedPoints):
            self.selectedPoints.sort()
            j = 0
            curRemovedX = []
            curRemovedY = []
            for i in range(len(self.ticX)):
                if i == self.selectedPoints[j]:
                    curRemovedX.append(self.ticX[i])
                    curRemovedY.append(self.ticY[i])
                    j += 1
                    if j == len(self.selectedPoints):
                        break
            self.ticX = np.delete(self.ticX, self.selectedPoints, axis=0)
            self.ticY = np.delete(self.ticY, self.selectedPoints)
            self.ax.clear()
            self.graph(self.ticX,self.ticY)
            self.removedPointsX.append(curRemovedX)
            self.removedPointsY.append(curRemovedY)
            self.selectedPoints = []

    def setFilenameDisplays(self, imageName):
        self.imagePathInput.setHidden(False)
        
        imFile = imageName.split('/')[-1]

        self.imagePathInput.setText(imFile)
        self.inputTextPath = imageName

    def acceptTIC(self):
        del self.ceusAnalysisGui
        self.ceusAnalysisGui = CeusAnalysisGUI()
        self.ceusAnalysisGui.show()
        self.ceusAnalysisGui.ax.clear()
        self.ceusAnalysisGui.ax.plot(self.ticX[:,0], self.ticY)
        self.ceusAnalysisGui.setFilenameDisplays(self.imagePathInput.text())

        tmppv = np.max(self.ticY)
        self.ticY = self.ticY/tmppv;
        x = self.ticX[:,0] - np.min(self.ticX[:,0])

        # Bunch of checks
        if np.isnan(np.sum(self.ticY)):
            print('STOPPED:NaNs in the VOI')
            return;
        if np.isinf(np.sum(self.ticY)):
            print('STOPPED:InFs in the VOI')
            return;

        # Do the fitting
        try:
            params, popt, wholecurve = lf.data_fit([x, self.ticY], tmppv);
            self.ceusAnalysisGui.ax.plot(self.ticX[:,0], wholecurve)
            range = max(self.ticX[:,0]) - min(self.ticX[:,0])
            self.ceusAnalysisGui.ax.set_xlim(xmin=min(self.ticX[:,0])-(0.05*range), xmax=max(self.ticX[:,0])+(0.05*range))
        except RuntimeError:
            print('RunTimeError')
            params = np.array([np.max(self.ticY)*tmppv, np.trapz(self.ticY*tmppv, x=self.ticX[:,0]), self.ticX[-1,0], np.argmax(self.ticY), np.max(self.ticX[:,0])*2, 0]);
        self.fig.subplots_adjust(left=0.1, right=0.97, top=0.85, bottom=0.25)
        self.canvas.draw()
        self.ticY *= tmppv

        self.ceusAnalysisGui.aucVal.setText(str(np.around(params[1], decimals=3)))
        self.ceusAnalysisGui.peVal.setText(str(np.around(params[0], decimals=3)))
        self.ceusAnalysisGui.tpVal.setText(str(np.around(params[2], decimals=2)))
        self.ceusAnalysisGui.mttVal.setText(str(np.around(params[3], decimals=2)))
        self.ceusAnalysisGui.tmppvVal.setText(str(np.around(tmppv, decimals=1)))
        self.ceusAnalysisGui.voiVolumeVal.setText(str(np.around(self.roiArea, decimals=1)))
        self.ceusAnalysisGui.auc = params[1]
        self.ceusAnalysisGui.pe = params[0]
        self.ceusAnalysisGui.tp = params[2]
        self.ceusAnalysisGui.mtt = params[3]
        self.ceusAnalysisGui.tmppv = tmppv
        self.ceusAnalysisGui.roiArea = self.roiArea
        self.ceusAnalysisGui.mcResultsBmode = self.mcResultsBmode
        self.ceusAnalysisGui.mcResultsCE = self.mcResultsCE
        self.ceusAnalysisGui.curFrameIndex = self.curFrameIndex
        self.ceusAnalysisGui.xCur = self.xCur
        self.ceusAnalysisGui.yCur = self.yCur
        self.ceusAnalysisGui.x = self.x
        self.ceusAnalysisGui.y = self.y
        self.ceusAnalysisGui.dataFrame = self.dataFrame
        self.ceusAnalysisGui.sliceArray = self.sliceArray
        self.ceusAnalysisGui.x0_bmode = self.x0_bmode
        self.ceusAnalysisGui.y0_bmode = self.y0_bmode
        self.ceusAnalysisGui.w_bmode = self.w_bmode
        self.ceusAnalysisGui.h_bmode = self.h_bmode
        self.ceusAnalysisGui.x0_CE = self.x0_CE
        self.ceusAnalysisGui.y0_CE = self.y0_CE
        self.ceusAnalysisGui.w_CE = self.w_CE
        self.ceusAnalysisGui.h_CE = self.h_CE
        self.ceusAnalysisGui.curSliceSpinBox.setValue(self.sliceArray[self.curFrameIndex])
        self.ceusAnalysisGui.curSliceSlider.setValue(self.curFrameIndex)
        self.ceusAnalysisGui.curSliceTotal.setText(str(self.mcResultsBmode.shape[0]-1))
        self.ceusAnalysisGui.totalSecondsLabel.setText(str(self.sliceArray[-1]))
        self.ceusAnalysisGui.curSliceSlider.setMaximum(self.mcResultsBmode.shape[0]-1)
        self.ceusAnalysisGui.curSliceSpinBox.setMaximum(self.mcResultsBmode.shape[0]-1)

        self.ceusAnalysisGui.updateBmode()
        self.ceusAnalysisGui.updateCE()
        self.ceusAnalysisGui.show()
        self.ceusAnalysisGui.curSliceSlider.setValue(self.curFrameIndex)
        self.ceusAnalysisGui.lastGui = self
        self.hide()


    def acceptT0(self):
        self.t0Slider.setHidden(True)
        self.t0Slider.setHidden(True)
        self.acceptT0Button.setHidden(True)
        self.deSelectLastPointButton.setHidden(False)
        self.deSelectLastPointButton.clicked.connect(self.deselectLast)
        self.removeSelectedPointsButton.setHidden(False)
        self.removeSelectedPointsButton.clicked.connect(self.removeSelectedPoints)
        self.restoreLastPointsButton.setHidden(False)
        self.restoreLastPointsButton.clicked.connect(self.restoreLastPoints)
        self.acceptTicButton.setHidden(False)
        self.acceptTicButton.clicked.connect(self.acceptTIC)

        if self.t0Index == -1:
            for i in range(len(self.ticX[:,0])):
                if self.ticX[:,0][i] > self.t0Slider.value():
                    break
            self.t0Index = i

        self.selectedPoints = list(range(self.t0Index))
        if len(self.selectedPoints):
            self.removeSelectedPoints()
            self.frontPointsX = self.removedPointsX[-1]
            self.frontPointsY = self.removedPointsY[-1]
            self.removedPointsX.pop()
            self.removedPointsY.pop()
        # self.ticX[:,0] -= (min(self.ticX[:,0]) - 1)
        self.ax.clear()
        self.graph(self.ticX, self.ticY)

    def rect_highlight(self, event1, event2):
        self.mask |= self.inside(event1, event2)
        x = self.ticX[:,0][self.mask]
        y = self.ticY[self.mask]
        addedIndices = np.sort(np.array(list(range(len(self.ticY))))[self.mask])
        for index in addedIndices:
            self.selectedPoints.append(index) 
        self.ax.scatter(x, y, color='orange')
        self.canvas.draw()

    def inside(self, event1, event2):
        # Returns a boolean mask of the points inside the rectangle defined by
        # event1 and event2
        x0, x1 = sorted([event1.xdata, event2.xdata])
        y0, y1 = sorted([event1.ydata, event2.ydata])
        mask = ((self.ticX[:,0] > x0) & (self.ticX[:,0] < x1) &
                (self.ticY > y0) & (self.ticY < y1))
        return mask
    
    def deselectLast(self):
        if len(self.selectedPoints):
            lastPt = self.selectedPoints[-1]
            self.selectedPoints.pop()
            self.ax.scatter(self.ticX[lastPt][0],self.ticY[lastPt],color='red')
            self.canvas.draw()
            self.mask = np.zeros(self.ticX[:,0].shape, dtype=bool)

    def restoreLastPoints(self):
        if len(self.removedPointsX) > 0:
            for i in range(len(self.selectedPoints)):
                self.deselectLast()
            self.selectedPoints = []
            j = 0
            i = 0
            max = self.ticX.shape[0] + len(self.removedPointsX[-1])
            while i < self.ticX.shape[0]-1:
                if self.ticX[i][0] < self.removedPointsX[-1][j][0] and self.removedPointsX[-1][j][0] < self.ticX[i+1][0]:
                    self.ticX = np.insert(self.ticX, i+1, self.removedPointsX[-1][j], axis=0)
                    self.ticY = np.insert(self.ticY, i+1, self.removedPointsY[-1][j])
                    j += 1
                    if j == len(self.removedPointsX[-1]):
                        break
                i += 1
            if i < max and j < len(self.removedPointsX[-1]):
                while j < len(self.removedPointsX[-1]):
                    self.ticX = np.insert(self.ticX, i+1, self.removedPointsX[-1][j], axis=0)
                    self.ticY = np.append(self.ticY, self.removedPointsY[-1][j])
                    j += 1
                    i += 1
            self.removedPointsX.pop()
            self.removedPointsY.pop()
            self.ax.clear()
            ticX = self.ticX
            ticY = self.ticY
            self.graph(ticX, ticY)

    def selectPoint(self, event):
        if self.t0Slider.isHidden():
            thisline = event.artist
            xdata = thisline.get_xdata()
            ind = event.ind[0]
            if self.timeLine != None:
                self.timeLine.remove()
            self.timeLine = self.ax.axvline(x = xdata[ind], color = (0,0,1,0.3), label = 'axvline - full height', zorder=1)
            self.curFrameIndex = self.findSliceFromTime(xdata[ind])
            self.updateBmode()
            self.updateCE()
            self.canvas.draw()    
        

if __name__ == "__main__":
    import sys
    from numpy import genfromtxt
    # my_data = genfromtxt('/Users/davidspector/Home/Stanford/USImgAnalysisGui_v2/Data/newest_test_tic.csv', delimiter=',')[1:]
    my_data = genfromtxt('/Users/davidspector/Home/Stanford/USImgAnalysisGui_v2/Data/C3P13_original_tic.csv', delimiter=',')[1:]
    # my_data = genfromtxt('/Users/davidspector/Home/Stanford/USImgAnalysisGui_v2/Data/C3P13_original_tic.csv', delimiter=',')

    test_ticX = np.array([[my_data[i,0],i] for i in range(len(my_data[:,0]))])
    # test_ticY = my_data[:,1]
    test_ticY = my_data[:,1] - min(my_data[:,1])

    normalizer = max(test_ticY)

    print(np.average(my_data[:,1]))


    app = QApplication(sys.argv)
    ui = TicAnalysisGUI()
    ui.show()
    ui.graph(test_ticX, test_ticY)
    sys.exit(app.exec_())
