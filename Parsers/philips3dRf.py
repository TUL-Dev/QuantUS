import os

from scipy.io import loadmat
from scipy.signal import hilbert
import numpy as np

from Parsers.philipsSipVolumeParser import ScParams, scanConvert3dVolumeSeries, readScVdbParams

class FileStruct():
    def __init__(self, filedirectory, filename):
        self.name = filename
        self.directory = filedirectory

class DataOutputStruct():
    def __init__(self):
        self.scRF = None
        self.scBmode = None
        self.rf = None
        self.bMode = None

class InfoStruct():
    def __init__(self):
        self.minFrequency = 3000000
        self.maxFrequency = 15000000
        self.lowBandFreq = 1000000
        self.upBandFreq = 6000000
        self.depth = None
        self.centerFrequency = 9000000 #Hz

        # For B-Mode image rendering
        self.clipFact = 0.95 
        self.dynRange = 55
       
        self.studyMode = None
        self.filename = None
        self.filepath = None
        self.probe = None
        self.system = None
        self.studyID = None
        self.studyEXT = None
        self.samples = None
        self.lines = None
        self.depthOffset = None
        self.depth = None
        self.width = None
        self.rxFrequency = None
        self.samplingFrequency = None
        self.txFrequency = None
        self.targetFOV = None
        self.numFocalZones = None
        self.numFrames = None
        self.frameSize = None
        self.depthAxis = None
        self.widthAxis = None
        self.lineDensity = None
        self.pitch = None
        self.yOffset = None
        self.xOffset = None
        self.gain = None
        self.rxGain = None
        self.userGain = None
        self.txPower = None
        self.power = None
        self.PRF = None
        self.width = None
        self.lateralRes = None
        self.axialRes = None
        self.maxval = None

        # Philips Specific - may repeat and need clean up
        self.tilt1 = None
        self.width1 = None
        self.startDepth1 = None
        self.endDepth1 = None
        self.endHeight = None
        self.clip_fact = None
        self.dyn_range = None
        self.numSonoCTAngles = None

        # One if preSC, the other is postSC resolutions
        self.yResRF = None 
        self.xResRF = None
        self.yRes = None
        self.xRes = None

        # Quad 2 or accounting for change in line density
        self.quad2x = None



def getImage(filename, filedirectory, refname, refdirectory):
    Files = FileStruct(filedirectory, filename)
    RefFiles = FileStruct(refdirectory, refname)

    [ImgInfo, RefInfo, ImgData, RefData] = getData(Files, RefFiles)
    
    return ImgData.scBmode, ImgData, ImgInfo, RefData, RefInfo



def getData(Files, RefFiles):
    input = loadmat(str(Files.directory + Files.name))
    ImgInfo, scParams = readFileInfo(Files.name, Files.directory)
    [ImgData, ImgInfo] = readFileImg(ImgInfo, input, scParams)

    input = loadmat(str(RefFiles.directory + RefFiles.name))
    RefInfo, scParams = readFileInfo(RefFiles.name, RefFiles.directory)
    [RefData, RefInfo] = readFileImg(RefInfo, input, scParams)

    return [ImgInfo, RefInfo, ImgData, RefData]

def readFileInfo(filename, filepath, pixPerMm=1.2):    
    studyID = filename[:-4]
    studyEXT = filename[-4:]

    # Input paths/filenames
    vdbFilename = str(filename[:-4] + "_Extras.txt")

    scParams = readScVdbParams(os.path.join(filepath, vdbFilename))
    if scParams.NUM_PLANES is None:
        scParams.NUM_PLANES = 20
    if scParams.pixPerMm is None:
        scParams.pixPerMm = pixPerMm

    Info = InfoStruct()
    Info.studyMode = "RF"
    Info.filename = filename
    Info.filepath = filepath
    Info.probe = "C5-?"
    Info.system = "EPIQ7"
    Info.studyID = studyID
    Info.studyEXT = studyEXT
    # Info.samples = input["pt"][0][0]
    # Info.lines = np.array(input["rf_data_all_fund"]).shape[0]
    Info.depthOffset = 0.04 # probeStruct.transmitoffset
    Info.depth = 0.16 #?
    Info.width = 70 #?
    Info.rxFrequency = 20000000
    Info.samplingFrequency = 20000000
    Info.txFrequency = 3200000
    Info.targetFOV = 0
    Info.numFocalZones = 1
    # Info.numFrames = input["NumFrame"][0][0]
    Info.frameSize = np.nan
    Info.depthAxis = np.nan
    Info.widthAxis = np.nan
    # Info.lineDensity = input["multilinefactor"][0][0]
    Info.pitch = 0
    Info.yOffset = 0
    Info.xOffset = 0
    Info.gain = 0
    Info.rxGain = 0
    Info.userGain = 0
    Info.txPower = 0
    Info.power = 0
    Info.PRF = 0

    # Philips Specific
    Info.tilt1 = 0
    Info.width1 = 70
    Info.startDepth1 = 0.04
    Info.endDepth1 = 0.16
    Info.endHeight = 500
    Info.clip_fact = 0.95
    # Info.numSonoCTAngles = input["NumSonoCTAngles"][0][0]
    
    Info.yResRF = 1
    Info.xResRF = 1
    Info.yRes = 1
    Info.xRes = 1
    Info.quad2x = 1

    return Info, scParams

def readFileImg(Info, input, scParams):
    echoData = input["rf_data_all_fund"]# indexing works by frame, angle, image
    while not(len(echoData[0].shape) > 1 and echoData[0].shape[0]>40 and echoData[0].shape[1]>40):
        echoData = echoData[0]
    echoData = np.array(echoData).astype(np.int32)

    # echoData = np.real(input["IQData"])
    # bmode = 20*np.log10(abs(input["IQData"]))
    # bmode = np.clip(bmode, (0.95*np.amax(bmode)-55), 0.95*np.amax(bmode)).astype(np.float)
    # bmode -= np.amin(bmode)
    # bmode *= (255/np.amax(bmode))

    bmode = np.zeros(echoData.shape).astype(np.int32)

    # Do Hilbert Transform on each column
    for fnum in range(echoData.shape[0]):
        for i in range(echoData.shape[2]):
            bmode[fnum,:,i] = 20*np.log10(abs(hilbert(echoData[fnum,:,i])))

    ModeIM = echoData

    # scBmode = None #np.array([bmode.shape[0]]+[])
    # scModeIM = None #np.array(ModeIM.shape)
    scBmode, bmodeDims = scanConvert3dVolumeSeries(bmode, scParams)
    scRf, rfDims = scanConvert3dVolumeSeries(ModeIM, scParams)

    # for fnum in range(echoData.shape[0]):
    #     if scBmode is None:
    #         [firstScBmode, hCm1, wCm1, _] = scanConvert(bmode[fnum], Info.width1, Info.tilt1, Info.startDepth1, Info.endDepth1, Info.endHeight)
    #         [_, hCm1, wCm1, firstScBmodeIM] = scanConvert(ModeIM[fnum], Info.width1, Info.tilt1, Info.startDepth1, Info.endDepth1, Info.endHeight)
    #         scBmode = np.zeros(tuple([bmode.shape[0]])+firstScBmode.shape)
    #         scBmode[fnum] = firstScBmode
    #         scModeIM = np.zeros([ModeIM.shape[0]], dtype=object)
    #         scModeIM[fnum] = firstScBmodeIM
    #     else:
    #         [scBmode[fnum], hCm1, wCm1, _] = scanConvert(bmode[fnum], Info.width1, Info.tilt1, Info.startDepth1, Info.endDepth1, Info.endHeight)
    #         [_, hCm1, wCm1, scModeIM[fnum]] = scanConvert(ModeIM[fnum], Info.width1, Info.tilt1, Info.startDepth1, Info.endDepth1, Info.endHeight)

    # Info.lateralRes = wCm1*10/scBmode.shape[2]
    # Info.axialRes = hCm1*10/scBmode.shape[1]
    # Info.depth = hCm1
    # Info.width = wCm1
    Info.maxval = np.amax(scBmode)

    Data = DataOutputStruct()
    Data.scRF = scRf
    Data.scBmode = scBmode * (255/Info.maxval)
    Data.rf = ModeIM
    Data.bMode = bmode * (255/np.amax(bmode))
    
    # Data.scRF = ModeIM
    # Data.scBmode = bmode
    # Info.maxval = np.amax(bmode)

    # Info.depth = 126.8344
    # Info.width = Info.depth*bmode.shape[0]/bmode.shape[1]
    # Info.lateralRes = Info.width/bmode.shape[0]
    # Info.axialRes = Info.depth/bmode.shape[1]

    return Data, Info

if __name__ == "__main__":
    getImage('FatQuantData1.mat', '/Users/davidspector/Documents/MATLAB/Data/', 'FatQuantPhantom1.mat', '/Users/davidspector/Documents/MATLAB/Data/', 0)