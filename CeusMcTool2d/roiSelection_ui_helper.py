from CeusMcTool2d.roiSelection_ui import *
from CeusMcTool2d.ticAnalysis_ui_helper import *
from CeusMcTool2d.saveRoi_ui_helper import *


import nibabel as nib
import numpy as np
from scipy.ndimage import binary_fill_holes

import os
import scipy.interpolate as interpolate
import numpy as np
import nibabel as nib
from scipy.spatial import ConvexHull
import pyvista as pv
import Utils.motionCorrection as mc
import cv2
import pydicom as dicom
from pydicom.pixel_data_handlers import convert_color_space
import json

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtCore import QLine, Qt, QRect

import platform
system = platform.system()

# Assumes no gap between images
# imDimsHashTable = {("TOSHIBA_MEC_US", "TUS-AI900"): (0.0898, 0.145, 0.410, 0.672)} #stores relative (x0_bmode, y0_bmode, w_bmode, h_bmode)


class RoiSelectionGUI(Ui_constructRoi, QWidget):
    def __init__(self):
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
            self.imagePathInput.setStyleSheet("""QLabel {
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

        self.acceptGeneratedRoiButton.setHidden(True)
        self.undoRoiButton.setHidden(True)
        self.roiFitNoteLabel.setHidden(True)
        self.drawRoiButton.setHidden(True)
        self.backFromDrawButton.setHidden(True)
        self.undoLastPtButton.setHidden(True)
        self.redrawRoiButton.setHidden(True)
        self.fitToRoiButton.setHidden(True)
        self.roiFitNoteLabel.setHidden(True)
        self.closeRoiButton.setHidden(True)
        self.preLoadedRoiButton.setHidden(True)
        self.chooseRoiButton.setHidden(True)
        self.backFromLoadButton.setHidden(True)
        self.saveRoiButton.setHidden(True)
        self.df = None
        self.dataFrame = None
        self.niftiSegPath = None

        self.curFrameIndex= 0
        self.curAlpha = 255
        self.curPointsPlottedX = []
        self.curPointsPlottedY = []
        self.pointsPlotted = []
        self.xCur = 0
        self.yCur = 0
        self.lastGui = None
        self.spline = None
        self.oldSpline = []
        self.mcResultsArray = []
        self.ticAnalysisGui = TicAnalysisGUI()
        self.saveRoiGUI = SaveRoiGUI()
        self.index = None
        self.bboxes = None
        self.ref_frames = None
        self.xcelIndices = None

        self.imDrawn = 0

        # self.bmodeCoverPixmap = QPixmap(381, 351)
        # self.bmodeCoverPixmap.fill(Qt.transparent)
        # self.bmodeCoverLabel.setPixmap(self.bmodeCoverPixmap)

        # self.ceCoverPixmap = QPixmap(381, 351)
        # self.ceCoverPixmap.fill(Qt.transparent)
        # self.ceCoverLabel.setPixmap(self.ceCoverPixmap)

        self.setMouseTracking(True)

        self.backButton.clicked.connect(self.backToLastScreen)
        self.newRoiButton.clicked.connect(self.drawNewRoi)
        self.loadRoiButton.clicked.connect(self.startLoadRoi)
        self.saveRoiButton.clicked.connect(self.startSaveRoi)
        self.backFromDrawButton.clicked.connect(self.backFromDraw)

    def startSaveRoi(self):
        self.saveRoiGUI.roiSelectionGUI = self
        pathPieces = self.fullPath.split('/')
        pathPieces[-2] = 'nifti_segmentation_QUANTUS'
        pathPieces[-1] = pathPieces[-1][:-4] # removes .dcm from filename
        path = pathPieces[0]
        for i in range(len(pathPieces)-2):
            path = str(path + '/' + pathPieces[i+1])
        if not os.path.exists(path):
            os.mkdir(path)
        self.saveRoiGUI.newFolderPathInput.setText(path)
        self.saveRoiGUI.newFileNameInput.setText(str(pathPieces[-1] + '.nii.gz'))
        self.saveRoiGUI.show()

    def saveRoi(self, fileDestination, name, frame):
        segMask = np.zeros([self.numSlices, self.y, self.x])
        self.pointsPlotted = [*set(self.pointsPlotted)]
        for point in self.pointsPlotted:
            segMask[frame, point[1], point[0]] = 1
        segMask[frame] = binary_fill_holes(segMask[frame])

        affine = np.eye(4)
        niiarray = nib.Nifti1Image(np.transpose(segMask).astype('uint8'), affine)
        niiarray.header['descrip'] = self.imagePathInput.text()
        outputPath = os.path.join(fileDestination, name)
        if os.path.exists(outputPath):
            os.remove(outputPath)
        nib.save(niiarray, outputPath)

    def startLoadRoi(self):
        self.newRoiButton.setHidden(True)
        self.loadRoiButton.setHidden(True)
        self.preLoadedRoiButton.setHidden(False)
        self.chooseRoiButton.setHidden(False)
        self.backFromLoadButton.setHidden(False)

        self.backFromLoadButton.clicked.connect(self.backFromLoad)
        self.preLoadedRoiButton.clicked.connect(self.loadPreloadedRoi)
        self.chooseRoiButton.clicked.connect(self.loadChosenRoi)

    def loadChosenRoi(self):
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open File', filter = '*.nii.gz')
        if fileName != '':
            nibIm = nib.load(fileName)
            if self.imagePathInput.text().replace("'", '"') == str(nibIm.header['descrip'])[2:-1]:
                self.loadRoi(nibIm.get_fdata().astype(np.uint8))

    def loadPreloadedRoi(self):  
        try:      
            self.niftiSegPath = self.df.loc[self.index, 'nifti_segmentation_path']
        except:
            return
        mask = nib.load(os.path.join(self.xcel_dir, self.niftiSegPath), mmap=False).get_fdata().astype(np.uint8)
        self.loadRoi(mask)
        
    def loadRoi(self, mask):
        mask = np.transpose(mask)
        maskPoints = np.where(mask > 0)
        minX = np.min(maskPoints[2])
        maxX = np.max(maskPoints[2])
        minY = np.min(maskPoints[1])
        maxY = np.max(maskPoints[1])
        if maxX < self.x0_CE + self.w_CE and minX > self.x0_CE and maxY < self.y0_CE + self.h_CE and minY > self.y0_CE:
            self.imDrawn = 2
        elif maxX < self.x0_bmode + self.w_bmode and minX > self.x0_bmode and maxY < self.y0_bmode + self.h_bmode and minY > self.y0_bmode:
            self.imDrawn = 1
        else:
            print("Cannont complete motion correction with this ROI!")
            return
        maskPoints = np.transpose(maskPoints)
        for point in maskPoints:
            self.maskCoverImg[point[1], point[2]] = [0,0,255,255]
            self.pointsPlotted.append((point[2], point[1]))
        self.curFrameIndex = maskPoints[0,0]
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.perform_MC(True)

        self.backFromLoadButton.setHidden(True)
        self.preLoadedRoiButton.setHidden(True)
        self.chooseRoiButton.setHidden(True)
        self.undoRoiButton.setHidden(False)
        self.acceptGeneratedRoiButton.setHidden(False)

    def drawNewRoi(self):
        self.newRoiButton.setHidden(True)
        self.loadRoiButton.setHidden(True)
        self.undoLastPtButton.setHidden(True)
        self.saveRoiButton.setHidden(True)
        self.drawRoiButton.setHidden(False)
        self.backFromDrawButton.setHidden(False)
        self.undoLastPtButton.setHidden(False)
        self.redrawRoiButton.setHidden(False)
        self.fitToRoiButton.setHidden(False)
        self.closeRoiButton.setHidden(False)
        self.saveRoiButton.setHidden(True)

    def backToLastScreen(self):
        self.lastGui.dataFrame = self.dataFrame
        self.lastGui.show()
        self.hide()


    def setFilenameDisplays(self, imageName):
        self.imagePathInput.setHidden(False)
        
        imFile = imageName.split('/')[-1]

        self.imagePathInput.setText(imFile)
        self.inputTextPath = imageName

    def perform_MC(self, loaded=False):
        # Credit Thodsawit Tiyarattanachai, MD. See Utils/motionCorrection.py for full citation
        self.segMask = np.zeros([self.numSlices, self.y, self.x])
        self.pointsPlotted = [*set(self.pointsPlotted)] 
        points = self.pointsPlotted    
        if self.imDrawn == 2:
            xDiff = self.x0_bmode - self.x0_CE
            yDiff = self.y0_bmode - self.y0_CE
            points = [[point[0]+xDiff, point[1]+yDiff] for point in self.pointsPlotted]
        elif self.imDrawn == 0:
            return
        
        for point in points:
            self.segMask[self.curFrameIndex,point[1], point[0]] = 1
        if not loaded:
            self.segMask[self.curFrameIndex] = binary_fill_holes(self.segMask[self.curFrameIndex])   

        set_quantile = 0.50
        step = 1 # fullFrameRate. step=2 for halfFrameRate
        threshold_decrease_per_step = 0.02

        # get ref frame
        search_margin = int((0.5/15)*self.h_bmode)
        ref_frames = [self.curFrameIndex]
        mask = self.segMask[self.curFrameIndex]
        pos_coor = np.argwhere(mask > 0)
        x_values = pos_coor[:,1]
        y_values = pos_coor[:,0]
        x0 = x_values.min()
        x1 = x_values.max()
        w = x1 - x0 +1
        y0 = y_values.min()
        y1 = y_values.max()
        h = y1 - y0 + 1
        bboxes = [(x0, y0, w, h)]
        masks = [mask]

        ###################################################
        # find initial correlation in the first run
        min_x0 = min([e[0] for e in bboxes]) - search_margin
        max_x1 = max([e[0]+e[2] for e in bboxes]) + search_margin
        min_y0 = min([e[1] for e in bboxes]) - search_margin
        max_y1 = max([e[1]+e[3] for e in bboxes])
        bmode = self.fullGrayArray[:, min_y0:max_y1, min_x0:max_x1]
        ref_f = ref_frames[0]
        ref_b = bboxes[0]
        ref_bmodes = [self.fullGrayArray[ref_f, \
                                      ref_b[1]:ref_b[1]+ref_b[3], \
                                      ref_b[0]:ref_b[0]+ref_b[2]]]
        
        corr_initial_run, threshold = mc.find_correlation(bmode, ref_bmodes, set_quantile)
        ###################################################

        ref_patches = ref_bmodes[:]

        previous_all_lesion_bboxes = [None]*self.fullGrayArray.shape[0]
        iteration = 1

        while True:

            out_array = np.zeros(list(self.fullGrayArray.shape) + [3], dtype=np.uint8)

            all_search_bboxes = [None]*self.fullGrayArray.shape[0]
            all_lesion_bboxes = [None]*self.fullGrayArray.shape[0]
            corr_with_ref = [None]*self.fullGrayArray.shape[0]

            for ref_idx in range(len(ref_frames)):
                ref_frame = ref_frames[ref_idx]
                ref_bbox = bboxes[ref_idx]

                if ref_idx == 0:
                    if ref_idx == len(ref_frames) - 1:
                        #There is only 1 ref_frame
                        ref_begin = 0
                        ref_end = self.fullGrayArray.shape[0]
                    else:
                        #This is the first ref_frame. There are >1 ref frames.
                        ref_begin = 0
                        ref_end = int((ref_frames[ref_idx]+ref_frames[ref_idx+1])/2)
                else:
                    if ref_idx == len(ref_frames) - 1:
                        #This is the last ref frame. There are >1 ref frames.
                        ref_begin = int((ref_frames[ref_idx-1]+ref_frames[ref_idx])/2)
                        ref_end = self.fullGrayArray.shape[0]
                    else:
                        #These are ref frames in the middle. There are >1 ref frames.
                        ref_begin = int((ref_frames[ref_idx-1]+ref_frames[ref_idx])/2)
                        ref_end = int((ref_frames[ref_idx]+ref_frames[ref_idx+1])/2)

                #######################

                #forward tracking
                ##############################################################
                if ref_frame < ref_end-1:  #can forward track only if there are frames after the ref_frame
                    #print('forward tracking')

                    previous_bbox = ref_bbox

                    valid = True

                    for frame in range(ref_frame, ref_end, step):

                        full_frame = self.fullGrayArray[frame]

                        if valid:
                            search_w = int(previous_bbox[2]+(2*search_margin))
                            search_h = int(previous_bbox[3]+(2*search_margin))
                            search_x0 = int(previous_bbox[0] - ((search_w - previous_bbox[2])/2))
                            search_y0 = int(previous_bbox[1] - ((search_h - previous_bbox[3])/2))
                            search_bbox = (search_x0, search_y0, search_w, search_h)
                            search_region = full_frame[search_y0:search_y0+search_h,
                                                    search_x0:search_x0+search_w]

                            all_search_bboxes[frame] = search_bbox

                        else:

                            all_search_x0 = [b[0] for b in all_search_bboxes[ref_frame+1:ref_end] if not(b is None)]
                            median_x0 = np.median(all_search_x0)
                            IQR_x0 = np.quantile(all_search_x0, 0.75) - np.quantile(all_search_x0, 0.25)
                            all_search_x0 = [x for x in all_search_x0 if (x>=median_x0-(1.5*IQR_x0)) and (x<=median_x0+(1.5*IQR_x0))]
                            min_search_x0 = min(all_search_x0)
                            max_search_x0 = max(all_search_x0)

                            all_search_y0 = [b[1] for b in all_search_bboxes[ref_frame+1:ref_end] if not(b is None)]
                            median_y0 = np.median(all_search_y0)
                            IQR_y0 = np.quantile(all_search_y0, 0.75) - np.quantile(all_search_y0, 0.25)
                            all_search_y0 = [y for y in all_search_y0 if (y>=median_y0-(1.5*IQR_y0)) and (y<=median_y0+(1.5*IQR_y0))]
                            min_search_y0 = min(all_search_y0)
                            max_search_y0 = max(all_search_y0)

                            search_x0 = min_search_x0
                            search_y0 = min_search_y0
                            search_w = (max_search_x0-min_search_x0) + int(ref_bbox[2]+(2*search_margin))
                            search_h = (max_search_y0-min_search_y0) + int(previous_bbox[3]+(2*search_margin))
                            search_bbox = (search_x0, search_y0, search_w, search_h)
                            search_region = full_frame[search_y0:search_y0+search_h,
                                                        search_x0:search_x0+search_w]    

                            
                        mean_corr, max_loc = mc.compute_similarity_map(search_region, ref_patches, ref_idx)
                        corr_with_ref[frame] = mean_corr
                        

                        if mean_corr >= threshold:
                            valid = True
                            current_w = ref_bbox[2]
                            current_h = ref_bbox[3]
                            current_x0 = search_x0 + max_loc[0]
                            current_y0 = search_y0 + max_loc[1]
                            current_bbox = (current_x0, current_y0, current_w, current_h)

                            img_bbox = cv2.rectangle(cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                                        (search_x0, search_y0),
                                                        (search_x0+search_w, search_y0+search_h),
                                                        (255, 255, 255), 2)
                            img_bbox = cv2.rectangle(img_bbox,
                                                        (current_bbox[0], current_bbox[1]),
                                                        (current_bbox[0] + current_bbox[2], current_bbox[1] + current_bbox[3]),
                                                        (0, 255, 0), 2)
                            # img_bbox = cv2.putText(img_bbox, 'frame: '+str(frame), (25,25), cv2.FONT_HERSHEY_SIMPLEX,  
                            #             1, (0,255,0), 2, cv2.LINE_AA) 
                            # img_bbox = cv2.putText(img_bbox, 'corr: '+str(mean_corr), (25,50), cv2.FONT_HERSHEY_SIMPLEX,  
                            #             1, (0,255,0), 2, cv2.LINE_AA) 

                            out_array[frame] = img_bbox

                            #####################################
                            all_lesion_bboxes[frame] = current_bbox[:]
                            previous_bbox = current_bbox[:]
                            

                        else:
                            valid = False
                            img_bbox = cv2.rectangle(cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                                        (search_x0, search_y0),
                                                        (search_x0+search_w, search_y0+search_h),
                                                        (255, 0, 0), 2)
                            # img_bbox = cv2.putText(img_bbox, 'frame: '+str(frame), (25,25), cv2.FONT_HERSHEY_SIMPLEX,  
                            #             1, (255,0,0), 2, cv2.LINE_AA) 
                            # img_bbox = cv2.putText(img_bbox, 'corr: '+str(mean_corr), (25,50), cv2.FONT_HERSHEY_SIMPLEX,  
                            #             1, (255,0,0), 2, cv2.LINE_AA) 

                            out_array[frame] = img_bbox
                    #########################################################
                    
                    
                    #backward tracking
                    ##############################################################
                    if ref_frame > ref_begin:  
                        #print('backward tracking')

                        previous_bbox = ref_bbox

                        valid = True

                        for frame in range(ref_frame-1, ref_begin-1, -step):

                            full_frame = self.fullGrayArray[frame]

                            if valid:
                                search_w = int(previous_bbox[2]+(2*search_margin))
                                search_h = int(previous_bbox[3]+(2*search_margin))
                                search_x0 = int(previous_bbox[0] - ((search_w - previous_bbox[2])/2))
                                search_y0 = int(previous_bbox[1] - ((search_h - previous_bbox[3])/2))
                                search_bbox = (search_x0, search_y0, search_w, search_h)
                                search_region = full_frame[search_y0:search_y0+search_h,
                                                        search_x0:search_x0+search_w]

                                all_search_bboxes[frame] = search_bbox

                            else:

                                all_search_x0 = [b[0] for b in all_search_bboxes[ref_begin:ref_frame] if not(b is None)]
                                median_x0 = np.median(all_search_x0)
                                IQR_x0 = np.quantile(all_search_x0, 0.75) - np.quantile(all_search_x0, 0.25)
                                all_search_x0 = [x for x in all_search_x0 if (x>=median_x0-(1.5*IQR_x0)) and (x<=median_x0+(1.5*IQR_x0))]
                                min_search_x0 = min(all_search_x0)
                                max_search_x0 = max(all_search_x0)

                                all_search_y0 = [b[1] for b in all_search_bboxes[ref_begin:ref_frame] if not(b is None)]
                                median_y0 = np.median(all_search_y0)
                                IQR_y0 = np.quantile(all_search_y0, 0.75) - np.quantile(all_search_y0, 0.25)
                                all_search_y0 = [y for y in all_search_y0 if (y>=median_y0-(1.5*IQR_y0)) and (y<=median_y0+(1.5*IQR_y0))]
                                min_search_y0 = min(all_search_y0)
                                max_search_y0 = max(all_search_y0)

                                search_x0 = min_search_x0
                                search_y0 = min_search_y0
                                search_w = (max_search_x0-min_search_x0) + int(ref_bbox[2]+(2*search_margin))
                                search_h = (max_search_y0-min_search_y0) + int(previous_bbox[3]+(2*search_margin))
                                search_bbox = (search_x0, search_y0, search_w, search_h)
                                search_region = full_frame[search_y0:search_y0+search_h,
                                                            search_x0:search_x0+search_w]    

                                
                            mean_corr, max_loc = mc.compute_similarity_map(search_region, ref_patches, ref_idx)
                            corr_with_ref[frame] = mean_corr
                            

                            if mean_corr >= threshold:
                                valid = True 
                                current_w = ref_bbox[2]
                                current_h = ref_bbox[3]
                                current_x0 = search_x0 + max_loc[0]
                                current_y0 = search_y0 + max_loc[1]
                                current_bbox = (current_x0, current_y0, current_w, current_h)

                                img_bbox = cv2.rectangle(cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                                            (search_x0, search_y0),
                                                            (search_x0+search_w, search_y0+search_h),
                                                            (255, 255, 255), 2)
                                img_bbox = cv2.rectangle(img_bbox,
                                                            (current_bbox[0], current_bbox[1]),
                                                            (current_bbox[0] + current_bbox[2], current_bbox[1] + current_bbox[3]),
                                                            (0, 255, 0), 2)
                                # img_bbox = cv2.putText(img_bbox, 'frame: '+str(frame), (25,25), cv2.FONT_HERSHEY_SIMPLEX,  
                                #             1, (0,255,0), 2, cv2.LINE_AA) 
                                # img_bbox = cv2.putText(img_bbox, 'corr: '+str(mean_corr), (25,50), cv2.FONT_HERSHEY_SIMPLEX,  
                                #             1, (0,255,0), 2, cv2.LINE_AA) 

                                out_array[frame] = img_bbox

                                #####################################
                                all_lesion_bboxes[frame] = current_bbox[:]
                                previous_bbox = current_bbox[:]
                                

                            else:
                                valid = False
                                img_bbox = cv2.rectangle(cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                                            (search_x0, search_y0),
                                                            (search_x0+search_w, search_y0+search_h),
                                                            (255, 0, 0), 2)
                                # img_bbox = cv2.putText(img_bbox, 'frame: '+str(frame), (25,25), cv2.FONT_HERSHEY_SIMPLEX,  
                                #             1, (255,0,0), 2, cv2.LINE_AA) 
                                # img_bbox = cv2.putText(img_bbox, 'corr: '+str(mean_corr), (25,50), cv2.FONT_HERSHEY_SIMPLEX,  
                                #             1, (255,0,0), 2, cv2.LINE_AA) 

                                out_array[frame] = img_bbox
                    #########################################################
                    

            #check if lesion bbox in any frame move in this iteration
            #####################
            bbox_move = mc.check_bbox_move(previous_all_lesion_bboxes, all_lesion_bboxes)
            if bbox_move or (threshold < min([e for e in corr_with_ref if not(e is None)])):
                break
            #####################

            previous_all_lesion_bboxes = all_lesion_bboxes[:]
            previous_out_array = out_array.copy()
            threshold -= threshold_decrease_per_step
            iteration += 1

        try:
            self.mcResultsArray = previous_out_array        
        except:
            print("MC not possible. Must choose a better ROI")
        self.bboxes = previous_all_lesion_bboxes
        self.ref_frames = ref_frames

        self.updateIm()
        self.acceptGeneratedRoiButton.setHidden(False)
        self.drawRoiButton.setHidden(True)
        self.backFromDrawButton.setHidden(True)
        self.undoRoiButton.setHidden(False)
        self.undoLastPtButton.setHidden(True)
        self.redrawRoiButton.setHidden(True)
        self.fitToRoiButton.setHidden(True)
        self.roiFitNoteLabel.setHidden(True)
        self.saveRoiButton.setHidden(True)
        self.acceptGeneratedRoiButton.setCheckable(False)
        self.undoRoiButton.setCheckable(False)
        self.acceptGeneratedRoiButton.clicked.connect(self.moveToTic)
        self.undoRoiButton.clicked.connect(self.restartRoi)
        self.update()

    def backFromLoad(self):
        self.preLoadedRoiButton.setHidden(True)
        self.chooseRoiButton.setHidden(True)
        self.backFromLoadButton.setHidden(True)
        self.loadRoiButton.setHidden(False)
        self.newRoiButton.setHidden(False)

    def backFromDraw(self):
        self.curPointsPlottedX = []
        self.curPointsPlottedY = []
        self.pointsPlotted = []
        self.maskCoverImg.fill(0)
        self.drawRoiButton.setHidden(True)
        self.saveRoiButton.setHidden(True)
        self.undoLastPtButton.setHidden(True)
        self.closeRoiButton.setHidden(True)
        self.redrawRoiButton.setHidden(True)
        self.fitToRoiButton.setHidden(True)
        self.backFromDrawButton.setHidden(True)
        self.roiFitNoteLabel.setHidden(True)
        self.drawRoiButton.setCheckable(True)
        self.drawRoiButton.setChecked(False)

        self.newRoiButton.setHidden(False)
        self.loadRoiButton.setHidden(False)
        self.updateIm()

    def restartRoi(self):
        if self.niftiSegPath is None:
            self.mcResultsArray = []
            self.mcImDisplayLabel.clear()
            self.drawRoiButton.setHidden(False)
            self.backFromDrawButton.setHidden(False)
            self.undoLastPtButton.setHidden(False)
            self.redrawRoiButton.setHidden(False)
            self.fitToRoiButton.setHidden(False)
            self.acceptGeneratedRoiButton.setHidden(True)
            self.undoRoiButton.setHidden(True)
            self.roiFitNoteLabel.setHidden(False)
        else:
            self.acceptGeneratedRoiButton.setHidden(True)
            self.undoRoiButton.setHidden(True)
            self.loadRoiButton.setHidden(False)
            self.newRoiButton.setHidden(False)
            self.maskCoverImg.fill(0)
        self.updateIm()
        self.update()

    def curSliceSpinBoxValueChanged(self):
        self.curFrameIndex = int(self.curSliceSpinBox.value())
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.updateIm()

    def curSliceSliderValueChanged(self):
        self.curFrameIndex = int(self.curSliceSlider.value())
        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.updateIm()

    def openNiftiImage(self, bmodePath, cePath):
        bmodeFile = nib.load(bmodePath)
        ceFile = nib.load(cePath)

        bmodePixDims = bmodeFile.header['pixdim']
        cePixDims = ceFile.header['pixdim']
        # self.pixelScale = bmodePixDims[0]*bmodePixDims[1]*bmodePixDims[2] # mm^3

        self.bmode = bmodeFile.get_fdata(caching='unchanged')
        self.contrastEnhanced = ceFile.get_fdata(caching='unchanged')
        print(self.bmode.shape)
        print(self.contrastEnhanced.shape)
        self.bmode = self.bmode.reshape((self.bmode.shape[0], self.bmode.shape[1], self.bmode.shape[2], self.bmode.shape[4]))
        self.contrastEnhanced = self.contrastEnhnaced.reshape((self.contrastEnhanced.shape[0], self.contrastEnhanced.shape[1], self.contrastEnhanced.shape[2], self.contrastEnhanced.shape[4]))

        self.bmode = np.mean(self.bmode, axis=3)
        self.contrastEnhanced = np.mean(self.contrastEnhanced, axis=3)

    def openDicomImage(self, index, xcel_dir):  

        self.CE_side = self.df.loc[self.xcelIndices[index], 'CE_window_left(l)_or_right(r)']
        self.cineRate = self.df.loc[self.xcelIndices[index], 'CineRate']
        self.index = index
        self.xcel_dir = xcel_dir

        self.fullPath = os.path.join(xcel_dir, self.df.loc[self.xcelIndices[index], 'cleaned_path'])
        ds = dicom.dcmread(self.fullPath)
        ar = ds.pixel_array

        color_channel = ds.PhotometricInterpretation
        self.fullArray, self.fullGrayArray = load_cine(ar, color_channel)
        self.x = self.fullArray.shape[2]
        self.y = self.fullArray.shape[1]
        self.numSlices = self.fullArray.shape[0]

        self.x0_bmode, self.x0_CE, self.w_bmode, self.w_CE = find_x0_bmode_CE(ds, self.CE_side, ar.shape[2])
        manufacturer = ds.Manufacturer
        model = ds.ManufacturerModelName
        imBoundariesPath = os.path.join('CeusMcTool2d', 'imBoundaries.json')

        try:
            self.y0_bmode = int(ds.SequenceOfUltrasoundRegions[0].RegionLocationMinY0)
            self.h_bmode = int(ds.SequenceOfUltrasoundRegions[0].RegionLocationMaxY1 - ds.SequenceOfUltrasoundRegions[0].RegionLocationMinY0 + 1)
            with open(imBoundariesPath, 'r') as fp:
                imDimsHashTable = json.load(fp)
            try:
                relativeImDims = imDimsHashTable[', '.join((manufacturer, model))]
            except:
                imDimsHashTable[', '.join((manufacturer, model))] = [self.x0_bmode/self.x, self.y0_bmode/self.y, self.w_bmode/self.x, self.h_bmode/self.y]
                os.remove(imBoundariesPath)
                with open(imBoundariesPath, 'w') as fp:
                    json.dump(imDimsHashTable, fp, sort_keys=True, indent=4)
        except:
            with open(imBoundariesPath, 'r') as fp:
                imDimsHashTable = json.load(fp)
            try:
                relativeImDims = imDimsHashTable[', '.join((manufacturer, model))]
            except:
                print("Transducer model and data format not supported!")
                return
            self.y0_bmode = round(relativeImDims[1]*self.y)
            self.w_bmode = round(relativeImDims[2]*self.x)
            self.h_bmode = round(relativeImDims[3]*self.y)
            self.x0_bmode = round(relativeImDims[0]*self.x)
            if self.CE_side == 'r':
                self.x0_CE = self.x0_bmode + self.w_bmode
            else:
                self.x0_CE = self.x0_bmode - self.w_bmode # assumes CE and bmode have same width
            self.w_CE = self.w_bmode
        self.y0_CE = self.y0_bmode
        self.h_CE = self.h_bmode

        self.imX0 = 350
        self.imX1 = 1151
        self.imY0 = 80
        self.imY1 = 561
        xLen = self.imX1 - self.imX0
        yLen = self.imY1 - self.imY0

        quotient = self.x / self.y
        if quotient > (xLen/yLen):
            self.widthScale = xLen
            self.depthScale = int(self.widthScale / quotient)
            emptySpace = yLen - self.depthScale
            yBuffer = int(emptySpace/2)
            self.imY0 += yBuffer
            self.imY1 -= yBuffer
        else:
            self.widthScale = int(yLen * quotient)
            self.depthScale = yLen
            emptySpace = xLen - self.widthScale
            xBuffer = int(emptySpace/2)
            self.imX0 += xBuffer
            self.imX1 -= xBuffer
        self.imPlane.move(self.imX0, self.imY0)
        self.imPlane.resize(self.widthScale, self.depthScale)  
        self.imMaskLayer.move(self.imX0, self.imY0)
        self.imMaskLayer.resize(self.widthScale, self.depthScale)
        self.imCoverLabel.move(self.imX0, self.imY0)
        self.imCoverLabel.resize(self.widthScale, self.depthScale)
        self.mcImDisplayLabel.move(self.imX0, self.imY0)
        self.mcImDisplayLabel.resize(self.widthScale, self.depthScale)

        self.imCoverPixmap = QPixmap(self.widthScale, self.depthScale)
        self.imCoverPixmap.fill(Qt.transparent)
        self.imCoverLabel.setPixmap(self.imCoverPixmap)

        painter = QPainter(self.imCoverLabel.pixmap())
        self.imCoverLabel.pixmap().fill(Qt.transparent)
        painter.setPen(Qt.yellow)
        xScale = self.widthScale/self.x
        yScale = self.depthScale/self.y
        self.bmodeStartX = self.imX0 + int(xScale*self.x0_bmode)
        self.bmodeEndX = self.bmodeStartX + int(xScale*self.w_bmode)
        self.bmodeStartY = self.imY0 + int(yScale*self.y0_bmode)
        self.bmodeEndY = self.bmodeStartY + int(yScale*self.h_bmode)
        self.ceStartX = self.imX0 + int(xScale*self.x0_CE)
        self.ceEndX = self.ceStartX + int(xScale*self.w_CE)
        self.ceStartY = self.imY0 + int(yScale*self.y0_CE)
        self.ceEndY = self.ceStartY + int(yScale*self.h_CE)
        painter.drawRect(int(self.x0_bmode*xScale), int(self.y0_bmode*yScale), int(self.w_bmode*xScale), int(self.h_bmode*yScale))
        painter.drawRect(int(self.x0_CE*xScale), int(self.y0_CE*yScale), int(self.w_CE*xScale), int(self.h_CE*yScale))
        painter.end()
        self.update()

        # self.bmode = self.fullArray[:,self.y0_bmode:self.y0_bmode+self.h_bmode, \
        #                              self.x0_bmode:self.x0_bmode+self.w_bmode]
        
        # self.contrastEnhanced = self.fullArray[:, self.y0_CE:self.y0_CE+self.h_CE, \
        #                                         self.x0_CE:self.x0_CE+self.w_CE]
        
        # self.x = self.w_bmode
        # self.y = self.h_bmode

        # ceSide = self.df.loc[self.xcelIndices[index], 'CE_window_left(l)_or_right(r)']
        # if ceSide == 'r':
        #     self.bmode = self.fullArray[:,:,:int(self.fullArray.shape[2]/2)]
        #     self.contrastEnhanced = self.fullArray[:,:,int(self.fullArray.shape[2]/2):]
        #     self.x0_bmode = 0
        #     self.x0_CE = int(self.fullArray.shape[2]/2)
        # else:
        #     self.bmode = self.fullArray[:,:,int(self.fullArray.shape[2]/2):]
        #     self.contrastEnhanced = self.fullArray[:,:,:int(self.fullArray.shape[2]/2)]
        #     self.x0_bmode = int(self.fullArray.shape[2]/2)
        #     self.x0_CE = 0
        # self.numSlices = self.bmode.shape[0]
        # self.x = self.bmode.shape[2]
        # self.y = self.bmode.shape[1]
        # self.y0_bmode = 0
        # self.y0_CE = 0

        self.maskCoverImg = np.zeros([self.y, self.x, 4])
        
        # imRegion = ds.SequenceOfUltrasoundRegions[0]
        # self.pixelScale = (imRegion.PhysicalDeltaY/self.y)*(imRegion.PhysicalDeltaX/self.x) # cm assuming imRegion.PhysicalUnitsXDirection == 3
        # self.pixelScale *= 100 # cm^2 -> mm^2
        # print("imRegion.PhysicalUnitsXDirection:", imRegion.PhysicalUnitsXDirection)

        self.curSliceSlider.setMaximum(self.numSlices - 1)
        self.curSliceSpinBox.setMaximum(self.numSlices - 1)

        self.sliceArray = np.round([i*(1/self.cineRate) for i in range(self.numSlices)], decimals=2)
        # self.totalSecondsLabel.setText(str(self.sliceArray[-1]))

        self.curSliceTotal.setText(str(self.numSlices-1))

        self.curSliceSpinBox.setValue(self.sliceArray[self.curFrameIndex])
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)

        self.drawRoiButton.setCheckable(True)

        self.updateIm()

        #getting initial image data for bmode and CE
        # self.dataBmode = self.bmode[self.curFrameIndex]
        # self.dataBmode = np.require(self.dataBmode, np.uint8, 'C')
        # self.dataCE = self.contrastEnhanced[self.curFrameIndex]
        # self.dataCE = np.require(self.dataCE, np.uint8, 'C')
        # self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, 'C')
        
        # self.bytesLineMask, _ = self.maskCoverImg[:,:,0].strides
        # self.bytesLineBmode, _ = self.dataBmode.strides #in order to create proper QImage, need to know bytes/line
        # self.bytesLineCE, _ = self.dataCE.strides

        # self.qImgBmode = QImage(self.dataBmode, self.x, self.y, self.bytesLineBmode, QImage.Format_Grayscale8) #creating QImage
        # self.qImgCE = QImage(self.dataCE, self.x, self.y, self.bytesLineCE, QImage.Format_Grayscale8)
        # self.qImgMask = QImage(self.maskCoverImg, self.x, self.y, self.bytesLineMask, QImage.Format_ARGB32)
        # self.qImgMask.mirrored().save(os.path.join("Junk", "bModeImRaw.png")) # Save as .png file

        # self.bmodePlane.setPixmap(QPixmap.fromImage(self.qImgBmode).scaled(381, 351))
        # self.cePlane.setPixmap(QPixmap.fromImage(self.qImgCE).scaled(381, 351))
        # self.bmodeMaskLayer.setPixmap(QPixmap.fromImage(self.qImgMask).scaled(381, 351))
        # self.ceMaskLayer.setPixmap(QPixmap.fromImage(self.qImgMask).scaled(381, 351))

        self.closeRoiButton.clicked.connect(self.acceptPolygon) #called to exit the paint function
        self.undoLastPtButton.clicked.connect(self.undoLastPoint) #deletes last drawn rectangle if on sag or cor slices

        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.drawRoiButton.clicked.connect(self.startRoiDraw)

    def updateIm(self):
        if len(self.mcResultsArray):
            self.mcData = np.require(self.mcResultsArray[self.curFrameIndex], np.uint8, 'C')
            self.bytesLineMc, _ = self.mcData[:,:,0].strides
            self.qImgMc = QImage(self.mcData, self.x, self.y, self.bytesLineMc, QImage.Format_RGB888)
            self.mcImDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMc).scaled(self.widthScale, self.depthScale))
        else:
            self.imData = self.fullArray[self.curFrameIndex]
            self.imData = np.require(self.imData, np.uint8, 'C')
            self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, 'C')
            self.bytesLineIm, _ = self.imData[:,:,0].strides
            self.bytesLineMask, _ = self.maskCoverImg[:,:,0].strides
            self.qImg = QImage(self.imData, self.x, self.y, self.bytesLineIm, QImage.Format_RGB888)
            self.qImgMask = QImage(self.maskCoverImg, self.x, self.y, self.bytesLineMask, QImage.Format_ARGB32)

            self.imPlane.setPixmap(QPixmap.fromImage(self.qImg).scaled(self.widthScale, self.depthScale))
            self.imMaskLayer.setPixmap(QPixmap.fromImage(self.qImgMask).scaled(self.widthScale, self.depthScale))

    # def updateBmode(self):
    #     if len(self.mcResultsBmode):
    #         self.mcDataBmode = np.require(self.mcResultsBmode[self.curFrameIndex], np.uint8, 'C')
    #         self.bytesLineMc, _ = self.mcDataBmode[:,:,0].strides
    #         self.qImgMcBmode = QImage(self.mcDataBmode, self.x, self.y, self.bytesLineMc, QImage.Format_RGB888)
    #         self.mcBmodeDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMcBmode).scaled(self.widthScale, self.heightScale))
    #     else:
    #         self.dataBmode = self.bmode[self.curFrameIndex]
    #         self.dataBmode = np.require(self.dataBmode, np.uint8, 'C')
    #         self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, 'C')

    #         self.bytesLineBmode, _ = self.dataBmode.strides
    #         self.bytesLineMask, _ = self.maskCoverImg[:,:,0].strides
    #         self.qImgBmode = QImage(self.dataBmode, self.x, self.y, self.bytesLineBmode, QImage.Format_Grayscale8)
    #         self.qImgMask = QImage(self.maskCoverImg, self.x, self.y, self.bytesLineMask, QImage.Format_ARGB32)

    #         self.bmodePlane.setPixmap(QPixmap.fromImage(self.qImgBmode).scaled(381, 351))
    #         self.bmodeMaskLayer.setPixmap(QPixmap.fromImage(self.qImgMask).scaled(381, 351))

    # def updateCE(self):
    #     if len(self.mcResultsCE):
    #         self.mcDataCE = np.require(self.mcResultsCE[self.curFrameIndex], np.uint8, 'C')
    #         self.bytesLineMc, _ = self.mcDataCE.strides
    #         self.qImgMcCE = QImage(self.mcDataCE, self.x, self.y, self.bytesLineMc, QImage.Format_Grayscale8)
    #         self.mcCeDisplayLabel.setPixmap(QPixmap.fromImage(self.qImgMcCE).scaled(381, 351))
    #     else:
    #         self.dataCE = self.contrastEnhanced[self.curFrameIndex]
    #         self.dataCE = np.require(self.dataCE, np.uint8, 'C')
    #         self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, 'C')

    #         self.bytesLineCE, _ = self.dataCE.strides
    #         self.bytesLineMask, _ = self.maskCoverImg[:,:,0].strides
    #         self.qImgCE = QImage(self.dataCE, self.x, self.y, self.bytesLineCE, QImage.Format_Grayscale8)
    #         self.qImgMask = QImage(self.maskCoverImg, self.x, self.y, self.bytesLineMask, QImage.Format_ARGB32)


    #         self.cePlane.setPixmap(QPixmap.fromImage(self.qImgCE).scaled(381, 351))
    #         self.ceMaskLayer.setPixmap(QPixmap.fromImage(self.qImgMask).scaled(381, 351))

    def updateCrosshair(self):
        if self.xCur < self.imX1 and self.xCur > self.imX0 and self.yCur < self.imY1 and self.yCur > self.imY0:
            self.actualX = int((self.xCur - self.imX0 - 1)*(self.y-1)/self.widthScale)
            self.actualY = int((self.yCur - self.imY0 - 1)*(self.x-1)/self.depthScale)
            plotX = self.xCur - self.imX0 - 1
        # elif self.xCur < 1151 and self.xCur > 770 and self.yCur < 501 and self.yCur > 150:
        #     self.actualX = int((self.xCur-771)*(self.y-1)/381)
        #     self.actualY = int((self.yCur-151)*(self.x-1)/351)
        #     plotX = self.xCur - 771
        else:
            return
        
        plotY = self.yCur - self.imY0 - 1

        # self.bmodeCoverLabel.pixmap().fill(Qt.transparent)
        self.imCoverLabel.pixmap().fill(Qt.transparent)
        # painter = QPainter(self.bmodeCoverLabel.pixmap())
        painter = QPainter(self.imCoverLabel.pixmap())
        painter.setPen(Qt.yellow)
        bmodeVertLine = QLine(plotX, 0, plotX, self.depthScale)
        bmodeLatLine = QLine(0, plotY, self.widthScale, plotY)
        painter.drawLines([bmodeVertLine, bmodeLatLine])
        painter.end()
            
        # self.ceCoverLabel.pixmap().fill(Qt.transparent)
        # painter = QPainter(self.ceCoverLabel.pixmap())
        # painter.setPen(Qt.yellow)
        # ceVertLine = QLine(plotX, 0, plotX, 351)
        # ceLatLine = QLine(0, plotY, 381, plotY)
        # painter.drawLines([ceVertLine, ceLatLine])
        # painter.end()
        self.update()

    def updateSpline(self):
        if len(self.curPointsPlottedX) > 0:
            if self.spline != None:
                self.spline.remove()
            
            if len(self.curPointsPlottedX) > 1:
                points = [(self.curPointsPlottedX[i], self.curPointsPlottedY[i]) for i in range(len(self.curPointsPlottedX))]
                self.curPointsPlottedX, self.curPointsPlottedY = np.transpose(removeDuplicates(points))
                self.curPointsPlottedX = list(self.curPointsPlottedX)
                self.curPointsPlottedY = list(self.curPointsPlottedY)
                xSpline, ySpline = calculateSpline(self.curPointsPlottedX, self.curPointsPlottedY)
                spline = [(int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))]
                spline = np.array([*set(spline)])
                xSpline, ySpline = np.transpose(spline)
                if self.imDrawn == 1:
                    xSpline = np.clip(xSpline, a_min=self.x0_bmode+1, a_max=self.x0_bmode+self.w_bmode-2)
                    ySpline = np.clip(ySpline, a_min=self.y0_bmode+1, a_max=self.y0_bmode+self.h_bmode-2)
                elif self.imDrawn == 2:
                    xSpline = np.clip(xSpline, a_min=self.x0_CE+1, a_max=self.x0_CE+self.w_CE-2)
                    ySpline = np.clip(ySpline, a_min=self.y0_CE+1, a_max=self.y0_CE+self.h_CE-2)
                else:
                    xSpline = np.clip(xSpline, a_min=1, a_max=self.x-2)
                    ySpline = np.clip(ySpline, a_min=1, a_max=self.y-2)
                # for point in self.oldSpline:
                #     self.maskCoverImg[point[0], point[1]] = [0,0,0,0]
                self.maskCoverImg.fill(0)
                self.oldSpline = []
                for i in range(len(xSpline)):
                    self.maskCoverImg[ySpline[i]-1:ySpline[i]+2, xSpline[i]-1:xSpline[i]+2] = [255, 255, 0, 255]
                    # for j in range(3):
                    #     for k in range(3):
                    #         self.oldSpline.append([ySpline[i]-j-1, xSpline[i]-k-1])
            else:
                self.maskCoverImg.fill(0)
                self.oldSpline = []
            for i in range(len(self.curPointsPlottedX)):
                self.maskCoverImg[self.curPointsPlottedY[i]-2:self.curPointsPlottedY[i]+3, \
                                    self.curPointsPlottedX[i]-2:self.curPointsPlottedX[i]+3] = [0,0,255, 255]
        else:
            self.maskCoverImg.fill(0)
            self.oldSpline = []

        self.updateIm()
        # self.updateCrosshair()

    def mousePressEvent(self,event):
        self.xCur = event.x()
        self.yCur = event.y()
        if self.drawRoiButton.isChecked():
            # Plot ROI points
            # if self.xCur < self.imX1 and self.xCur > self.imX0 and self.yCur < self.imY1 and self.yCur > self.imY0:
            #     self.actualX = int((self.xCur - self.imX0 - 1)*(self.y-1)/self.depthScale)
            #     self.actualY = int((self.yCur - self.imY0 - 1)*(self.x-1)/self.widthScale)
            if self.imDrawn != 2 and self.xCur < self.bmodeEndX and self.xCur > self.bmodeStartX and self.yCur < self.bmodeEndY and self.yCur > self.bmodeStartY:
                # self.actualX = int((self.xCur - self.bmodeStartX - 1)*(self.h_bmode - 1)/(self.bmodeEndY - self.bmodeStartY))
                # self.actualY = int((self.yCur - self.bmodeStartY - 1)*(self.w_bmode - 1)/(self.bmodeEndX - self.bmodeStartX))
                self.actualX = int((self.xCur - self.imX0 - 1)*(self.y-1)/self.depthScale)
                self.actualY = int((self.yCur - self.imY0 - 1)*(self.x-1)/self.widthScale)
                self.imDrawn = 1
            elif self.imDrawn != 1 and self.xCur < self.ceEndX and self.xCur > self.ceStartX and self.yCur < self.ceEndY and self.yCur > self.ceStartY:
                # self.actualX = int((self.xCur - self.ceStartX - 1)*(self.h_CE - 1)/(self.ceEndY - self.ceStartY))
                # self.actualY = int((self.yCur - self.ceStartY - 1)*(self.w_CE - 1)/(self.ceEndX - self.ceStartX))
                self.actualX = int((self.xCur - self.imX0 - 1)*(self.y-1)/self.depthScale)
                self.actualY = int((self.yCur - self.imY0 - 1)*(self.x-1)/self.widthScale)
                self.imDrawn = 2
            else:
                return
            self.curPointsPlottedX.append(self.actualX)
            self.curPointsPlottedY.append(self.actualY)
            self.updateSpline()

    def mouseMoveEvent(self, event):
        self.xCur = event.x()
        self.yCur = event.y()
        # self.updateCrosshair()

    
    def acceptPolygon(self):
        # 2d interpolation
        if len(self.curPointsPlottedX) > 2:
            self.drawRoiButton.setChecked(False)

            # remove duplicate points
            points = np.transpose(np.array([self.curPointsPlottedX, self.curPointsPlottedY]))
            points = removeDuplicates(points)
            [self.curPointsPlottedX, self.curPointsPlottedY] = np.transpose(points)
            self.curPointsPlottedX = list(self.curPointsPlottedX)
            self.curPointsPlottedY = list(self.curPointsPlottedY)
            self.curPointsPlottedX.append(self.curPointsPlottedX[0])
            self.curPointsPlottedY.append(self.curPointsPlottedY[0])
            self.maskCoverImg.fill(0)

            xSpline, ySpline = calculateSpline(self.curPointsPlottedX, self.curPointsPlottedY)
            spline = [(int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))]
            spline = np.array([*set(spline)])
            xSpline, ySpline = np.transpose(spline)
            if self.imDrawn == 1:
                xSpline = np.clip(xSpline, a_min=self.x0_bmode+1, a_max=self.x0_bmode+self.w_bmode-2)
                ySpline = np.clip(ySpline, a_min=self.y0_bmode+1, a_max=self.y0_bmode+self.h_bmode-2)
            elif self.imDrawn == 2:
                xSpline = np.clip(xSpline, a_min=self.x0_CE+1, a_max=self.x0_CE+self.w_CE-2)
                ySpline = np.clip(ySpline, a_min=self.y0_CE+1, a_max=self.y0_CE+self.h_CE-2)
            else:
                xSpline = np.clip(xSpline, a_min=1, a_max=self.x-2)
                ySpline = np.clip(ySpline, a_min=1, a_max=self.y-2)
            self.oldSpline = []
            for i in range(len(xSpline)):
                self.maskCoverImg[ySpline[i]-1:ySpline[i]+2, xSpline[i]-1:xSpline[i]+2] = [0, 0, 255, 255]
                for j in range(3):
                    self.pointsPlotted.append((xSpline[i]-j, ySpline[i]-j))
                    if not j:
                        self.pointsPlotted.append((xSpline[i]+j, ySpline[i]+j))
            self.curPointsPlottedX = []
            self.curPointsPlottedY = []
            self.redrawRoiButton.setHidden(False)
            self.closeRoiButton.setHidden(True)
            self.undoLastPtButton.setHidden(True)
            self.saveRoiButton.setHidden(False)
            self.roiFitNoteLabel.setHidden(False)
            self.drawRoiButton.setChecked(False)
            self.drawRoiButton.setCheckable(False)
            self.fitToRoiButton.clicked.connect(self.perform_MC)
            self.updateIm()
            # self.updateCrosshair()

            

    def undoLastPoint(self):
        if len(self.curPointsPlottedX) and (not len(self.pointsPlotted)):
            self.maskCoverImg[self.curPointsPlottedY[-1]-2:self.curPointsPlottedY[-1]+3, \
                              self.curPointsPlottedX[-1]-2:self.curPointsPlottedX[-1]+3] = [0,0,0,0]
            self.curPointsPlottedX.pop()
            self.curPointsPlottedY.pop()
            self.updateSpline()
        if not len(self.curPointsPlottedX):
            self.imDrawn = 0


    def startRoiDraw(self):
        if self.drawRoiButton.isChecked():
            self.closeRoiButton.setHidden(False)
            self.redrawRoiButton.setHidden(True)
        elif not len(self.curPointsPlottedX):
            self.closeRoiButton.setHidden(True)
            self.redrawRoiButton.setHidden(False)

    def undoLastRoi(self):
        if len(self.pointsPlotted) > 0:
            self.pointsPlotted = []
            self.maskCoverImg.fill(0)
            self.redrawRoiButton.setHidden(True)
            self.closeRoiButton.setHidden(False)
            self.roiFitNoteLabel.setHidden(True)
            self.drawRoiButton.setCheckable(True)
            self.saveRoiButton.setHidden(True)
            self.undoLastPtButton.setHidden(False)
            self.imDrawn = 0
            try:
                self.fitToRoiButton.clicked.disconnect()
            except:
                pass
            self.updateIm()
            self.update()

    def computeTic(self):
        times = np.array([i*(1/self.cineRate) for i in range(self.numSlices)])
        mcResultsCE = self.fullGrayArray[:, self.y0_CE:self.y0_CE+self.h_CE, self.x0_CE:self.x0_CE+self.w_CE]
        bboxes = self.bboxes.copy()
        for i in range(len(bboxes)):
            if bboxes[i] is not None:
                bboxes[i] = (bboxes[i][0]-self.x0_bmode, bboxes[i][1]-self.y0_bmode, bboxes[i][2], bboxes[i][3]) # assumes bmode and CEUS images are same size
        #         self.mcResultsArray[i, self.y0_CE + bboxes[i][1]: self.y0_CE + bboxes[i][1] + self.bboxes[i][3], self.x0_CE + bboxes[i][0]: self.x0_CE + bboxes[i][0] + bboxes[i][3]] = [255, 0, 0]
        # self.updateIm()
        # return
        TIC, self.ticAnalysisGui.roiArea = mc.generate_TIC_no_TMPPV(mcResultsCE, bboxes, times, 24.09, self.ref_frames[0])
        TIC[:,1] /= np.amax(TIC[:,1])
        # # Compute TICs

        # # resize all MC bboxes to same size
        # self.bboxes = mc.resize_mc_bboxes(self.bboxes)

        # # remove outlier bboxes
        # self.bboxes = mc.remove_outlier_bboxes(self.bboxes)

        # self.ceMcBboxes = mc.create_ce_mc_bboxes(self.bboxes, self.x0_bmode, self.x0_CE, self.CE_side)

        # self.ceMcRoi = mc.cut_ROI200(self.fullArray, self.ceMcBboxes, (self.x0_CE, self.y0_CE, self.x, self.y))

        # self.ticArray = mc.getAllTICs(self.ceMcRoi, self.pixelScale, times)
        

        # Bunch of checks
        if np.isnan(np.sum(TIC[:,1])):
            print("STOPPED: NaNs in the ROI")
            return
        if np.isinf(np.sum(TIC[:,1])):
            print("STOPPED: Infs in the ROI")
            return
        
        # self.meanTIC = np.mean(self.ticArray.reshape((self.ticArray.shape[0]*self.ticArray.shape[1], \
        #                                               self.ticArray.shape[2], self.ticArray.shape[3])), axis=0)

        # self.ticX = np.array([[self.meanTIC[i,0],i] for i in range(len(self.meanTIC[:,0]))])
        # self.ticY = self.meanTIC[:,1]
        self.ticX = np.array([[TIC[i,0],i] for i in range(len(TIC[:,0]))])
        self.ticY = TIC[:,1]
        self.ticAnalysisGui.ax.clear()
        self.ticAnalysisGui.ticX = []
        self.ticAnalysisGui.ticY = []
        # self.ticAnalysisGui.pixelScale = self.pixelScale
        self.ticAnalysisGui.removedPointsX = []
        self.ticAnalysisGui.removedPointsY = []
        self.ticAnalysisGui.selectedPoints = []
        self.ticAnalysisGui.t0Index = -1
        self.ticAnalysisGui.graph(self.ticX, self.ticY)
        self.ticAnalysisGui.ticArray = TIC

    def moveToTic(self):
        self.ticAnalysisGui.timeLine = None
        self.computeTic()
        self.ticAnalysisGui.dataFrame = self.dataFrame
        self.ticAnalysisGui.curFrameIndex = self.curFrameIndex
        self.ticAnalysisGui.mcResultsArray = self.mcResultsArray
        self.ticAnalysisGui.x = self.x
        self.ticAnalysisGui.y = self.y
        self.ticAnalysisGui.sliceArray = self.sliceArray
        self.ticAnalysisGui.lastGui = self
        self.ticAnalysisGui.x0_bmode = self.x0_bmode
        self.ticAnalysisGui.y0_bmode = self.y0_bmode
        self.ticAnalysisGui.x = self.x
        self.ticAnalysisGui.y = self.y
        self.ticAnalysisGui.x0_CE = self.x0_CE
        self.ticAnalysisGui.y0_CE = self.y0_CE
        self.ticAnalysisGui.x = self.x
        self.ticAnalysisGui.y = self.y
        self.ticAnalysisGui.setFilenameDisplays(self.imagePathInput.text())
        self.ticAnalysisGui.deSelectLastPointButton.setHidden(True)
        self.ticAnalysisGui.removeSelectedPointsButton.setHidden(True)
        self.ticAnalysisGui.restoreLastPointsButton.setHidden(True)
        self.ticAnalysisGui.acceptTicButton.setHidden(True)
        self.ticAnalysisGui.acceptT0Button.setHidden(True)
        self.ticAnalysisGui.t0Slider.setHidden(True)
        self.ticAnalysisGui.selectT0Button.setHidden(False)
        self.ticAnalysisGui.updateIm()
        self.ticAnalysisGui.show()
        self.hide()


def calculateSpline(xpts, ypts): # 2D spline interpolation
    cv = []
    for i in range(len(xpts)):
        cv.append([xpts[i], ypts[i]])
    cv = np.array(cv)
    if len(xpts) == 2:
        tck, u_ = interpolate.splprep(cv.T, s=0.0, k=1)
    elif len(xpts) == 3:
        tck, u_ = interpolate.splprep(cv.T, s=0.0, k=2)
    else:
        tck, u_ = interpolate.splprep(cv.T, s=0.0, k=3)
    x,y = np.array(interpolate.splev(np.linspace(0, 1, 1000), tck))
    return x, y

def removeDuplicates(ar):
        # Credit: https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
        seen = set()
        seen_add = seen.add
        return [x for x in ar if not (tuple(x) in seen or seen_add(tuple(x)))]
         

def find_x0_bmode_CE(ds, CE_side, width):
    if CE_side == 'r':
        try:
            print('computing x0_bmode and x0_CE by SequenceOfUltrasoundRegions')
            regions = ds.SequenceOfUltrasoundRegions
            x0_list = [int(reg.RegionLocationMinX0) for reg in regions]
            x0_bmode = min(x0_list)
            x0_CE = max(x0_list)
            w_bmode = int(regions[0].RegionLocationMaxX1) - int(regions[0].RegionLocationMinX0)
            w_CE = w_bmode
        except:
            print('computing x0_bmode and x0_CE by width/2')
            x0_bmode = 0
            x0_CE = int(width/2)
            w_bmode = int(width/2)
            w_CE = w_bmode
    elif CE_side == 'l':
        try:
            print('computing x0_bmode and x0_CE by SequenceOfUltrasoundRegions')
            regions = ds.SequenceOfUltrasoundRegions
            x0_list = [int(reg.RegionLocationMinX0) for reg in regions]
            x0_bmode = max(x0_list)
            x0_CE = min(x0_list)
            w_bmode = int(regions[0].RegionLocationMaxX1) - int(regions[0].RegionLocationMinX0)
            w_CE = w_bmode
        except:
            print('computing x0_bmode and x0_CE by width/2')
            x0_CE = 0
            x0_bmode = int(width/2)
            w_bmode = int(width/2)
            w_CE = w_bmode
    else:
        print('CE side not specified in Excel file')
        
    return x0_bmode, x0_CE, w_bmode, w_CE

def load_cine(cine_array, color_channel):
    
    #parameters:
    #    cine_array -- array from ds.pixel_array
    #    color_channel -- ds.PhotometricInterpretation
    #return:
    #    cine_array (frames, height, width, 3), gray_cine_array (frames, height, width)
    
    
    if 'MONOCHROME' in color_channel:
        if len(cine_array.shape) == 3:    #video (frames, height, width)
            cine_array = np.expand_dims(cine_array, ayis=3)
            cine_array = np.broadcast_to(cine_array, list(cine_array.shape[:-1])+[3])
        elif len(cine_array.shape) == 2:    #static image (height, width)
            cine_array = np.expand_dims(cine_array, ayis=0)
            cine_array = np.expand_dims(cine_array, ayis=3)
            cine_array = np.broadcast_to(cine_array, list(cine_array.shape[:-1])+[3])
        else:
            raise Exception("Number of channels does not match MONOCHROME color space")
    else:
        if len(cine_array.shape) == 4:    #video (frames, height, width, 3)
            pass
        elif len(cine_array.shape) == 3:    #static image (height, width, 3)
            cine_array = np.expand_dims(cine_array, axis=0)
        else:
            raise Exception("Number of channels does not match color space")
            
    #debug
    print(cine_array.shape)
    print(color_channel)
    
    #convert color channels to RGB and gray
    """
    RGB
    MONOCHROME
    YBR_FULL --> need to convert to RGB
    YBR_RCT --> no need conversion; it is actually stored as RGB
    """
    if 'YBR_FULL' in color_channel:
        if color_channel == 'YBR_FULL' or color_channel == 'YBR_FULL_422':
            cine_array = convert_color_space(cine_array, color_channel, "RGB", per_frame=True)
        else:
            #swap YBR to YRB first
            cine_array[:,:,:,:] = cine_array[:,:,:,[0,2,1]]
            #then convert from YRB to RGB using openCV
            for frame in range(cine_array.shape[0]):
                cine_array[frame,:,:,:] = cv2.cvtColor(cine_array[frame,:,:,:], cv2.COLOR_YCrCb2RGB)
        
            
    gray_cine_array = np.zeros(cine_array.shape[:-1])
    for frame in range(cine_array.shape[0]):
        gray_cine_array[frame,:,:] = cv2.cvtColor(cine_array[frame,:,:,:], cv2.COLOR_RGB2GRAY)
        
    cine_array = cine_array.astype(np.uint8)
    gray_cine_array = gray_cine_array.astype(np.uint8)
            
    return cine_array, gray_cine_array

def removeDuplicates(ar):
    # Credit: https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in ar if not (tuple(x) in seen or seen_add(tuple(x)))]


if __name__ == "__main__":
    pickle_full_path = "/Users/davidspector/Home/Stanford/MC_Sample_Code/data/P_005_021/pickle_bmode_CE_gray/ceus_inj1_wi_000000.000000.pkl"
    x0_bmode = 0
    x0_CE = 721
    y0_bmode = 40
    y0_CE = 40
    x = 721
    y = 697
    x = 721
    y = 697

    import sys
    app = QApplication(sys.argv)
    # selectWindow = QWidget()
    ui = RoiSelectionGUI()
    # ui.selectImage.show()
    ui.show()
    sys.exit(app.exec_())