
from typing import List

import numpy as np

class SpectralResults:
    def __init__(self):
        self.mbf: float  # midband fit
        self.ss: float  # spectral slope
        self.si: float  # spectral intercept
        self.atCoef: float  # attenuation coefficient
        self.nps: np.ndarray  # normalized power spectrum
        self.ps: np.ndarray  # image power spectrum
        self.rPs: np.ndarray  # phantom power spectrum
        self.f: np.ndarray  # frequency array

class Window:
    def __init__(self):
        self.left: int 
        self.right: int 
        self.top: int 
        self.bottom: int 
        self.results = SpectralResults()

class Config:
    def __init__(self):
        self.transducerFreqBand: List[int]  # [min, max] (Hz)
        self.analysisFreqBand: List[int]  # [lower, upper] (Hz)
        self.samplingFrequency: int  # Hz
        self.axWinSize: float  # axial length per window (mm)
        self.latWinSize: float  # lateral width per window (mm)
        self.windowThresh: float  # % of window area required to be in ROI
        self.axialOverlap: float  # % of ax window length to move before next window
        self.lateralOverlap: float  # % of lat window length to move before next window
        self.centerFrequency: float  # Hz

class UltrasoundImage:
    def __init__(self):
        self.scBmode: np.ndarray # rgb
        self.bmode: np.ndarray # rgb
        self.rf: np.ndarray
        self.phantomRf: np.ndarray
        self.axialResRf: float # mm/pix
        self.lateralResRf: float # mm/pix
        self.xmap: np.ndarray # maps (y,x) in SC coords to x preSC coord
        self.ymap: np.ndarray # maps (y,x) in SC coords to y preSC coord
        