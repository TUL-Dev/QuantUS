from numpy import matlib
import numpy as np
from PIL import Image, ImageDraw

class RoiPositionsStruct():
    def __init__(self):
        self.left = []
        self.right = []
        self.top = []
        self.bottom = []

def roiWindowsGenerator(
    xspline, yspline, # The spline parameters
    axialNum, lateralNum, # Number of pixels along the axial and lateral sides of the image
    axialRSize, lateralRSize, # Window size in mm - user inputted via GUI
    axialRes, lateralRes, # Axial and lateral image resolution in mm/pixel - width/lines, height/samples
    axialOverlap, lateralOverlap, # Percent overlap - user inputted via GUI
    thresholdPercentage, xmap=[], ymap=[] # Contains coordindates xmap and ymap for preSC conversion
):

    # Some axial/lateral dims
    axialSize = round(axialRSize/axialRes) # in pixels :: mm/(mm/pixel)
    lateralSize = round(lateralRSize/lateralRes)
    axial = list(range(axialNum))
    lateral = list(range(lateralNum))
    xRegionCoords = xspline
    yRegionCoords = yspline

    # Overlap fraction determines the incremental distance between ROIs
    axialIncrement = axialSize * (1-axialOverlap)
    lateralIncrement = lateralSize * (1-lateralOverlap)

    # ROI sizes in pixels
    axialRoiSizePixels = round(axialSize/(axial[1]-axial[0]))
    lateralRoiSizePixels = round(lateralSize/(lateral[1]-lateral[0]))

    # Determine ROIS - Find Region to Iterate Over
    axialStart = max(min(yRegionCoords), axial[0])
    axialEnd = min(max(yRegionCoords), axial[-1]-axialSize)
    lateralStart = max(min(xRegionCoords), lateral[0])
    lateralEnd = min(max(xRegionCoords), lateral[-1]-lateralSize)

    # Determine ROI set
    roiPositions = RoiPositionsStruct()
    if len(xmap) != 0:
        roiPositionsPreSC = RoiPositionsStruct()

    # Determine all points inside the user-defined polygon that defines analysis region
    # The 'mask' matrix - "1" inside region and "0" outside region
    # Pair x and y spline coordinates 
    spline = []
    if len(xspline) != len(yspline):
        print ("Spline has unequal amount of x and y coordinates")
        return 
    for i in range(len(xspline)):
        spline.append((xspline[i], yspline[i]))

    img = Image.new('L', (lateralNum, axialNum), 0)
    ImageDraw.Draw(img).polygon(spline, outline=1, fill=1)
    mask = np.array(img)

    for axialPos in np.arange(axialStart, axialEnd, axialIncrement):
        for lateralPos in np.arange(lateralStart, lateralEnd, lateralIncrement):

            # Convert axial and lateral positions in mm to Indices
            axialAbsAr = abs(axial-axialPos)
            axialInd = np.where(axialAbsAr == min(axialAbsAr))[0][0]
            lateralAbsAr = abs(lateral-lateralPos)
            lateralInd = np.where(lateralAbsAr == min(lateralAbsAr))[0][0]

            # Determine if ROI is Inside Analysis Region
            maskVals = mask[axialInd:(axialInd+axialRoiSizePixels), lateralInd:(lateralInd+lateralRoiSizePixels)]

            # Define Percentage Threshold
            totalNumberOfElementsInRegion = maskVals.size
            numberOfOnesInRegion = len(np.where(maskVals==1)[0])
            percentageOnes = numberOfOnesInRegion/totalNumberOfElementsInRegion 
            
            if percentageOnes>(thresholdPercentage/100):
                # Add ROI to output structure, quantize back to valid distances
                roiPositions.left.append(int(lateral[lateralInd]))
                roiPositions.right.append(int(lateral[lateralInd+lateralRoiSizePixels-1]))
                roiPositions.top.append(int(axial[axialInd]))
                roiPositions.bottom.append(int(axial[axialInd+axialRoiSizePixels-1]))

                if len(xmap) != 0:
                    # PreSC conversion
                    roiPositionsPreSC.left.append(int(np.floor(xmap[int(np.floor(axialInd)), int(np.floor(lateralInd))])))
                    roiPositionsPreSC.right.append(int(np.ceil(xmap[int(np.floor(axialInd)), int(np.floor(lateralInd+lateralRoiSizePixels-1))])))
                    roiPositionsPreSC.top.append(int(np.floor(ymap[int(np.floor(axialInd)), int(np.floor(lateralInd))])))
                    roiPositionsPreSC.bottom.append(int(np.floor(ymap[int(np.ceil(axialInd+axialRoiSizePixels-1)), int(np.floor(lateralInd))])))
    
    if len(xmap) != 0:
        return roiPositions, roiPositionsPreSC
    return roiPositions

def computePowerSpec(RFData, startFrequency, endFrequency, samplingFrequency):

    # Create Hanning Window Function
    unrmWind = np.hanning(RFData.shape[0])
    windFuncComputations = unrmWind*np.sqrt(len(unrmWind)/sum(np.square(unrmWind)))
    windFunc = matlib.repmat(windFuncComputations.reshape((RFData.shape[0],1)),1,RFData.shape[1])

    # Frequency Range
    frequency = np.linspace(0, samplingFrequency, 8192)
    fLow = round(startFrequency*(8192/samplingFrequency))
    fHigh = round(endFrequency*(8192/samplingFrequency))
    freqChop = frequency[fLow:fHigh]

    # Get PS
    windFunc = np.ones(windFunc.shape)
    fft = np.square(abs(np.fft.fft(np.transpose(np.multiply(RFData,windFunc)),8192)*RFData.size))
    fullPS = 20*np.log10(np.mean(fft, axis=0))

    ps = fullPS[fLow:fHigh]

    return freqChop, ps


def spectralAnalysisDefault6db(npsNormalized, f, db6LowF, db6HighF):

    # 1. in one scan / run-through of data file's f array, find the data points on
    # the frequency axis closest to reference file's 6dB window's LOWER bound and UPPER bounds
    smallestDiffDb6LowF = 999999999
    smallestDiffDb6HighF = 999999999

    for i in range(len(f)):
        currentDiffDb6LowF = abs(db6LowF - f[i])
        currentDiffDb6HighF = abs(db6HighF - f[i])
        
        if currentDiffDb6LowF < smallestDiffDb6LowF:
            smallestDiffDb6LowF = currentDiffDb6LowF
            smallestDiffIndexDb6LowF = i
        
        if currentDiffDb6HighF < smallestDiffDb6HighF:
            smallestDiffDb6HighF = currentDiffDb6HighF
            smallestDiffIndexDb6HighF = i
        

    # 2. compute linear regression within the 6dB window
    fBand = f[smallestDiffIndexDb6LowF:smallestDiffIndexDb6HighF] # transpose row vector f in order for it to have same dimensions as column vector nps
    p = np.polyfit(fBand, npsNormalized[smallestDiffIndexDb6LowF:smallestDiffIndexDb6HighF],1)
    npsLinfit = np.polyval(p,fBand) # y_linfit is a column vecotr
    """Check this"""

    # Compute linear regression residuals
    npsResid = npsNormalized[smallestDiffIndexDb6LowF:smallestDiffIndexDb6HighF]-npsLinfit
    npsSsResid = sum(np.square(npsResid))
    npsSsTotal = (len(npsNormalized-1))*np.var(npsNormalized)
    rsqu = 1 - (npsSsResid/npsSsTotal)

    # Compute spectral parameters
    ib = 0
    for i in range(smallestDiffIndexDb6LowF,smallestDiffIndexDb6HighF):
        ib += npsNormalized[i]*i 
    """May supposed to be *i+1"""
    
    mbfit = p[0]*fBand[round(fBand.shape[0]/2)]+p[1]

    return mbfit, fBand, npsLinfit, p, rsqu, ib

def computeSpecWindowsIQ(
    imgRF, refRF, top, bottom, left, right,
    minFrequency, maxFrequency, imgLowBandFreq, imgUpBandFreq,
    imgSamplingFreq
):

    # Set some flags
    db6LowF = imgLowBandFreq #.txFrequency - 3000000, hardcoded
    db6HighF = imgUpBandFreq #.txFrequency - 3000000, hardcoded

    # Frequency params
    fs = imgSamplingFreq*2 # Not sure why multiply by two here, but it's the only way it works ~ Ahmed?
    """Look into this"""
    f0 = minFrequency  
    f1 = maxFrequency
    fRange = round(f1*(8192/fs)) - round(f0*(8192/fs))

    # Output pre-allocation
    if len(top) >= 1:
        imNps = np.zeros((len(top),fRange))
        imPs = np.zeros((len(top),fRange))
        imF = np.zeros((len(top),fRange)) 
        """Find out why zeros are different dimensions for different filetypes (.rfd vs .rf, etc)"""
        imRps = np.zeros((len(top), fRange))
        imWinTopBottomDepth = np.zeros((len(top),2))
        imWinLeftRightWidth = np.zeros((len(top),2))
        imMbf = np.zeros(len(top))
        imSs = np.zeros(len(top))
        imSi = np.zeros(len(top))
    else:
        imNps = []
        imPs = []
        imF = []
        imRps = []
        imWinTopBottomDepth = []
        imWinLeftRightWidth = []

    # Compute spectral parameters for each window
    for i in range(len(top)):

        # Make some adjustments and find the window to use
        imgWindow = imgRF[top[i]:bottom[i],left[i]:right[i]]
        refWindow = refRF[top[i]:bottom[i],left[i]:right[i]]

        [f, ps] = computePowerSpec(imgWindow, f0, f1, fs) # initially had round(img_gain), but since not used in function, we left it out
        [f, rPS] = computePowerSpec(refWindow, f0, f1, fs) # Same as above, except for round(ref_gain)
        # [f, ps] = eng.computePowerSpec(matlab.double(np.ascontiguousarray(imgWindow)), matlab.double(f0), matlab.double(f1), matlab.double(fs), 0, nargout=2)
        # [f, rPS] = eng.computePowerSpec(matlab.double(np.ascontiguousarray(refWindow)), matlab.double(f0), matlab.double(f1), matlab.double(fs), 0, nargout=2)
        nps = np.asarray(ps)-np.asarray(rPS) # SUBTRACTION method: log data
        # import matplotlib.pyplot as plt
        # fig, ax = plt.subplots()
        # ax.scatter(f,ps)
        # # plt.vlines([imgLowBandFreq, imgUpBandFreq], ymin=min(ps), ymax=max(ps), colors="green")
        # plt.show()
        # return

        # Get ready to send output
        for j in range(fRange):
            # imNps[i,j]=nps[0][j]
            # imPs[i,j]=ps[0][j]
            # imRps[i,j]=rPS[0][j]
            # imF[i,j]=f[0][j]
            imNps[i,j]=nps[j]
            imPs[i,j]=ps[j]
            imRps[i,j]=rPS[j]
            imF[i,j]=f[j]
        imWinLeftRightWidth[i,0]=left[i]
        imWinLeftRightWidth[i,1]=right[i]
        imWinTopBottomDepth[i,0]=top[i]
        imWinTopBottomDepth[i,1]=bottom[i]

        # Compute QUS parameters
        [mbfit, _, _, p, _, _] = spectralAnalysisDefault6db(nps, f, db6LowF, db6HighF)
        # [mbfit, _, _, p, _, _] = eng.spectralAnalysisDefault6db(matlab.double(np.ascontiguousarray(nps)), matlab.double(f), matlab.double(db6LowF), matlab.double(db6HighF), matlab.double(2), nargout=6)
        imMbf[i]=mbfit
        # imSs[i]=p[0][0]
        # imSi[i]=p[0][1]
        imSs[i]=p[0]
        imSi[i]=p[1]

    return imWinTopBottomDepth, imWinLeftRightWidth, imMbf, imSs, imSi, imF[0], imNps



def computeSpecWindows(
    imgRF, refRF, top, bottom, left, right,
    minFrequency, maxFrequency, imgLowBandFreq, imgUpBandFreq,
    imgSamplingFreq, frame, phantName=None
):

    # Set some flags
    db6LowF = imgLowBandFreq #.txFrequency - 3000000, hardcoded
    db6HighF = imgUpBandFreq #.txFrequency - 3000000, hardcoded

    # Frequency params
    # fs = imgSamplingFreq*2 # Not sure why multiply by two here, but it's the only way it works ~ Ahmed?
    fs = imgSamplingFreq
    f0 = minFrequency  
    f1 = maxFrequency
    fRange = round(f1*(8192/fs)) - round(f0*(8192/fs))

    # Output pre-allocation
    if len(top) >= 1:
        imNps = np.zeros((len(top),fRange))
        imPs = np.zeros((len(top),fRange))
        imF = np.zeros((len(top),fRange)) 
        """Find out why zeros are different dimensions for different filetypes (.rfd vs .rf, etc)"""
        imRps = np.zeros((len(top), fRange))
        imWinTopBottomDepth = np.zeros((len(top),2))
        imWinLeftRightWidth = np.zeros((len(top),2))
        imMbf = np.zeros(len(top))
        imSs = np.zeros(len(top))
        imSi = np.zeros(len(top))
    else:
        imNps = []
        imPs = []
        imF = []
        imRps = []
        imWinTopBottomDepth = []
        imWinLeftRightWidth = []

    # Compute spectral parameters for each window
    for i in range(len(top)):

        # Make some adjustments and find the window to use
        if frame is None:
            imgWindow = imgRF[top[i]:bottom[i],left[i]:right[i]]
            refWindow = refRF[top[i]:bottom[i],left[i]:right[i]]
        else:
            imgWindow = imgRF[frame,top[i]:bottom[i],left[i]:right[i]]
            if phantName == 'uri_SpV2232_VpF512_FpA90_20210129103529.rfd':
                refWindow = refRF[top[i]:bottom[i], left[i]:right[i]]
            else:
                refWindow = refRF[frame,top[i]:bottom[i],left[i]:right[i]]

        [f, ps] = computePowerSpec(imgWindow, f0, f1, fs) # initially had round(img_gain), but since not used in function, we left it out
        [f, rPS] = computePowerSpec(refWindow, f0, f1, fs) # Same as above, except for round(ref_gain)
        nps = np.asarray(ps)-np.asarray(rPS) # SUBTRACTION method: log data
        # import matplotlib.pyplot as plt
        # fig, ax = plt.subplots()
        # ax.scatter(f,ps)
        # # plt.vlines([imgLowBandFreq, imgUpBandFreq], ymin=min(ps), ymax=max(ps), colors="green")
        # plt.show()
        # return

        # Get ready to send output
        for j in range(fRange):
            # imNps[i,j]=nps[0][j]
            # imPs[i,j]=ps[0][j]
            # imRps[i,j]=rPS[0][j]
            # imF[i,j]=f[0][j]
            imNps[i,j]=nps[j]
            imPs[i,j]=ps[j]
            imRps[i,j]=rPS[j]
            imF[i,j]=f[j]
        imWinLeftRightWidth[i,0]=left[i]
        imWinLeftRightWidth[i,1]=right[i]
        imWinTopBottomDepth[i,0]=top[i]
        imWinTopBottomDepth[i,1]=bottom[i]

        # Compute QUS parameters
        [mbfit, _, _, p, _, _] = spectralAnalysisDefault6db(nps, f, db6LowF, db6HighF)
        # [mbfit, _, _, p, _, _] = eng.spectralAnalysisDefault6db(matlab.double(np.ascontiguousarray(nps)), matlab.double(f), matlab.double(db6LowF), matlab.double(db6HighF), matlab.double(2), nargout=6)
        imMbf[i]=mbfit
        # imSs[i]=p[0][0]
        # imSi[i]=p[0][1]
        imSs[i]=p[0]
        imSi[i]=p[1]

    return imWinTopBottomDepth, imWinLeftRightWidth, imMbf, imSs, imSi, imF[0], imNps