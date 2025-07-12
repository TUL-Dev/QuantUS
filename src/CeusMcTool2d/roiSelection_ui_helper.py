import os
from pathlib import Path

import cv2
import numpy as np
import pydicom as dicom
import nibabel as nib
import scipy.interpolate as interpolate
from scipy.ndimage import binary_fill_holes
from pydicom.pixel_data_handlers import convert_color_space
from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog
from PyQt6.QtGui import QPixmap, QPainter, QImage, QMouseEvent
from PyQt6.QtCore import QLine, Qt

import src.Utils.motionCorrection as mc
from src.CeusMcTool2d.roiSelection_ui import Ui_constructRoi
from src.CeusMcTool2d.ticAnalysis_ui_helper import TicAnalysisGUI
from src.CeusMcTool2d.saveRoi_ui_helper import SaveRoiGUI
from src.Parsers.visualsonics2dCeus import visualsonics2dCeusParser

# Assumes no gap between images
# imDimsHashTable = {("TOSHIBA_MEC_US", "TUS-AI900"): (0.0898, 0.145, 0.410, 0.672)} #stores relative (x0_bmode, y0_bmode, w_bmode, h_bmode)


class RoiSelectionGUI(Ui_constructRoi, QWidget):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

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
        self.acceptBoundsButton.setHidden(True)
        self.horizontalSlider.setHidden(True)
        self.defImBoundsButton.setHidden(True)
        self.boundDrawLabel.setHidden(True)
        self.boundBackButton.setHidden(True)
        self.acceptConstRoiButton.setHidden(True)
        self.df = None
        self.niftiSegPath = None

        self.curFrameIndex = 0
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
        self.index = None
        self.bboxes = None
        self.ref_frames = None
        self.xcelIndices = None
        self.curLeftLineX = -1
        self.imWidth = None; self.imDepth = None

        self.imDrawn = 0
        self.axRes, self.latRes, self.cineRate, self.fullPath, self.mc = -1, -1, None, None, False

        self.setMouseTracking(True)

        self.backButton.clicked.connect(self.backToLastScreen)
        self.newRoiButton.clicked.connect(self.drawNewRoi)
        self.loadRoiButton.clicked.connect(self.startLoadRoi)
        self.saveRoiButton.clicked.connect(self.startSaveRoi)
        self.acceptConstRoiButton.clicked.connect(self.acceptRoiNoMc)
        self.backFromDrawButton.clicked.connect(self.backFromDraw)
        self.fitToRoiButton.clicked.connect(self.perform_MC)

    def startSaveRoi(self):
        try:
            del self.saveRoiGUI
        except AttributeError:
            pass
        self.saveRoiGUI = SaveRoiGUI()
        self.saveRoiGUI.roiSelectionGUI = self
        default_roi_path = Path(self.fullPath).parent / "nifti_segmentation_QUANTUS"
        default_roi_path.mkdir(parents=True, exist_ok=True)
        self.saveRoiGUI.newFolderPathInput.setText(str(default_roi_path))
        self.saveRoiGUI.newFileNameInput.setText(Path(self.fullPath).with_suffix('.nii.gz').name.replace(' ', '_'))
        self.saveRoiGUI.show()

    def saveRoi(self, fileDestination, name):  # frame):
        affine = np.eye(4)
        niiarray = nib.Nifti1Image(np.transpose(self.segMask).astype("uint8"), affine)
        niiarray.header["descrip"] = self.imagePathInput.text()
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
        fileName, _ = QFileDialog.getOpenFileName(None, "Open File", filter="*.nii.gz")
        if fileName != "":
            nibIm = nib.load(fileName)
            if (
                self.imagePathInput.text().replace("'", '"')
                == str(nibIm.header["descrip"]).split("b'")[1].split("'")[0]
            ):
                self.loadRoi(nibIm.get_fdata().astype(np.uint8))

    def loadPreloadedRoi(self):
        try:
            self.niftiSegPath = self.df.loc[self.index, "nifti_segmentation_path"]
        except (KeyError, AttributeError):
            return
        mask = (
            nib.load(os.path.join(self.xcel_dir, self.niftiSegPath), mmap=False)
            .get_fdata()
            .astype(np.uint8)
        )
        self.loadRoi(mask)

    def loadRoi(self, mask):
        mask = np.transpose(mask)
        maskPoints = np.where(mask > 0)
        self.mcResultsArray = self.fullArray

        self.segMask = mask
        self.segCoverMask = np.zeros((self.numSlices, self.y, self.x, 4))
        self.pointsPlotted = np.transpose(maskPoints)
        if self.x0_bmode == -1:
            for point in self.pointsPlotted:
                self.segCoverMask[point[0], point[1], point[2]] = [0, 255, 0, 100]
        else:
            for point in self.pointsPlotted:
                self.segCoverMask[point[0], point[1], point[2]] = [128, 0, 128, 100]
                newY = point[1] + (self.y0_bmode - self.y0_CE)
                newX = point[2] + (self.x0_bmode - self.x0_CE)
                self.segCoverMask[point[0], newY, newX] = [0, 255, 0, 100]

        self.backFromLoadButton.setHidden(True)
        self.preLoadedRoiButton.setHidden(True)
        self.chooseRoiButton.setHidden(True)
        self.undoRoiButton.setHidden(False)
        self.acceptGeneratedRoiButton.setHidden(False)
        self.acceptGeneratedRoiButton.clicked.connect(self.moveToTic)
        self.undoRoiButton.clicked.connect(self.restartRoi)
        self.updateIm()

    def drawNewRoi(self):
        self.newRoiButton.setHidden(True)
        self.loadRoiButton.setHidden(True)
        self.saveRoiButton.setHidden(True)
        self.drawRoiButton.setHidden(False)
        self.backFromDrawButton.setHidden(False)
        self.undoLastPtButton.setHidden(False)
        self.redrawRoiButton.setHidden(False)
        self.fitToRoiButton.setHidden(False)
        self.closeRoiButton.setHidden(False)
        self.acceptConstRoiButton.setHidden(False)

    def backToLastScreen(self):
        self.lastGui.show()
        self.hide()

    def setFilenameDisplays(self, imageName):
        self.imagePathInput.setHidden(False)

        imFile = imageName.split("/")[-1]

        self.imagePathInput.setText(imFile)
        self.inputTextPath = imageName

    def acceptRoiNoMc(self):
        if not self.drawRoiButton.isCheckable():
            self.pointsPlotted = [*set(self.pointsPlotted)]
            points = self.pointsPlotted
            if self.imDrawn == 1:  # move ROI to CE
                xDiff = self.x0_CE - self.x0_bmode
                yDiff = self.y0_CE - self.y0_bmode
                points = [
                    [point[0] + xDiff, point[1] + yDiff] for point in self.pointsPlotted
                ]
            elif self.imDrawn == 0:
                return

            self.mcResultsArray = self.fullArray

            self.segCoverMask = np.zeros((self.numSlices, self.y, self.x, 4))
            self.segMask = np.zeros((self.numSlices, self.y, self.x))

            bmodeMask = np.zeros((self.y, self.x))
            ceusMask = np.zeros((self.y, self.x))
            for point in points:
                ceusMask[point[1], point[0]] = 1
                self.segMask[:, point[1], point[0]] = 1
                # self.mcResultsArray[:, point[1], point[0]] = [255, 0, 0]
                newX = point[0] + (self.x0_bmode - self.x0_CE)  # CE to B-Mode
                newY = point[1] + (self.y0_bmode - self.y0_CE)  # CE to B-Mode
                bmodeMask[newY, newX] = 1

            ceusMask = binary_fill_holes(ceusMask)
            bmodeMask = binary_fill_holes(bmodeMask)

            ceusMaskPoints = np.transpose(np.where(ceusMask > 0))
            bmodeMaskPoints = np.transpose(np.where(bmodeMask > 0))

            for point in ceusMaskPoints:
                self.segCoverMask[:, point[0], point[1]] = [128, 0, 128, 100]
                self.segMask[:, point[0], point[1]] = 1

            # self.loadRoi(np.transpose(self.segMask))

            for point in bmodeMaskPoints:
                self.segCoverMask[:, point[0], point[1]] = [0, 255, 0, 100]

            self.updateIm()
            self.acceptGeneratedRoiButton.setHidden(False)
            self.drawRoiButton.setHidden(True)
            self.backFromDrawButton.setHidden(True)
            self.undoRoiButton.setHidden(False)
            self.undoLastPtButton.setHidden(True)
            self.redrawRoiButton.setHidden(True)
            self.fitToRoiButton.setHidden(True)
            self.acceptConstRoiButton.setHidden(True)
            self.roiFitNoteLabel.setHidden(True)
            self.saveRoiButton.setHidden(False)
            self.acceptGeneratedRoiButton.setCheckable(False)
            self.undoRoiButton.setCheckable(False)
            self.acceptGeneratedRoiButton.clicked.connect(self.moveToTic)
            self.undoRoiButton.clicked.connect(self.restartRoi)
            self.update()

    def perform_MC(self):
        # Credit Thodsawit Tiyarattanachai, MD. See Utils/motionCorrection.py for full citation
        if not self.drawRoiButton.isCheckable():
            self.segMask = np.zeros([self.numSlices, self.y, self.x])
            self.pointsPlotted = [*set(self.pointsPlotted)]
            points = self.pointsPlotted
            if self.imDrawn == 2:
                xDiff = self.x0_bmode - self.x0_CE
                yDiff = self.y0_bmode - self.y0_CE
                points = [
                    [point[0] + xDiff, point[1] + yDiff] for point in self.pointsPlotted
                ]
            elif self.imDrawn == 0:
                return

            for point in points:
                self.segMask[self.curFrameIndex, point[1], point[0]] = 1
            self.segMask[self.curFrameIndex] = binary_fill_holes(
                self.segMask[self.curFrameIndex]
            )

            set_quantile = 0.50
            step = 1  # fullFrameRate. step=2 for halfFrameRate
            threshold_decrease_per_step = 0.02

            # get ref frame
            search_margin = int((0.5 / 15) * self.h_bmode)
            ref_frames = [self.curFrameIndex]
            mask = self.segMask[self.curFrameIndex]
            pos_coor = np.argwhere(mask > 0)
            x_values = pos_coor[:, 1]
            y_values = pos_coor[:, 0]
            x0 = x_values.min()
            x1 = x_values.max()
            w = x1 - x0 + 1
            y0 = y_values.min()
            y1 = y_values.max()
            h = y1 - y0 + 1
            bboxes = [(x0, y0, w, h)]

            ###################################################
            # find initial correlation in the first run
            min_x0 = min([e[0] for e in bboxes]) - search_margin
            max_x1 = max([e[0] + e[2] for e in bboxes]) + search_margin
            min_y0 = min([e[1] for e in bboxes]) - search_margin
            max_y1 = max([e[1] + e[3] for e in bboxes])
            bmode = self.fullGrayArray[:, min_y0:max_y1, min_x0:max_x1]
            ref_f = ref_frames[0]
            ref_b = bboxes[0]
            ref_bmodes = [
                self.fullGrayArray[
                    ref_f,
                    ref_b[1] : ref_b[1] + ref_b[3],
                    ref_b[0] : ref_b[0] + ref_b[2],
                ]
            ]

            _, threshold = mc.find_correlation(
                bmode, ref_bmodes, set_quantile
            )
            ###################################################

            ref_patches = ref_bmodes[:]

            previous_all_lesion_bboxes = [None] * self.fullGrayArray.shape[0]
            iteration = 1

            while True:
                out_array = np.zeros(
                    list(self.fullGrayArray.shape) + [3], dtype=np.uint8
                )

                all_search_bboxes = [None] * self.fullGrayArray.shape[0]
                all_lesion_bboxes = [None] * self.fullGrayArray.shape[0]
                corr_with_ref = [None] * self.fullGrayArray.shape[0]

                for ref_idx in range(len(ref_frames)):
                    ref_frame = ref_frames[ref_idx]
                    ref_bbox = bboxes[ref_idx]

                    if ref_idx == 0:
                        if ref_idx == len(ref_frames) - 1:
                            # There is only 1 ref_frame
                            ref_begin = 0
                            ref_end = self.fullGrayArray.shape[0]
                        else:
                            # This is the first ref_frame. There are >1 ref frames.
                            ref_begin = 0
                            ref_end = int(
                                (ref_frames[ref_idx] + ref_frames[ref_idx + 1]) / 2
                            )
                    else:
                        if ref_idx == len(ref_frames) - 1:
                            # This is the last ref frame. There are >1 ref frames.
                            ref_begin = int(
                                (ref_frames[ref_idx - 1] + ref_frames[ref_idx]) / 2
                            )
                            ref_end = self.fullGrayArray.shape[0]
                        else:
                            # These are ref frames in the middle. There are >1 ref frames.
                            ref_begin = int(
                                (ref_frames[ref_idx - 1] + ref_frames[ref_idx]) / 2
                            )
                            ref_end = int(
                                (ref_frames[ref_idx] + ref_frames[ref_idx + 1]) / 2
                            )

                    #######################

                    # forward tracking
                    ##############################################################
                    if (
                        ref_frame < ref_end - 1
                    ):  # can forward track only if there are frames after the ref_frame
                        # print('forward tracking')

                        previous_bbox = ref_bbox

                        valid = True

                        for frame in range(ref_frame, ref_end, step):
                            full_frame = self.fullGrayArray[frame]

                            if valid:
                                search_w = int(previous_bbox[2] + (2 * search_margin))
                                search_h = int(previous_bbox[3] + (2 * search_margin))
                                search_x0 = int(
                                    previous_bbox[0]
                                    - ((search_w - previous_bbox[2]) / 2)
                                )
                                search_y0 = int(
                                    previous_bbox[1]
                                    - ((search_h - previous_bbox[3]) / 2)
                                )
                                search_bbox = (search_x0, search_y0, search_w, search_h)
                                search_region = full_frame[
                                    search_y0 : search_y0 + search_h,
                                    search_x0 : search_x0 + search_w,
                                ]

                                all_search_bboxes[frame] = search_bbox

                            else:
                                all_search_x0 = [
                                    b[0]
                                    for b in all_search_bboxes[ref_frame + 1 : ref_end]
                                    if not (b is None)
                                ]
                                median_x0 = np.median(all_search_x0)
                                IQR_x0 = np.quantile(all_search_x0, 0.75) - np.quantile(
                                    all_search_x0, 0.25
                                )
                                all_search_x0 = [
                                    x
                                    for x in all_search_x0
                                    if (x >= median_x0 - (1.5 * IQR_x0))
                                    and (x <= median_x0 + (1.5 * IQR_x0))
                                ]
                                min_search_x0 = min(all_search_x0)
                                max_search_x0 = max(all_search_x0)

                                all_search_y0 = [
                                    b[1]
                                    for b in all_search_bboxes[ref_frame + 1 : ref_end]
                                    if not (b is None)
                                ]
                                median_y0 = np.median(all_search_y0)
                                IQR_y0 = np.quantile(all_search_y0, 0.75) - np.quantile(
                                    all_search_y0, 0.25
                                )
                                all_search_y0 = [
                                    y
                                    for y in all_search_y0
                                    if (y >= median_y0 - (1.5 * IQR_y0))
                                    and (y <= median_y0 + (1.5 * IQR_y0))
                                ]
                                min_search_y0 = min(all_search_y0)
                                max_search_y0 = max(all_search_y0)

                                search_x0 = min_search_x0
                                search_y0 = min_search_y0
                                search_w = (max_search_x0 - min_search_x0) + int(
                                    ref_bbox[2] + (2 * search_margin)
                                )
                                search_h = (max_search_y0 - min_search_y0) + int(
                                    previous_bbox[3] + (2 * search_margin)
                                )
                                search_bbox = (search_x0, search_y0, search_w, search_h)
                                search_region = full_frame[
                                    search_y0 : search_y0 + search_h,
                                    search_x0 : search_x0 + search_w,
                                ]

                            mean_corr, max_loc = mc.compute_similarity_map(
                                search_region, ref_patches, ref_idx
                            )
                            corr_with_ref[frame] = mean_corr

                            if mean_corr >= threshold:
                                valid = True
                                current_w = ref_bbox[2]
                                current_h = ref_bbox[3]
                                current_x0 = search_x0 + max_loc[0]
                                current_y0 = search_y0 + max_loc[1]
                                current_bbox = (
                                    current_x0,
                                    current_y0,
                                    current_w,
                                    current_h,
                                )

                                img_bbox = cv2.rectangle(
                                    cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                    (search_x0, search_y0),
                                    (search_x0 + search_w, search_y0 + search_h),
                                    (255, 255, 255),
                                    2,
                                )
                                # img_bbox = cv2.rectangle(img_bbox,
                                #                             (current_bbox[0], current_bbox[1]),
                                #                             (current_bbox[0] + current_bbox[2], current_bbox[1] + current_bbox[3]),
                                #                             (0, 255, 0), 2)
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
                                img_bbox = cv2.rectangle(
                                    cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                    (search_x0, search_y0),
                                    (search_x0 + search_w, search_y0 + search_h),
                                    (255, 0, 0),
                                    2,
                                )
                                # img_bbox = cv2.putText(img_bbox, 'frame: '+str(frame), (25,25), cv2.FONT_HERSHEY_SIMPLEX,
                                #             1, (255,0,0), 2, cv2.LINE_AA)
                                # img_bbox = cv2.putText(img_bbox, 'corr: '+str(mean_corr), (25,50), cv2.FONT_HERSHEY_SIMPLEX,
                                #             1, (255,0,0), 2, cv2.LINE_AA)

                                out_array[frame] = img_bbox
                        #########################################################

                        # backward tracking
                        ##############################################################
                        if ref_frame > ref_begin:
                            # print('backward tracking')

                            previous_bbox = ref_bbox

                            valid = True

                            for frame in range(ref_frame - 1, ref_begin - 1, -step):
                                full_frame = self.fullGrayArray[frame]

                                if valid:
                                    search_w = int(
                                        previous_bbox[2] + (2 * search_margin)
                                    )
                                    search_h = int(
                                        previous_bbox[3] + (2 * search_margin)
                                    )
                                    search_x0 = int(
                                        previous_bbox[0]
                                        - ((search_w - previous_bbox[2]) / 2)
                                    )
                                    search_y0 = int(
                                        previous_bbox[1]
                                        - ((search_h - previous_bbox[3]) / 2)
                                    )
                                    search_bbox = (
                                        search_x0,
                                        search_y0,
                                        search_w,
                                        search_h,
                                    )
                                    search_region = full_frame[
                                        search_y0 : search_y0 + search_h,
                                        search_x0 : search_x0 + search_w,
                                    ]

                                    all_search_bboxes[frame] = search_bbox

                                else:
                                    all_search_x0 = [
                                        b[0]
                                        for b in all_search_bboxes[ref_begin:ref_frame]
                                        if not (b is None)
                                    ]
                                    median_x0 = np.median(all_search_x0)
                                    IQR_x0 = np.quantile(
                                        all_search_x0, 0.75
                                    ) - np.quantile(all_search_x0, 0.25)
                                    all_search_x0 = [
                                        x
                                        for x in all_search_x0
                                        if (x >= median_x0 - (1.5 * IQR_x0))
                                        and (x <= median_x0 + (1.5 * IQR_x0))
                                    ]
                                    min_search_x0 = min(all_search_x0)
                                    max_search_x0 = max(all_search_x0)

                                    all_search_y0 = [
                                        b[1]
                                        for b in all_search_bboxes[ref_begin:ref_frame]
                                        if not (b is None)
                                    ]
                                    median_y0 = np.median(all_search_y0)
                                    IQR_y0 = np.quantile(
                                        all_search_y0, 0.75
                                    ) - np.quantile(all_search_y0, 0.25)
                                    all_search_y0 = [
                                        y
                                        for y in all_search_y0
                                        if (y >= median_y0 - (1.5 * IQR_y0))
                                        and (y <= median_y0 + (1.5 * IQR_y0))
                                    ]
                                    min_search_y0 = min(all_search_y0)
                                    max_search_y0 = max(all_search_y0)

                                    search_x0 = min_search_x0
                                    search_y0 = min_search_y0
                                    search_w = (max_search_x0 - min_search_x0) + int(
                                        ref_bbox[2] + (2 * search_margin)
                                    )
                                    search_h = (max_search_y0 - min_search_y0) + int(
                                        previous_bbox[3] + (2 * search_margin)
                                    )
                                    search_bbox = (
                                        search_x0,
                                        search_y0,
                                        search_w,
                                        search_h,
                                    )
                                    search_region = full_frame[
                                        search_y0 : search_y0 + search_h,
                                        search_x0 : search_x0 + search_w,
                                    ]

                                mean_corr, max_loc = mc.compute_similarity_map(
                                    search_region, ref_patches, ref_idx
                                )
                                corr_with_ref[frame] = mean_corr

                                if mean_corr >= threshold:
                                    valid = True
                                    current_w = ref_bbox[2]
                                    current_h = ref_bbox[3]
                                    current_x0 = search_x0 + max_loc[0]
                                    current_y0 = search_y0 + max_loc[1]
                                    current_bbox = (
                                        current_x0,
                                        current_y0,
                                        current_w,
                                        current_h,
                                    )

                                    img_bbox = cv2.rectangle(
                                        cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                        (search_x0, search_y0),
                                        (search_x0 + search_w, search_y0 + search_h),
                                        (255, 255, 255),
                                        2,
                                    )
                                    # img_bbox = cv2.rectangle(img_bbox,
                                    #                             (current_bbox[0], current_bbox[1]),
                                    #                             (current_bbox[0] + current_bbox[2], current_bbox[1] + current_bbox[3]),
                                    #                             (0, 255, 0), 2)
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
                                    img_bbox = cv2.rectangle(
                                        cv2.cvtColor(full_frame, cv2.COLOR_GRAY2BGR),
                                        (search_x0, search_y0),
                                        (search_x0 + search_w, search_y0 + search_h),
                                        (255, 0, 0),
                                        2,
                                    )
                                    # img_bbox = cv2.putText(img_bbox, 'frame: '+str(frame), (25,25), cv2.FONT_HERSHEY_SIMPLEX,
                                    #             1, (255,0,0), 2, cv2.LINE_AA)
                                    # img_bbox = cv2.putText(img_bbox, 'corr: '+str(mean_corr), (25,50), cv2.FONT_HERSHEY_SIMPLEX,
                                    #             1, (255,0,0), 2, cv2.LINE_AA)

                                    out_array[frame] = img_bbox
                        #########################################################

                # check if lesion bbox in any frame move in this iteration
                #####################
                bbox_move = mc.check_bbox_move(
                    previous_all_lesion_bboxes, all_lesion_bboxes
                )
                if bbox_move or (
                    threshold < min([e for e in corr_with_ref if not (e is None)])
                ):
                    break
                #####################

                previous_all_lesion_bboxes = all_lesion_bboxes[:]
                previous_out_array = out_array.copy()
                threshold -= threshold_decrease_per_step
                iteration += 1

            try:
                self.mcResultsArray = previous_out_array
            except NameError:
                print("MC not possible. Must choose a better ROI")
            self.bboxes = previous_all_lesion_bboxes
            self.ref_frames = ref_frames

            # Repurpose self.segMask to hold mc results
            del self.segMask
            self.segCoverMask = np.zeros((self.numSlices, self.y, self.x, 4))
            self.segMask = np.zeros((self.numSlices, self.y, self.x))
            xDiff = self.x0_CE - self.x0_bmode
            yDiff = self.y0_CE - self.y0_bmode
            for t in range(self.segMask.shape[0]):
                if self.bboxes[t] is not None:
                    x0, y0, x_len, y_len = self.bboxes[t]
                    x0 += xDiff
                    y0 += yDiff
                    if y0 + y_len >= self.segMask.shape[1]:
                        y_len = self.segMask.shape[1] - y0 - 1
                    if x0 + x_len >= self.segMask.shape[2]:
                        x_len = self.segMask.shape[2] - x0 - 1
                    self.segCoverMask[t, y0 : y0 + y_len, x0 : x0 + x_len] = [
                        128,
                        0,
                        128,
                        100,
                    ]
                    self.segMask[t, y0 : y0 + y_len, x0 : x0 + x_len] = 1
                    x0 += self.x0_bmode - self.x0_CE  # CE to B-Mode
                    y0 += self.y0_bmode - self.y0_CE  # CE to B-Mode
                    if y0 + y_len >= self.segMask.shape[1]:
                        y_len = self.segMask.shape[1] - y0 - 1
                    if x0 + x_len >= self.segMask.shape[2]:
                        x_len = self.segMask.shape[2] - x0 - 1
                    self.segCoverMask[t, y0 : y0 + y_len, x0 : x0 + x_len] = [
                        0,
                        255,
                        0,
                        100,
                    ]

            self.mc = True
            self.updateIm()
            self.acceptGeneratedRoiButton.setHidden(False)
            self.drawRoiButton.setHidden(True)
            self.backFromDrawButton.setHidden(True)
            self.undoRoiButton.setHidden(False)
            self.undoLastPtButton.setHidden(True)
            self.redrawRoiButton.setHidden(True)
            self.fitToRoiButton.setHidden(True)
            self.acceptConstRoiButton.setHidden(True)
            self.roiFitNoteLabel.setHidden(True)
            self.saveRoiButton.setHidden(False)
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
        self.acceptConstRoiButton.setHidden(True)
        self.backFromDrawButton.setHidden(True)
        self.roiFitNoteLabel.setHidden(True)
        self.drawRoiButton.setCheckable(True)
        self.drawRoiButton.setChecked(False)

        self.newRoiButton.setHidden(False)
        self.loadRoiButton.setHidden(False)
        self.updateIm()

    def restartRoi(self):
        self.mcResultsArray = []
        self.mcImDisplayLabel.clear()
        self.drawRoiButton.setHidden(False)
        self.backFromDrawButton.setHidden(False)
        self.undoLastPtButton.setHidden(False)
        self.redrawRoiButton.setHidden(False)
        self.fitToRoiButton.setHidden(False)
        self.acceptConstRoiButton.setHidden(False)
        self.acceptGeneratedRoiButton.setHidden(True)
        self.undoRoiButton.setHidden(True)
        self.roiFitNoteLabel.setHidden(False)
        self.saveRoiButton.setHidden(True)
        try:
            del self.segCoverMask
        except AttributeError:
            pass
        self.undoLastRoi()
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
        bmode = np.array(bmodeFile.get_fdata(caching="unchanged")).astype(np.uint8)
        del bmodeFile
        ceFile = nib.load(cePath)
        contrastEnhanced = np.array(ceFile.get_fdata(caching="unchanged")).astype(
            np.uint8
        )
        del ceFile

        bmode = np.transpose(
            bmode.reshape(
                (bmode.shape[0], bmode.shape[1], bmode.shape[2], bmode.shape[4])
            ),
            (2, 1, 0, 3),
        )
        contrastEnhanced = np.transpose(
            contrastEnhanced.reshape(
                (
                    contrastEnhanced.shape[0],
                    contrastEnhanced.shape[1],
                    contrastEnhanced.shape[2],
                    contrastEnhanced.shape[4],
                )
            ),
            (2, 1, 0, 3),
        )
        self.w_CE = contrastEnhanced.shape[2]
        self.h_CE = contrastEnhanced.shape[1]
        self.fullArray = np.concatenate((contrastEnhanced, bmode), axis=1)
        del bmode
        del contrastEnhanced

        self.x = self.fullArray.shape[2]
        self.y = self.fullArray.shape[1]
        self.numSlices = self.fullArray.shape[0]
        self.fullGrayArray = np.array(
            [
                cv2.cvtColor(self.fullArray[i], cv2.COLOR_BGR2GRAY)
                for i in range(self.fullArray.shape[0])
            ]
        )

        # Eli Prostate Specific Vals
        self.axRes, self.latRes = 0.4, 0.4 # mm/pixel (hard-coded for Prostate Project)
        self.cineRate = 30  # frames/sec (hard-coded for Prostate Project)

        self.maskCoverImg = np.zeros([self.y, self.x, 4])
        self.mask = np.zeros([self.y, self.x])

        self.imX0 = 350
        self.imX1 = 1151
        self.imY0 = 80
        self.imY1 = 561
        xLen = self.imX1 - self.imX0
        yLen = self.imY1 - self.imY0

        quotient = self.x / self.y
        if quotient > (xLen / yLen):
            self.widthScale = xLen
            self.depthScale = int(self.widthScale / quotient)
            emptySpace = yLen - self.depthScale
            yBuffer = int(emptySpace / 2)
            self.imY0 += yBuffer
            self.imY1 -= yBuffer
        else:
            self.widthScale = int(yLen * quotient)
            self.depthScale = yLen
            emptySpace = xLen - self.widthScale
            xBuffer = int(emptySpace / 2)
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
        self.imCoverPixmap.fill(Qt.GlobalColor.transparent)
        self.imCoverLabel.setPixmap(self.imCoverPixmap)

        self.curLeftLineX = 0
        self.curRightLineX = self.widthScale - 1
        self.curTopLineY = 0
        self.curBottomLineY = self.depthScale - 1
        self.fullPath = cePath

        self.curSliceSlider.setMaximum(self.numSlices - 1)
        self.curSliceSpinBox.setMaximum(self.numSlices - 1)

        self.sliceArray = np.round(
            [i * (1 / self.cineRate) for i in range(self.numSlices)], decimals=2
        )

        self.curSliceTotal.setText(str(self.numSlices - 1))

        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)

        self.drawRoiButton.setCheckable(True)

        self.updateIm()

        self.loadRoiButton.setHidden(True)
        self.newRoiButton.setHidden(True)
        self.defImBoundsButton.setHidden(False)
        self.defImBoundsButton.clicked.connect(self.startBoundDef)

        self.closeRoiButton.clicked.connect(
            self.acceptPolygon
        )  # called to exit the paint function
        self.undoLastPtButton.clicked.connect(
            self.undoLastPoint
        )  # deletes last drawn rectangle if on sag or cor slices

        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.drawRoiButton.clicked.connect(self.startRoiDraw)

    def openAviImage(self, path):
        cap = cv2.VideoCapture(path)
        self.numSlices = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.cineRate = cap.get(cv2.CAP_PROP_FPS)
        ret, firstFrame = cap.read()
        if not ret:
            print("No data in video file!")
            return
        firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_RGB2BGR)
        self.fullArray = np.zeros(
            (self.numSlices, firstFrame.shape[0], firstFrame.shape[1], 3)
        ).astype(firstFrame.dtype)
        self.fullArray[0] = firstFrame
        for i in range(1, self.numSlices):
            ret, frame = cap.read()
            if not ret:
                print("Video data ended prematurely!")
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.fullArray[i] = frame

        self.x = self.fullArray.shape[2]
        self.y = self.fullArray.shape[1]
        self.fullGrayArray = np.array(
            [
                cv2.cvtColor(self.fullArray[i], cv2.COLOR_BGR2GRAY)
                for i in range(self.fullArray.shape[0])
            ]
        )

        self.fullPath = path

        self.imX0 = 350
        self.imX1 = 1151
        self.imY0 = 80
        self.imY1 = 561
        xLen = self.imX1 - self.imX0
        yLen = self.imY1 - self.imY0

        quotient = self.x / self.y
        if quotient > (xLen / yLen):
            self.widthScale = xLen
            self.depthScale = int(self.widthScale / quotient)
            emptySpace = yLen - self.depthScale
            yBuffer = int(emptySpace / 2)
            self.imY0 += yBuffer
            self.imY1 -= yBuffer
        else:
            self.widthScale = int(yLen * quotient)
            self.depthScale = yLen
            emptySpace = xLen - self.widthScale
            xBuffer = int(emptySpace / 2)
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
        self.imCoverPixmap.fill(Qt.GlobalColor.transparent)
        self.imCoverLabel.setPixmap(self.imCoverPixmap)

        self.maskCoverImg = np.zeros([self.y, self.x, 4])

        self.curSliceSlider.setMaximum(self.numSlices - 1)
        self.curSliceSpinBox.setMaximum(self.numSlices - 1)

        self.sliceArray = np.round(
            [i * (1 / self.cineRate) for i in range(self.numSlices)], decimals=2
        )

        self.curSliceTotal.setText(str(self.numSlices - 1))

        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)

        self.xScale = self.widthScale / self.x
        self.yScale = self.depthScale / self.y
        self.curLeftLineX = 0
        self.curRightLineX = self.widthScale - 1
        self.curTopLineY = 0
        self.curBottomLineY = self.depthScale - 1

        self.updateBoundLines("Left X")

        self.drawRoiButton.setCheckable(True)

        self.updateIm()

        self.loadRoiButton.setHidden(True)
        self.newRoiButton.setHidden(True)
        self.defImBoundsButton.setHidden(False)
        self.defImBoundsButton.clicked.connect(self.startBoundDef)

        self.closeRoiButton.clicked.connect(
            self.acceptPolygon
        )  # called to exit the paint function
        self.undoLastPtButton.clicked.connect(
            self.undoLastPoint
        )  # deletes last drawn rectangle if on sag or cor slices

        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.drawRoiButton.clicked.connect(self.startRoiDraw)
        
    def openVisualsonicsXmlImage(self, path):
        _, self.fullGrayArray, info = visualsonics2dCeusParser(Path(path))
        self.fullArray = np.zeros((self.fullGrayArray.shape[0], self.fullGrayArray.shape[1], self.fullGrayArray.shape[2], 3))
        self.fullPath = str(Path(path).absolute())
        
        aviPath = next(Path(path).parent.glob("*.avi"), None)
        if aviPath is None:
            self.cineRate = 21 # default
        else:
            cap = cv2.VideoCapture(aviPath)
            self.cineRate = cap.get(cv2.CAP_PROP_FPS)
        
        clipFact = 1; dynRange = 150
        for i in range(self.fullGrayArray.shape[0]):
            frame = self.fullGrayArray[i]/np.amax(self.fullGrayArray)*255
            maxVal = clipFact*np.amax(frame); minVal = np.amax(frame) - dynRange
            frame = np.clip(frame, minVal, maxVal)
            frame = 255 * (frame - np.min(frame)) / (np.max(frame) - np.min(frame))
            self.fullArray[i] = cv2.cvtColor(np.array(frame, dtype=np.uint8), cv2.COLOR_GRAY2RGB)
        
        self.numSlices, self.y, self.x = self.fullGrayArray.shape
        self.imX0 = 350
        self.imX1 = 1151
        self.imY0 = 80
        self.imY1 = 561
        xLen = self.imX1 - self.imX0
        yLen = self.imY1 - self.imY0
        
        width, depth = (info.contrastWidthAxis[-1] - info.contrastDepthAxis[0]), (info.contrastDepthAxis[-1] - info.contrastDepthAxis[0])

        quotient = width / depth
        if quotient > (xLen / yLen):
            self.widthScale = xLen
            self.depthScale = int(self.widthScale / quotient)
            emptySpace = yLen - self.depthScale
            yBuffer = int(emptySpace / 2)
            self.imY0 += yBuffer
            self.imY1 -= yBuffer
        else:
            self.widthScale = int(yLen * quotient)
            self.depthScale = yLen
            emptySpace = xLen - self.widthScale
            xBuffer = int(emptySpace / 2)
            self.imX0 += xBuffer
            self.imX1 -= xBuffer
            
        self.x0_bmode = -1; self.x0_CE = 0
        self.y0_bmode = -1; self.y0_CE = 0
        self.w_bmode = 0; self.w_CE = self.x
        self.h_bmode = 0; self.h_CE = self.y

        self.imPlane.move(self.imX0, self.imY0)
        self.imPlane.resize(self.widthScale, self.depthScale)
        self.imMaskLayer.move(self.imX0, self.imY0)
        self.imMaskLayer.resize(self.widthScale, self.depthScale)
        self.imCoverLabel.move(self.imX0, self.imY0)
        self.imCoverLabel.resize(self.widthScale, self.depthScale)
        self.mcImDisplayLabel.move(self.imX0, self.imY0)
        self.mcImDisplayLabel.resize(self.widthScale, self.depthScale)

        self.imCoverPixmap = QPixmap(self.widthScale, self.depthScale)
        self.imCoverPixmap.fill(Qt.GlobalColor.transparent)
        self.imCoverLabel.setPixmap(self.imCoverPixmap)

        self.maskCoverImg = np.zeros([self.y, self.x, 4])

        self.curSliceSlider.setMaximum(self.numSlices - 1)
        self.curSliceSpinBox.setMaximum(self.numSlices - 1)

        self.sliceArray = np.round(
            [i * (1 / self.cineRate) for i in range(self.numSlices)], decimals=2
        )

        self.curSliceTotal.setText(str(self.numSlices - 1))

        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)

        self.xScale = self.widthScale / self.x
        self.yScale = self.depthScale / self.y
        self.curLeftLineX = 0
        self.curRightLineX = self.widthScale - 1
        self.curTopLineY = 0
        self.curBottomLineY = self.depthScale - 1

        self.updateBoundLines("Left X")

        self.drawRoiButton.setCheckable(True)

        # self.updateIm()

        # self.loadRoiButton.setHidden(True)
        # self.newRoiButton.setHidden(True)
        # self.defImBoundsButton.setHidden(False)
        self.defImBoundsButton.clicked.connect(self.startBoundDef)

        self.closeRoiButton.clicked.connect(
            self.acceptPolygon
        )  # called to exit the paint function
        self.undoLastPtButton.clicked.connect(
            self.undoLastPoint
        )  # deletes last drawn rectangle if on sag or cor slices

        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.drawRoiButton.clicked.connect(self.startRoiDraw)
        
        canvas = self.imCoverLabel.pixmap()
        canvas.fill(Qt.GlobalColor.transparent)
        self.imCoverLabel.setPixmap(canvas)
        self.updateIm()


    def openDicomImage(self, index, xcel_dir):
        if index > -1:
            self.CE_side = self.df.loc[
                self.xcelIndices[index], "CE_window_left(l)_or_right(r)"
            ]
            self.cineRate = self.df.loc[self.xcelIndices[index], "CineRate"]
            self.index = index
            self.xcel_dir = xcel_dir

            self.fullPath = os.path.join(
                xcel_dir, self.df.loc[self.xcelIndices[index], "cleaned_path"]
            )
        else:
            self.fullPath = xcel_dir

        ds = dicom.dcmread(self.fullPath)
        ar = ds.pixel_array

        color_channel = ds.PhotometricInterpretation
        self.fullArray, self.fullGrayArray = load_cine(ar, color_channel)
        self.x = self.fullArray.shape[2]
        self.y = self.fullArray.shape[1]
        self.numSlices = self.fullArray.shape[0]

        self.imX0 = 350
        self.imX1 = 1151
        self.imY0 = 80
        self.imY1 = 561
        xLen = self.imX1 - self.imX0
        yLen = self.imY1 - self.imY0

        quotient = self.x / self.y
        if quotient > (xLen / yLen):
            self.widthScale = xLen
            self.depthScale = int(self.widthScale / quotient)
            emptySpace = yLen - self.depthScale
            yBuffer = int(emptySpace / 2)
            self.imY0 += yBuffer
            self.imY1 -= yBuffer
        else:
            self.widthScale = int(yLen * quotient)
            self.depthScale = yLen
            emptySpace = xLen - self.widthScale
            xBuffer = int(emptySpace / 2)
            self.imX0 += xBuffer
            self.imX1 -= xBuffer
        
        self.cineRate = ds.CineRate
        self.imCoverPixmap = QPixmap(self.widthScale, self.depthScale)
        self.imCoverPixmap.fill(Qt.GlobalColor.transparent)
        self.imCoverLabel.setPixmap(self.imCoverPixmap)

        self.sliceArray = np.round(
            [i * (1 / self.cineRate) for i in range(self.numSlices)], decimals=2
        ).astype(np.int32)
        self.maskCoverImg = np.zeros([self.y, self.x, 4])
        self.curSliceSlider.setMaximum(self.numSlices - 1)
        self.curSliceSpinBox.setMaximum(self.numSlices - 1)
        self.curSliceTotal.setText(str(self.numSlices - 1))

        self.curSliceSpinBox.setValue(self.curFrameIndex)
        self.curSliceSlider.setValue(self.curFrameIndex)
        self.curSliceSlider.valueChanged.connect(self.curSliceSliderValueChanged)
        self.curSliceSpinBox.valueChanged.connect(self.curSliceSpinBoxValueChanged)

        self.drawRoiButton.setCheckable(True)

        self.updateIm()

        self.closeRoiButton.clicked.connect(
            self.acceptPolygon
        )  # called to exit the paint function
        self.undoLastPtButton.clicked.connect(
            self.undoLastPoint
        )  # deletes last drawn rectangle if on sag or cor slices

        self.redrawRoiButton.clicked.connect(self.undoLastRoi)
        self.drawRoiButton.clicked.connect(self.startRoiDraw)
        
        if hasattr(ds, 'SequenceOfUltrasoundRegions') and len(ds.SequenceOfUltrasoundRegions) >= 2 \
            and hasattr(ds.SequenceOfUltrasoundRegions[0], 'RegionLocationMinX0'):
            self.x0_CE = ds.SequenceOfUltrasoundRegions[0].RegionLocationMinX0
            self.y0_CE = ds.SequenceOfUltrasoundRegions[0].RegionLocationMinY0
            self.w_CE = ds.SequenceOfUltrasoundRegions[0].RegionLocationMaxX1 - self.x0_CE
            self.h_CE = ds.SequenceOfUltrasoundRegions[0].RegionLocationMaxY1 - self.y0_CE
            self.x0_bmode = ds.SequenceOfUltrasoundRegions[1].RegionLocationMinX0
            self.y0_bmode = ds.SequenceOfUltrasoundRegions[1].RegionLocationMinY0
            self.w_bmode = ds.SequenceOfUltrasoundRegions[1].RegionLocationMaxX1 - self.x0_bmode
            self.h_bmode = ds.SequenceOfUltrasoundRegions[1].RegionLocationMaxY1 - self.y0_bmode
            self.moveToAnalysis(preloaded_bounds=True)
            
        else:
            self.loadRoiButton.setHidden(True)
            self.newRoiButton.setHidden(True)
            self.defImBoundsButton.setHidden(False)
            self.defImBoundsButton.clicked.connect(self.startBoundDef)
            
            self.curLeftLineX = 0
            self.curRightLineX = self.widthScale - 1
            self.curTopLineY = 0
            self.curBottomLineY = self.depthScale - 1

    def updateBoundLines(self, line):
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.green)
        if line == "Bottom Y":
            painter.drawLine(
                self.curLeftLineX,
                self.curBottomLineY,
                self.curRightLineX,
                self.curBottomLineY,
            )
        elif line == "Top Y":
            painter.drawLine(
                self.curLeftLineX,
                self.curTopLineY,
                self.curRightLineX,
                self.curTopLineY,
            )
        elif line == "Left X":
            painter.drawLine(
                self.curLeftLineX,
                self.curBottomLineY,
                self.curLeftLineX,
                self.curTopLineY,
            )
        elif line == "Right X":
            painter.drawLine(
                self.curRightLineX,
                self.curBottomLineY,
                self.curRightLineX,
                self.curTopLineY,
            )
        else:
            print("Bound line error")
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def leftChangedX(self):
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.green)
        self.curLeftLineX = self.horizontalSlider.value()
        painter.drawLine(
            self.curLeftLineX, self.curBottomLineY, self.curLeftLineX, self.curTopLineY
        )
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def horizContrastChanged(self):
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.yellow)
        painter.drawRect(self.x0_bmode, self.y0_bmode, self.w_bmode, self.h_bmode)
        painter.setPen(Qt.GlobalColor.cyan)
        self.x0_CE = self.horizontalSlider.value()
        painter.drawRect(self.x0_CE, self.y0_CE, self.w_CE, self.h_CE)
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def verticalContrastChanged(self):
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.yellow)
        painter.drawRect(self.x0_bmode, self.y0_bmode, self.w_bmode, self.h_bmode)
        painter.setPen(Qt.GlobalColor.cyan)
        self.y0_CE = self.horizontalSlider.value()
        painter.drawRect(self.x0_CE, self.y0_CE, self.w_CE, self.h_CE)
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def rightChangedX(self):
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.cyan)
        painter.drawLine(
            self.curLeftLineX, self.curBottomLineY, self.curLeftLineX, self.curTopLineY
        )
        painter.setPen(Qt.GlobalColor.green)
        self.curRightLineX = self.horizontalSlider.value()
        painter.drawLine(
            self.curRightLineX,
            self.curBottomLineY,
            self.curRightLineX,
            self.curTopLineY,
        )
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def topChangedY(self):
        self.curTopLineY = self.horizontalSlider.value()
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.cyan)
        painter.drawLine(
            self.curLeftLineX, self.curBottomLineY, self.curLeftLineX, self.curTopLineY
        )
        painter.drawLine(
            self.curRightLineX,
            self.curBottomLineY,
            self.curRightLineX,
            self.curTopLineY,
        )
        painter.setPen(Qt.GlobalColor.green)
        painter.drawLine(
            self.curLeftLineX, self.curTopLineY, self.curRightLineX, self.curTopLineY
        )
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def bottomChangedY(self):
        self.curBottomLineY = self.horizontalSlider.value()
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.cyan)
        painter.drawLine(
            self.curLeftLineX, self.curBottomLineY, self.curLeftLineX, self.curTopLineY
        )
        painter.drawLine(
            self.curRightLineX,
            self.curBottomLineY,
            self.curRightLineX,
            self.curTopLineY,
        )
        painter.drawLine(
            self.curLeftLineX, self.curTopLineY, self.curRightLineX, self.curTopLineY
        )
        painter.setPen(Qt.GlobalColor.green)
        painter.drawLine(
            self.curLeftLineX,
            self.curBottomLineY,
            self.curRightLineX,
            self.curBottomLineY,
        )
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.update()

    def startBoundDef(self):
        self.defImBoundsButton.setHidden(True)
        self.curSliceLabel.setHidden(True)
        self.curSliceOfLabel.setHidden(True)
        self.curSliceSlider.setHidden(True)
        self.curSliceSpinBox.setHidden(True)
        self.curSliceTotal.setHidden(True)
        self.boundBackButton.setHidden(True)
        self.acceptBoundsButton.setHidden(False)
        self.boundDrawLabel.setHidden(False)
        self.horizontalSlider.setHidden(False)
        self.acceptBoundsButton.setText("Accept Left")
        self.boundDrawLabel.setText("Draw B-mode Left Border:")
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(self.widthScale - 1)
        self.curRightLineX = self.widthScale - 1
        try:
            self.horizontalSlider.valueChanged.disconnect()
            self.acceptBoundsButton.clicked.disconnect()
        except TypeError:
            pass
        self.horizontalSlider.valueChanged.connect(self.leftChangedX)
        self.acceptBoundsButton.clicked.connect(self.moveToRightBoundDef)
        self.horizontalSlider.setValue(self.curLeftLineX)
        self.leftChangedX()

    def moveToRightBoundDef(self):
        self.boundDrawLabel.setText("Draw B-mode Right Border")
        self.acceptBoundsButton.setText("Accept Right")
        self.boundBackButton.setHidden(False)
        self.curTopLineY = 0
        self.imCoverLabel.pixmap().fill(Qt.GlobalColor.transparent)
        self.horizontalSlider.valueChanged.disconnect()
        self.acceptBoundsButton.clicked.disconnect()
        self.horizontalSlider.setMinimum(self.curLeftLineX)
        self.horizontalSlider.setMaximum(self.widthScale - 1)
        self.boundBackButton.clicked.connect(self.startBoundDef)
        self.horizontalSlider.valueChanged.connect(self.rightChangedX)
        self.acceptBoundsButton.clicked.connect(self.moveToTopBoundDef)
        self.horizontalSlider.setValue(self.curRightLineX)
        self.rightChangedX()

    def moveToTopBoundDef(self):
        self.boundDrawLabel.setText("Draw B-mode Top Border")
        self.acceptBoundsButton.setText("Accept Top")
        self.curBottomLineY = self.depthScale - 1
        self.imCoverLabel.pixmap().fill(Qt.GlobalColor.transparent)
        self.boundBackButton.clicked.disconnect()
        self.horizontalSlider.valueChanged.disconnect()
        self.acceptBoundsButton.clicked.disconnect()
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(self.depthScale - 1)
        self.horizontalSlider.valueChanged.connect(self.topChangedY)
        self.horizontalSlider.setValue(self.curTopLineY)
        self.acceptBoundsButton.clicked.connect(self.moveToBottomBoundDef)
        self.boundBackButton.clicked.connect(self.moveToRightBoundDef)
        self.topChangedY()

    def moveToBottomBoundDef(self):
        self.boundDrawLabel.setText("Draw B-mode Bottom Border")
        self.acceptBoundsButton.setText("Accept Bottom")
        self.boundBackButton.clicked.disconnect()
        self.horizontalSlider.valueChanged.disconnect()
        self.acceptBoundsButton.clicked.disconnect()
        self.horizontalSlider.setMinimum(self.curTopLineY)
        self.horizontalSlider.setMaximum(self.depthScale - 1)
        self.horizontalSlider.valueChanged.connect(self.bottomChangedY)
        self.horizontalSlider.setValue(self.curBottomLineY)
        self.acceptBoundsButton.clicked.connect(self.acceptBmode)
        self.boundBackButton.clicked.connect(self.moveToTopBoundDef)
        self.bottomChangedY()

    def acceptBmode(self):
        self.y0_bmode = self.curTopLineY
        self.y0_CE = self.y0_bmode
        if self.boundDrawLabel.text() == "Draw B-mode Bottom Border":
            self.x0_bmode = self.curLeftLineX
            self.x0_CE = self.x0_bmode
            self.w_bmode = self.curRightLineX - self.curLeftLineX
            self.h_bmode = self.curBottomLineY - self.curTopLineY
            self.w_CE = self.w_bmode
            self.h_CE = self.h_bmode
        self.horizontalSlider.valueChanged.disconnect()
        self.acceptBoundsButton.clicked.disconnect()
        self.boundBackButton.clicked.disconnect()
        self.boundDrawLabel.setText("Find Horizontal Position for Contrast Image")
        self.acceptBoundsButton.setText("Accept Horizontal")
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(self.widthScale - 1)
        self.horizontalSlider.valueChanged.connect(self.horizContrastChanged)
        self.acceptBoundsButton.clicked.connect(self.moveToVertical)
        self.boundBackButton.clicked.connect(self.moveToBottomBoundDef)
        self.horizontalSlider.setValue(self.x0_CE)
        self.horizContrastChanged()

    def moveToVertical(self):
        self.horizontalSlider.valueChanged.disconnect()
        self.acceptBoundsButton.clicked.disconnect()
        self.boundBackButton.clicked.disconnect()
        self.boundDrawLabel.setText("Find Vertical Position for Contrast Image")
        self.acceptBoundsButton.setText("Accept Vertical")
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(self.depthScale - 1)
        self.horizontalSlider.valueChanged.connect(self.verticalContrastChanged)
        self.acceptBoundsButton.clicked.connect(self.moveToAnalysis)
        self.boundBackButton.clicked.connect(self.acceptBmode)
        self.horizontalSlider.setValue(self.y0_CE)
        self.verticalContrastChanged()
        
    def update_bound_lines(self):
        xScale = self.widthScale / self.x
        yScale = self.depthScale / self.y
        self.x0_bmode = int(self.x0_bmode / xScale)
        self.y0_bmode = int(self.y0_bmode / yScale)
        self.x0_CE = int(self.x0_CE / xScale)
        self.y0_CE = int(self.y0_CE / yScale)
        self.w_bmode = int(self.w_bmode / xScale)
        self.h_bmode = int(self.h_bmode / yScale)
        self.w_CE = int(self.w_CE / xScale)
        self.h_CE = int(self.h_CE / yScale)

    def moveToAnalysis(self, preloaded_bounds=False):
        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        self.imCoverLabel.pixmap().fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.yellow)
        xScale = self.widthScale / self.x
        yScale = self.depthScale / self.y
        
        if not preloaded_bounds:
            self.update_bound_lines()
            
        self.bmodeStartX = self.imX0 + int(xScale * self.x0_bmode)
        self.bmodeEndX = self.bmodeStartX + int(xScale * self.w_bmode)
        self.bmodeStartY = self.imY0 + int(yScale * self.y0_bmode)
        self.bmodeEndY = self.bmodeStartY + int(yScale * self.h_bmode)
        self.ceStartX = self.imX0 + int(xScale * self.x0_CE)
        self.ceEndX = self.ceStartX + int(xScale * self.w_CE)
        self.ceStartY = self.imY0 + int(yScale * self.y0_CE)
        self.ceEndY = self.ceStartY + int(yScale * self.h_CE)
        
        if self.x0_bmode >= 0 and self.y0_bmode >= 0 and self.w_bmode > 0 and self.h_bmode > 0:
            painter.drawRect(
                int(self.x0_bmode * xScale),
                int(self.y0_bmode * yScale),
                int(self.w_bmode * xScale),
                int(self.h_bmode * yScale),
            )
        painter.drawRect(
            int(self.x0_CE * xScale),
            int(self.y0_CE * yScale),
            int(self.w_CE * xScale),
            int(self.h_CE * yScale),
        )
        painter.end()
        self.imCoverLabel.setPixmap(canvas)
        self.horizontalSlider.setHidden(True)
        self.boundDrawLabel.setHidden(True)
        self.acceptBoundsButton.setHidden(True)
        self.boundBackButton.setHidden(True)
        self.curSliceLabel.setHidden(False)
        self.curSliceOfLabel.setHidden(False)
        self.curSliceSlider.setHidden(False)
        self.curSliceSpinBox.setHidden(False)
        self.curSliceTotal.setHidden(False)
        self.loadRoiButton.setHidden(False)
        self.newRoiButton.setHidden(False)
        self.update()
        self.updateIm()

    def updateIm(self):
        if len(self.mcResultsArray):
            self.mcData = np.require(
                self.mcResultsArray[self.curFrameIndex], np.uint8, "C"
            )
            self.bytesLineMc, _ = self.mcData[:, :, 0].strides
            self.qImgMc = QImage(
                self.mcData, self.x, self.y, self.bytesLineMc, QImage.Format.Format_RGB888
            )
            self.mcImDisplayLabel.setPixmap(
                QPixmap.fromImage(self.qImgMc).scaled(self.widthScale, self.depthScale)
            )
            self.maskCoverImg = np.require(
                self.segCoverMask[self.curFrameIndex], np.uint8, "C"
            )
        else:
            self.imData = self.fullArray[self.curFrameIndex]
            self.imData = np.require(self.imData, np.uint8, "C")
            self.bytesLineIm, _ = self.imData[:, :, 0].strides
            self.qImg = QImage(
                self.imData, self.x, self.y, self.bytesLineIm, QImage.Format.Format_RGB888
            )
            self.imPlane.setPixmap(
                QPixmap.fromImage(self.qImg).scaled(self.widthScale, self.depthScale)
            )
            self.maskCoverImg = np.require(self.maskCoverImg, np.uint8, "C")
        self.bytesLineMask, _ = self.maskCoverImg[:, :, 0].strides
        self.qImgMask = QImage(
            self.maskCoverImg, self.x, self.y, self.bytesLineMask, QImage.Format.Format_ARGB32
        )
        self.imMaskLayer.setPixmap(
            QPixmap.fromImage(self.qImgMask).scaled(self.widthScale, self.depthScale)
        )

    def updateCrosshair(self):
        if (
            self.xCur < self.imX1
            and self.xCur > self.imX0
            and self.yCur < self.imY1
            and self.yCur > self.imY0
        ):
            self.actualX = int(
                (self.xCur - self.imX0 - 1) * (self.y - 1) / self.widthScale
            )
            self.actualY = int(
                (self.yCur - self.imY0 - 1) * (self.x - 1) / self.depthScale
            )
            plotX = self.xCur - self.imX0 - 1
        else:
            return

        plotY = self.yCur - self.imY0 - 1

        canvas = self.imCoverLabel.pixmap()
        painter = QPainter(canvas)
        canvas.fill(Qt.GlobalColor.transparent)
        painter.setPen(Qt.GlobalColor.yellow)
        bmodeVertLine = QLine(plotX, 0, plotX, self.depthScale)
        bmodeLatLine = QLine(0, plotY, self.widthScale, plotY)
        painter.drawLines([bmodeVertLine, bmodeLatLine])
        painter.end()
        self.imCoverLabel.setPixmap(canvas)

        self.update()

    def updateSpline(self):
        if len(self.curPointsPlottedX) > 0:
            if self.spline is not None:
                self.spline.remove()

            if len(self.curPointsPlottedX) > 1:
                points = [
                    (self.curPointsPlottedX[i], self.curPointsPlottedY[i])
                    for i in range(len(self.curPointsPlottedX))
                ]
                self.curPointsPlottedX, self.curPointsPlottedY = np.transpose(
                    removeDuplicates(points)
                )
                self.curPointsPlottedX = list(self.curPointsPlottedX)
                self.curPointsPlottedY = list(self.curPointsPlottedY)
                xSpline, ySpline = calculateSpline(
                    self.curPointsPlottedX, self.curPointsPlottedY
                )
                spline = [
                    (int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))
                ]
                spline = np.array([*set(spline)])
                xSpline, ySpline = np.transpose(spline)
                if self.imDrawn == 1:
                    xSpline = np.clip(
                        xSpline,
                        a_min=self.x0_bmode + 1,
                        a_max=self.x0_bmode + self.w_bmode - 2,
                    )
                    ySpline = np.clip(
                        ySpline,
                        a_min=self.y0_bmode + 1,
                        a_max=self.y0_bmode + self.h_bmode - 2,
                    )
                elif self.imDrawn == 2:
                    xSpline = np.clip(
                        xSpline, a_min=self.x0_CE + 1, a_max=self.x0_CE + self.w_CE - 2
                    )
                    ySpline = np.clip(
                        ySpline, a_min=self.y0_CE + 1, a_max=self.y0_CE + self.h_CE - 2
                    )
                # else:
                #     xSpline = np.clip(xSpline, a_min=1, a_max=self.x-2)
                #     ySpline = np.clip(ySpline, a_min=1, a_max=self.y-2)
                # for point in self.oldSpline:
                #     self.maskCoverImg[point[0], point[1]] = [0,0,0,0]
                self.maskCoverImg.fill(0)
                self.oldSpline = []
                for i in range(len(xSpline)):
                    self.maskCoverImg[
                        ySpline[i] - 1 : ySpline[i] + 2, xSpline[i] - 1 : xSpline[i] + 2
                    ] = [255, 255, 0, 255]
                    # for j in range(3):
                    #     for k in range(3):
                    #         self.oldSpline.append([ySpline[i]-j-1, xSpline[i]-k-1])
            else:
                self.maskCoverImg.fill(0)
                self.oldSpline = []
            for i in range(len(self.curPointsPlottedX)):
                self.maskCoverImg[
                    self.curPointsPlottedY[i] - 2 : self.curPointsPlottedY[i] + 3,
                    self.curPointsPlottedX[i] - 2 : self.curPointsPlottedX[i] + 3,
                ] = [0, 0, 255, 255]
        else:
            self.maskCoverImg.fill(0)
            self.oldSpline = []

        self.updateIm()
        # self.updateCrosshair()

    def mousePressEvent(self, event: QMouseEvent):
        self.xCur = event.pos().x()
        self.yCur = event.pos().y()
        if self.drawRoiButton.isChecked():
            # Plot ROI points
            # if self.xCur < self.imX1 and self.xCur > self.imX0 and self.yCur < self.imY1 and self.yCur > self.imY0:
            #     self.actualX = int((self.xCur - self.imX0 - 1)*(self.y-1)/self.depthScale)
            #     self.actualY = int((self.yCur - self.imY0 - 1)*(self.x-1)/self.widthScale)
            if self.x0_bmode == -1:
                self.actualX = int(
                    (self.xCur - self.imX0 - 1) * (self.x - 1) / self.widthScale
                )
                self.actualY = int(
                    (self.yCur - self.imY0 - 1) * (self.y - 1) / self.depthScale
                )
                self.imDrawn = 2
            elif (
                self.imDrawn != 2
                and self.xCur < self.bmodeEndX
                and self.xCur > self.bmodeStartX
                and self.yCur < self.bmodeEndY
                and self.yCur > self.bmodeStartY
            ):
                # self.actualX = int((self.xCur - self.bmodeStartX - 1)*(self.h_bmode - 1)/(self.bmodeEndY - self.bmodeStartY))
                # self.actualY = int((self.yCur - self.bmodeStartY - 1)*(self.w_bmode - 1)/(self.bmodeEndX - self.bmodeStartX))
                self.actualX = int(
                    (self.xCur - self.imX0 - 1) * (self.y - 1) / self.depthScale
                )
                self.actualY = int(
                    (self.yCur - self.imY0 - 1) * (self.x - 1) / self.widthScale
                )
                self.imDrawn = 1
            elif (
                self.imDrawn != 1
                and self.xCur < self.ceEndX
                and self.xCur > self.ceStartX
                and self.yCur < self.ceEndY
                and self.yCur > self.ceStartY
            ):
                # self.actualX = int((self.xCur - self.ceStartX - 1)*(self.h_CE - 1)/(self.ceEndY - self.ceStartY))
                # self.actualY = int((self.yCur - self.ceStartY - 1)*(self.w_CE - 1)/(self.ceEndX - self.ceStartX))
                self.actualX = int(
                    (self.xCur - self.imX0 - 1) * (self.y - 1) / self.depthScale
                )
                self.actualY = int(
                    (self.yCur - self.imY0 - 1) * (self.x - 1) / self.widthScale
                )
                self.imDrawn = 2
            else:
                return
            self.curPointsPlottedX.append(self.actualX)
            self.curPointsPlottedY.append(self.actualY)
            self.updateSpline()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.xCur = event.pos().x()
        self.yCur = event.pos().y()
        # self.updateCrosshair()

    def acceptPolygon(self):
        # 2d interpolation
        if len(self.curPointsPlottedX) > 2:
            self.drawRoiButton.setChecked(False)

            # remove duplicate points
            points = np.transpose(
                np.array([self.curPointsPlottedX, self.curPointsPlottedY])
            )
            points = removeDuplicates(points)
            [self.curPointsPlottedX, self.curPointsPlottedY] = np.transpose(points)
            self.curPointsPlottedX = list(self.curPointsPlottedX)
            self.curPointsPlottedY = list(self.curPointsPlottedY)
            self.curPointsPlottedX.append(self.curPointsPlottedX[0])
            self.curPointsPlottedY.append(self.curPointsPlottedY[0])
            self.maskCoverImg.fill(0)

            xSpline, ySpline = calculateSpline(
                self.curPointsPlottedX, self.curPointsPlottedY
            )
            spline = [(int(xSpline[i]), int(ySpline[i])) for i in range(len(xSpline))]
            spline = np.array([*set(spline)])
            xSpline, ySpline = np.transpose(spline)
            if self.imDrawn == 1:
                xSpline = np.clip(
                    xSpline,
                    a_min=self.x0_bmode + 1,
                    a_max=self.x0_bmode + self.w_bmode - 2,
                )
                ySpline = np.clip(
                    ySpline,
                    a_min=self.y0_bmode + 1,
                    a_max=self.y0_bmode + self.h_bmode - 2,
                )
            elif self.imDrawn == 2:
                xSpline = np.clip(
                    xSpline, a_min=self.x0_CE + 1, a_max=self.x0_CE + self.w_CE - 2
                )
                ySpline = np.clip(
                    ySpline, a_min=self.y0_CE + 1, a_max=self.y0_CE + self.h_CE - 2
                )
            # else:
            #     xSpline = np.clip(xSpline, a_min=1, a_max=self.x-2)
            #     ySpline = np.clip(ySpline, a_min=1, a_max=self.y-2)
            self.oldSpline = []
            for i in range(len(xSpline)):
                self.maskCoverImg[
                    ySpline[i] - 1 : ySpline[i] + 2, xSpline[i] - 1 : xSpline[i] + 2
                ] = [0, 0, 255, 255]
                for j in range(3):
                    self.pointsPlotted.append((xSpline[i] - j, ySpline[i] - j))
                    if not j:
                        self.pointsPlotted.append((xSpline[i] + j, ySpline[i] + j))
            self.curPointsPlottedX = []
            self.curPointsPlottedY = []
            self.redrawRoiButton.setHidden(False)
            self.closeRoiButton.setHidden(True)
            self.roiFitNoteLabel.setHidden(False)
            self.drawRoiButton.setChecked(False)
            self.drawRoiButton.setCheckable(False)
            self.updateIm()
            # self.updateCrosshair()

    def undoLastPoint(self):
        if len(self.curPointsPlottedX) and (not len(self.pointsPlotted)):
            self.maskCoverImg[
                self.curPointsPlottedY[-1] - 2 : self.curPointsPlottedY[-1] + 3,
                self.curPointsPlottedX[-1] - 2 : self.curPointsPlottedX[-1] + 3,
            ] = [0, 0, 0, 0]
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
            self.undoLastPtButton.setHidden(False)
            self.imDrawn = 0
            self.updateIm()
            self.update()

    def computeTic(self):
        times = np.array([i * (1 / self.cineRate) for i in range(self.numSlices)])

        if self.curLeftLineX != -1:
            TIC, self.ticAnalysisGui.roiArea = mc.generate_TIC_no_TMPPV_no_MC(
                self.fullGrayArray, self.segMask, times, 1
            )
        else:
            TIC, self.ticAnalysisGui.roiArea = mc.generate_TIC_no_TMPPV_no_MC(
                self.fullGrayArray, self.segMask, times, 1
            )

        # TIC[:, 1] /= np.amax(TIC[:, 1])

        # Bunch of checks
        if np.isnan(np.sum(TIC[:, 1])):
            print("STOPPED: NaNs in the ROI")
            return
        if np.isinf(np.sum(TIC[:, 1])):
            print("STOPPED: Infs in the ROI")
            return

        self.ticX = np.array([[TIC[i, 0], i] for i in range(len(TIC[:, 0]))])
        self.ticY = TIC[:, 1]
        self.ticAnalysisGui.ax.clear()
        self.ticAnalysisGui.ticX = []
        self.ticAnalysisGui.ticY = []
        self.ticAnalysisGui.removedPointsX = []
        self.ticAnalysisGui.removedPointsY = []
        self.ticAnalysisGui.selectedPoints = []
        self.ticAnalysisGui.t0Index = -1
        self.ticAnalysisGui.graph(self.ticX, self.ticY)
        self.ticAnalysisGui.ticArray = TIC

    def moveToTic(self):
        self.ticAnalysisGui.timeLine = None
        self.computeTic()

        self.ticAnalysisGui.fullPath = self.fullPath
        self.ticAnalysisGui.cineRate, self.ticAnalysisGui.axRes, self.ticAnalysisGui.latRes = self.cineRate, self.axRes, self.latRes
        self.ticAnalysisGui.mc = self.mc
        self.ticAnalysisGui.w_CE, self.ticAnalysisGui.h_CE = self.w_CE, self.h_CE
        self.ticAnalysisGui.w_bmode, self.ticAnalysisGui.h_bmode = self.w_bmode, self.h_bmode
        self.ticAnalysisGui.x0_CE, self.ticAnalysisGui.x0_bmode = self.x0_CE, self.x0_bmode
        self.ticAnalysisGui.y0_CE, self.ticAnalysisGui.y0_bmode = self.y0_CE, self.y0_bmode
        self.ticAnalysisGui.curFrameIndex = self.curFrameIndex
        self.ticAnalysisGui.mcResultsArray = self.mcResultsArray
        self.ticAnalysisGui.segCoverMask = self.segCoverMask
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
        self.ticAnalysisGui.automaticT0Button.setHidden(False)
        self.ticAnalysisGui.updateIm()
        self.ticAnalysisGui.show()
        self.hide()


def calculateSpline(xpts, ypts):  # 2D spline interpolation
    cv = []
    for i in range(len(xpts)):
        cv.append([xpts[i], ypts[i]])
    cv = np.array(cv)
    if len(xpts) == 2:
        tck, _ = interpolate.splprep(cv.T, s=0.0, k=1)
    elif len(xpts) == 3:
        tck, _ = interpolate.splprep(cv.T, s=0.0, k=2)
    else:
        tck, _ = interpolate.splprep(cv.T, s=0.0, k=3)
    x, y = np.array(interpolate.splev(np.linspace(0, 1, 1000), tck))
    return x, y


def removeDuplicates(ar):
    # Credit: https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in ar if not (tuple(x) in seen or seen_add(tuple(x)))]


def find_x0_bmode_CE(ds, CE_side, width):
    if CE_side == "r":
        try:
            print("computing x0_bmode and x0_CE by SequenceOfUltrasoundRegions")
            regions = ds.SequenceOfUltrasoundRegions
            x0_list = [int(reg.RegionLocationMinX0) for reg in regions]
            x0_bmode = min(x0_list)
            x0_CE = max(x0_list)
            w_bmode = int(regions[0].RegionLocationMaxX1) - int(
                regions[0].RegionLocationMinX0
            )
            w_CE = w_bmode
        except (AttributeError, ValueError, NameError, IndexError):
            print("computing x0_bmode and x0_CE by width/2")
            x0_bmode = 0
            x0_CE = int(width / 2)
            w_bmode = int(width / 2)
            w_CE = w_bmode
    elif CE_side == "l":
        try:
            print("computing x0_bmode and x0_CE by SequenceOfUltrasoundRegions")
            regions = ds.SequenceOfUltrasoundRegions
            x0_list = [int(reg.RegionLocationMinX0) for reg in regions]
            x0_bmode = max(x0_list)
            x0_CE = min(x0_list)
            w_bmode = int(regions[0].RegionLocationMaxX1) - int(
                regions[0].RegionLocationMinX0
            )
            w_CE = w_bmode
        except (AttributeError, ValueError, NameError, IndexError):
            print("computing x0_bmode and x0_CE by width/2")
            x0_CE = 0
            x0_bmode = int(width / 2)
            w_bmode = int(width / 2)
            w_CE = w_bmode
    else:
        print("CE side not specified in Excel file")

    return x0_bmode, x0_CE, w_bmode, w_CE


def load_cine(cine_array, color_channel):
    # parameters:
    #    cine_array -- array from ds.pixel_array
    #    color_channel -- ds.PhotometricInterpretation
    # return:
    #    cine_array (frames, height, width, 3), gray_cine_array (frames, height, width)

    if "MONOCHROME" in color_channel:
        if len(cine_array.shape) == 3:  # video (frames, height, width)
            cine_array = np.expand_dims(cine_array, ayis=3)
            cine_array = np.broadcast_to(cine_array, list(cine_array.shape[:-1]) + [3])
        elif len(cine_array.shape) == 2:  # static image (height, width)
            cine_array = np.expand_dims(cine_array, ayis=0)
            cine_array = np.expand_dims(cine_array, ayis=3)
            cine_array = np.broadcast_to(cine_array, list(cine_array.shape[:-1]) + [3])
        else:
            raise Exception("Number of channels does not match MONOCHROME color space")
    else:
        if len(cine_array.shape) == 4:  # video (frames, height, width, 3)
            pass
        elif len(cine_array.shape) == 3:  # static image (height, width, 3)
            cine_array = np.expand_dims(cine_array, axis=0)
        else:
            raise Exception("Number of channels does not match color space")

    # debug
    print(cine_array.shape)
    print(color_channel)

    # convert color channels to RGB and gray
    """
    RGB
    MONOCHROME
    YBR_FULL --> need to convert to RGB
    YBR_RCT --> no need conversion; it is actually stored as RGB
    """
    if "YBR_FULL" in color_channel:
        if color_channel == "YBR_FULL" or color_channel == "YBR_FULL_422":
            if cine_array.shape[-1] == 3:
                pass
            else:
                cine_array = convert_color_space(
                    cine_array, color_channel, "RGB", per_frame=True
                )
        else:
            # swap YBR to YRB first
            cine_array[:, :, :, :] = cine_array[:, :, :, [0, 2, 1]]
            # then convert from YRB to RGB using openCV
            for frame in range(cine_array.shape[0]):
                cine_array[frame, :, :, :] = cv2.cvtColor(
                    cine_array[frame, :, :, :], cv2.COLOR_YCrCb2RGB
                )

    gray_cine_array = np.zeros(cine_array.shape[:-1])
    for frame in range(cine_array.shape[0]):
        gray_cine_array[frame, :, :] = cv2.cvtColor(
            cine_array[frame, :, :, :], cv2.COLOR_RGB2GRAY
        )

    cine_array = cine_array.astype(np.uint8)
    gray_cine_array = gray_cine_array.astype(np.uint8)

    return cine_array, gray_cine_array


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
