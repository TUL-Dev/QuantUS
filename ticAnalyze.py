from scipy.optimize import curve_fit
import numpy as np

def generate_TIC(window, mask, times, compression, voxelscale=1):
    TICtime = times
    TIC = []
    bool_mask = np.array(mask, dtype=bool)
    for t in range(window.shape[0]):
        tmpwin = window[t]
        TIC.append(np.exp(tmpwin[bool_mask] / compression).mean() * voxelscale)
    TICz = np.array([TICtime, TIC]).astype("float64")
    TICz = TICz.transpose()
    TICz[:, 1] = TICz[:, 1] - np.mean(TICz[0:2, 1])
    # Substract noise in TIC before contrast.
    if TICz[np.nan_to_num(TICz) < 0].any():  # make the smallest number in the TIC 0.
        TICz[:, 1] = TICz[:, 1] + np.abs(np.min(TICz[:, 1]))
    else:
        TICz[:, 1] = TICz[:, 1] - np.min(TICz[:, 1])
    return TICz

def data_fit(TIC, normalizer, autoT0):
    t0 = 0
    if not autoT0:
        normalizedLogParams, _ = curve_fit(
            lognormal,
            TIC[0],
            TIC[1],
            p0=(1.0, 0.0, 1.0),
            bounds=([0.0, 0.0, 0.0], [np.inf, np.inf, np.inf]),
            method="trf",
        )  # p0=(1.0,3.0,0.5,0.1) ,**kwargs
        wholeCurve = lognormal(
            TIC[0],
            normalizedLogParams[0],
            normalizedLogParams[1],
            normalizedLogParams[2],
        )
    else:
        normalizedLogParams, _ = curve_fit(
            lognormal_t0,
            TIC[0],
            TIC[1],
            p0=(1.0, 0.0, 1.0, 0.0),
            bounds=([0.0, 0.0, 0.0, 0.0], [np.inf, np.inf, np.inf, np.inf]),
            method="trf",
        )  # p0=(1.0,3.0,0.5,0.1) ,**kwargs
        t0 = normalizedLogParams[3]
        wholeCurve = lognormal_t0(
            TIC[0],
            normalizedLogParams[0],
            normalizedLogParams[1],
            normalizedLogParams[2],
            t0,
        )

    # popt = np.around(normalizedLogParams, decimals=1);
    popt = normalizedLogParams

    auc = popt[0]
    mu = popt[1]
    sigma = popt[2]
    mtt = np.exp(mu + (sigma**2 / 2))
    # print("brute force auc:", sklearn.metrics.auc(TIC[0], wholeCurve))
    tp = np.exp(mu - (sigma**2))
    pe = np.max(wholeCurve)
    params = np.array(np.around(np.array([pe, auc, tp, mtt, t0]), decimals=1))
    params[0] = np.around(pe, decimals=3)

    wholeCurve *= normalizer
    return params, popt, wholeCurve


def lognormal(x, auc, mu, sigma):
    curve_fit = (auc / (2.5066 * sigma * x)) * np.exp(
        (-1 / 2) * (((np.log(x) - mu) / sigma) ** 2)
    )
    return np.nan_to_num(curve_fit)


def lognormal_t0(x, auc, mu, sigma, t0):
    curve_fit = (auc / (2.5066 * sigma * (x - t0))) * np.exp(
        -1 * (((np.log(x - t0) - mu) ** 2) / (2 * sigma * sigma))
    )
    return np.nan_to_num(curve_fit)

