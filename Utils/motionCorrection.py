"""
Thodsawit Tiyarattanachai, MD
Department of Radiology, Stanford University School of Medicine, California, US
Faculty of Medicine, Chulalongkorn University, Bangkok, Thailand
May 18, 2022
Full paper: "A Comprehensive Motion Compensation Method for In-Plane and Out-of-Plane Motion in Dynamic Contrast-Enhanced Ultrasound of Focal Liver Lesions"
"""

import cv2
import numpy as np
import pickle
from scipy.optimize import curve_fit
import nibabel as nib
from scipy.ndimage import binary_fill_holes


def load_pickle(pickle_path):
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)

    return data

def find_ref_frames_from_nifti(nifti_path, ROI_margin_suffix, search_margin):
    
    nifti_array = np.transpose(nib.load(nifti_path).get_fdata()).astype(int)

    spatial_sum = np.sum(nifti_array, axis=(1, 2))  # shape (frames,)
    ref_frames = np.argwhere(spatial_sum > 0)
    ref_frames = np.reshape(ref_frames, ref_frames.shape[0])

    if ROI_margin_suffix == 'withROImargin':
        ROI_margin = int(search_margin/2)
    elif ROI_margin_suffix == 'withoutROImargin':
        ROI_margin = 0
    
    bboxes = []
    masks = []
    for i,ref_frame in enumerate(ref_frames):
        mask = nifti_array[ref_frame]
        pos_coor = np.argwhere(mask > 0)
        x_values = pos_coor[:, 1]
        y_values = pos_coor[:, 0]
        x0 = x_values.min()
        x1 = x_values.max()
        w = x1 - x0 + 1
        y0 = y_values.min()
        y1 = y_values.max()
        h = y1 - y0 + 1
        
        bboxes.append((x0-ROI_margin,
                       y0-ROI_margin,
                       w+(2*ROI_margin),
                       h+(2*ROI_margin)))
        masks.append(mask[y0-ROI_margin:y0-ROI_margin+h+(2*ROI_margin), 
                          x0-ROI_margin:x0-ROI_margin+w+(2*ROI_margin)])

    return ref_frames, bboxes, masks


def find_correlation(bmode, ref_bmodes, set_quantile):
    # works for multiple reference frames
    #based on cv2.matchTemplate
    
    n_refs = len(ref_bmodes)
    n_frames = bmode.shape[0]
    correlations = np.zeros((n_refs, n_frames))
    
    for ref_idx in range(n_refs):
        ref = ref_bmodes[ref_idx]
        for frame in range(n_frames):
            similarity_map = cv2.matchTemplate(bmode[frame], ref, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(similarity_map)
            correlations[ref_idx, frame] = max_val
            
    correlations = np.mean(correlations, axis=0)
    threshold = np.quantile(correlations, set_quantile)
    
    return correlations, threshold

def compute_similarity_map(search_region, ref_patches, current_ref_idx):
    
    n_refs = len(ref_patches)
    corrs = np.zeros((n_refs,))
    
    for ref_idx in range(n_refs):
        ref = ref_patches[ref_idx]
        similarity_map = cv2.matchTemplate(search_region, ref, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(similarity_map)
        corrs[ref_idx] = max_val
        if current_ref_idx == ref_idx:
            current_max_loc = max_loc
            
    mean_corr = np.mean(corrs)
            
    return mean_corr, current_max_loc

def check_bbox_move(previous_all_lesion_bboxes, all_lesion_bboxes):
    
    bbox_move = False
    
    for frame in range(len(previous_all_lesion_bboxes)):
        previous_bbox = previous_all_lesion_bboxes[frame]
        current_bbox = all_lesion_bboxes[frame]
        if not(previous_bbox is None):
            if not(previous_bbox == current_bbox):
                bbox_move = True
                break
    
    return bbox_move

def getIndTIC(intensities, mode, availableFrames, pixelScale, times):
    if mode == 'ori':
        nFrames = intensities.shape[0]
        availableFrames = np.arange(nFrames)
        availableIntensities = intensities
    elif mode == 'mc':
        availableIntensities = intensities[availableFrames]
    else:
        print("ERROR: Invalid Mode Selected. Must be \"ori\" or \"mc\"")
        return
    availableIntensities *= pixelScale
    availableFrames = times[availableFrames]
    
    tic = np.concatenate([availableFrames[:, np.newaxis], \
                        availableIntensities[:, np.newaxis]], \
                        axis=1)
    
    return tic

def getAllTICs(ceMcRoi, pixelScale, times):
    availableFrames = np.argwhere(np.sum(ceMcRoi, axis=(1,2))>0).flatten()
    ticArray = np.zeros((ceMcRoi.shape[1], ceMcRoi.shape[2], len(availableFrames), 2))
    for x in range(ceMcRoi.shape[1]):
        for y in range(ceMcRoi.shape[2]):
            ticArray[x,y] = getIndTIC(ceMcRoi[:,x,y], 'mc', availableFrames, pixelScale, times)
    return ticArray

def dataFit(tic):
    tmppv = max(tic[:,1])
    tic[:,1] /= tmppv
    normalizedLogParams, normalizedLogParamCov = curve_fit(lognormal, tic[:,0], tic[:,1], \
                                                           p0=(1.0,0.0,1.0), bounds=([0.,0.,0.],\
                                                           [np.inf,np.inf,np.inf]),method='trf')
    
    auc = normalizedLogParams[0]
    mu = normalizedLogParams[1]
    sigma = normalizedLogParams[2]
    mtt = np.exp(mu+(sigma**2/2))
    tp = np.exp(mu - (sigma**2))
    wholeCurve = lognormal(tic[:,0], auc, mu, sigma)
    pe = np.max(wholeCurve)
    return [auc, pe, mtt, tp, tmppv]

def lognormal(x, auc, mu, sigma):      
    curve_fit=(auc/(2.5066*sigma*x))*np.exp((-1/2)*(((np.log(x)-mu)/sigma)**2)) 
    return np.nan_to_num(curve_fit)

def generateParamap(ticArray):
    paramap = np.zeros((ticArray.shape[0], ticArray.shape[1], 5))
    for x in range(ticArray.shape[0]):
        for y in range(ticArray.shape[1]):
            try:
                paramap[x,y] = dataFit(ticArray[x,y].copy())
            except:
                paramap[x,y] = [-1,-1,-1,-1,max(ticArray[x,y,:,1])]
    return paramap

def resize_mc_bboxes(bboxes):
    #resize bboxes to minimum width and height
    
    min_w = min([b[2] for b in bboxes if not(b is None)])
    min_h = min([b[3] for b in bboxes if not(b is None)])
    
    for i in range(len(bboxes)):
        if bboxes[i] is None:
            continue
        x0, y0, w, h = bboxes[i]
        new_w = min_w
        new_h = min_h
        new_x0 = x0 + int((w-new_w)/2)
        new_y0 = y0 + int((h-new_h)/2)
        bboxes[i] = (new_x0, new_y0, new_w, new_h)
        
    return bboxes

def remove_outlier_bboxes(bboxes):
    
    all_x0 = [b[0] for b in bboxes if not(b is None)]
    q1_x0 = np.quantile(all_x0, 0.25)
    q3_x0 = np.quantile(all_x0, 0.75)
    IQR_x0 = q3_x0 - q1_x0
    
    all_y0 = [b[1] for b in bboxes if not(b is None)]
    q1_y0 = np.quantile(all_y0, 0.25)
    q3_y0 = np.quantile(all_y0, 0.75)
    IQR_y0 = q3_y0 - q1_y0
    
    out_bboxes = [None]*len(bboxes)
    outliers = [None]*len(bboxes)
    for i,b in enumerate(bboxes):
        if not(b is None):
            if (b[0]>=q1_x0-(1.5*IQR_x0)) and (b[0]<=q3_x0+(1.5*IQR_x0)) and \
            (b[1]>=q1_y0-(1.5*IQR_y0)) and (b[1]<=q3_y0+(1.5*IQR_y0)):
                out_bboxes[i] = b[:]
            else:
                outliers[i] = b[:]
                
    # print('usable bboxes:', len([b for b in out_bboxes if not(b is None)]))
    # print('outlier bboxes:', len([b for b in outliers if not(b is None)]))
    
    return out_bboxes

def create_ce_mc_bboxes(bmode_bboxes, x0_bmode, x0_CE, CE_side):
    
    CE_bboxes = [None] * len(bmode_bboxes)
    
    for i in range(len(bmode_bboxes)):
        if bmode_bboxes[i] is None:
            continue
        x0, y0, w, h = bmode_bboxes[i]
        
        if CE_side == 'r':
            new_x0 = x0 + (x0_CE-x0_bmode)
        elif CE_side == 'l':
            new_x0 = x0 - (x0_bmode-x0_CE)
        else:
            print('error!')
            quit()
            
        CE_bboxes[i] = (new_x0, y0, w, h)
    
    return CE_bboxes
    
def cut_ROI200(full_array, bboxes, window_loc):
    
    min_w = min([b[2] for b in bboxes if not(b is None)])
    min_h = min([b[3] for b in bboxes if not(b is None)])
    
    window_x0, window_y0, window_w, window_h = window_loc
    
    cut_h = int(max(0.4*window_h, min_h, min_w))
    cut_w = cut_h
    
    ROI = np.zeros((full_array.shape[0], cut_h, cut_w))
    
    for frame in range(full_array.shape[0]):
        bbox = bboxes[frame]
        if bbox is None:  #skip MC frames without bbox (due to out-of-frame motion)
            continue
        x0,y0,w,h = bbox
        x_center = x0 + int(w/2)
        y_center = y0 + int(h/2)
        valid_w = min(int(x_center+cut_w/2),window_x0+window_w) - max(int(x_center-cut_w/2),window_x0)
        valid_h = min(int(y_center+cut_h/2),window_y0+window_h) - max(int(y_center-cut_h/2),window_y0)
        center_ROI = int(cut_h/2)

        try:
            ROI[frame, int(center_ROI-valid_h/2):int(center_ROI+valid_h/2), int(center_ROI-valid_w/2):int(center_ROI+valid_w/2)] = full_array[frame, 
                                    max(int(y_center-cut_h/2),window_y0):min(int(y_center+cut_h/2),window_y0+window_h), 
                                    max(int(x_center-cut_w/2),window_x0):min(int(x_center+cut_w/2),window_x0+window_w)]
        except:
            ROI[frame, int(center_ROI-valid_h/2):int(center_ROI+valid_h/2), int(center_ROI-valid_w/2):int(center_ROI+valid_w/2)] = full_array[frame, 
                                    max(int(y_center-cut_h/2+1),window_y0):min(int(y_center+cut_h/2),window_y0+window_h), 
                                    max(int(x_center-cut_w/2+1),window_x0):min(int(x_center+cut_w/2),window_x0+window_w)]
    
    return ROI
    
    
def generate_TIC(window, bboxes, times, compression, pixelScale, refFrame):
    TICtime = []
    TIC = []
    areas = []
    for t in range(0, window.shape[0]):
        if bboxes[t] != None:
            tmpwin = window[t]
            bool_mask = np.zeros(tmpwin.shape, dtype=bool)
            x0, y0, x_len, y_len = bboxes[t]
            for x in range(x_len):
                bool_mask[y0,x] = True
                bool_mask[y0+y_len, x] = True
            for y in range(y_len):
                bool_mask[y, x0] = True
                bool_mask[y, x0+x_len-1] = True
            bool_mask = binary_fill_holes(bool_mask)
            numPoints = len(np.where(bool_mask == True)[0])
            TIC.append(np.exp(tmpwin[bool_mask]/compression).mean()*pixelScale)
            TICtime.append(times[t])
            areas.append(pixelScale*numPoints)

    TICz = np.array([TICtime, TIC]).astype('float64')
    TICz = TICz.transpose()
    TICz[:,1]=TICz[:,1]-np.mean(TICz[0:2,1])#Subtract noise in TIC before contrast
    if TICz[np.nan_to_num(TICz)<0].any():#make the smallest number in TIC 0
        TICz[:,1]=TICz[:,1]+np.abs(np.min(TICz[:,1]))
    else:
        TICz[:,1]=TICz[:,1]-np.min(TICz[:,1])
    return TICz, np.round(np.mean(areas), decimals=2)

def generate_TIC_no_TMPPV(window, bboxes, times, compression, refFrame):
    TICtime = []
    TIC = []
    areas = []
    for t in range(0, window.shape[0]):
        if bboxes[t] != None:
            tmpwin = window[t]
            bool_mask = np.zeros(tmpwin.shape, dtype=bool)
            x0, y0, x_len, y_len = bboxes[t]
            if y0+y_len >= bool_mask.shape[0]:
                y_len = bool_mask.shape[0] - y0 - 1
            if x0+x_len >= bool_mask.shape[1]:
                x_len = bool_mask.shape[0] - x0 - 1
            bool_mask[y0:y0+y_len, x0:x0+x_len] = True
            # for x in range(x_len):
            #     bool_mask[y0,x] = True
            #     bool_mask[y0+y_len, x] = True
            # for y in range(y_len):
            #     bool_mask[y, x0] = True
            #     bool_mask[y, x0+x_len] = True
            # bool_mask = binary_fill_holes(bool_mask)
            numPoints = len(np.where(bool_mask == True)[0])
            TIC.append(np.exp(tmpwin[bool_mask]/compression).mean())
            TICtime.append(times[t])
            areas.append(numPoints)

    TICz = np.array([TICtime, TIC]).astype('float64')
    TICz = TICz.transpose()
    TICz[:,1]=TICz[:,1]-np.mean(TICz[0:2,1])#Subtract noise in TIC before contrast
    if TICz[np.nan_to_num(TICz)<0].any():#make the smallest number in TIC 0
        TICz[:,1]=TICz[:,1]+np.abs(np.min(TICz[:,1]))
    else:
        TICz[:,1]=TICz[:,1]-np.min(TICz[:,1])
    return TICz, np.round(np.mean(areas), decimals=2)