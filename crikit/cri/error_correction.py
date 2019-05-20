"""
Created on Mon Jun  6 11:20:35 2016

@author: chc
"""

import numpy as _np
import copy as _copy

from scipy.signal import savgol_filter as _sg

from crikit.cri.algorithms.kk import hilbertfft as _hilbert

from crikit.preprocess.algorithms.als import AlsCvxopt as _AlsCvxopt

from crikit.utils.datacheck import _rng_is_pix_vec


class PhaseErrCorrectALS:
    """
    Phase error correction using alternating least squares (ALS)

    References
    -----------
    * C H Camp Jr, Y J Lee, and M T Cicerone, JRS (2016).
    """
    def __init__(self, smoothness_param=1, asym_param=1e-2,
                 redux=10, order=2, rng=None, fix_end_points=False,
                 fix_rng=None, fix_const=1, max_iter=100, min_diff=1e-5,
                 verbose=True, **kwargs):


        self.rng = _rng_is_pix_vec(rng)
        self._k = kwargs

        self._k.update({'smoothness_param' : smoothness_param,
                        'asym_param' : asym_param,
                        'redux' : redux,
                        'order' : order,
                        'rng' : rng,
                        'fix_end_points' : fix_end_points,
                        'fix_rng' : fix_rng,
                        'fix_const' : fix_const,
                        'max_iter' : max_iter,
                        'min_diff' : min_diff,
                        'verbose' : verbose})


    def _calc(self, data, ret_obj, **kwargs):

        self._inst_als = _AlsCvxopt(**kwargs)

        try:
            # if data.ndim>2:
            shp = data.shape[0:-2]
            total_num = _np.array(shp).prod()
            # else:
            #     shp = ()
            #     total_num = 1
            
            counter = 1
            for idx in _np.ndindex(shp):
                if self._k['verbose']:
                    print('Detrended iteration {} / {}'.format(counter, total_num))
                ph = _np.unwrap(_np.angle(data[idx]))
                # if self.rng is None:
                err_phase = self._inst_als.calculate(ph)
                # else:
                    # err_phase = self._inst_als.calculate(ph[..., self.rng])
                # print('Error phase shape: {}'.format(err_phase.shape))
                # print('Range: {}'.format(self.rng))
                # raise ValueError
                h = _np.zeros(err_phase[..., self.rng].shape)
                h += _hilbert(err_phase[..., self.rng])

                correction_factor = 1/_np.exp(h) * _np.exp(-1j*err_phase[...,self.rng])

                # if self.rng is None:
                #     ret_obj[idx] *= correction_factor
                # else:

                # if len(idx) == 0:
                #     ret_obj[..., self.rng] *= correction_factor
                # else:
                ret_obj[idx][..., self.rng] *= correction_factor
                counter += 1
        except:
            return False
        else:
#            print(self._inst_als.__dict__)
            return True

    def calculate(self, data, **kwargs):
        if self.rng is None:
            self.rng = _np.arange(data.shape[-1])
            
        data_copy = _np.zeros(data.shape, dtype=data.dtype)
        data_copy[..., self.rng] = 1*data[..., self.rng]

        self._k.update(kwargs)

        success = self._calc(data, ret_obj=data_copy, **self._k)
        if success:
            return data_copy
        else:
            return None

    def transform(self, data, **kwargs):
        if self.rng is None:
            self.rng = _np.arange(data.shape[-1])

        total_rng = _np.arange(data.shape[-1])

        not_in_rng = list(set(total_rng).difference(self.rng))
        not_in_rng.sort()
        not_in_rng = _np.array(not_in_rng)

        if not_in_rng.size != 0:
            data[..., not_in_rng] *= 0

        self._k.update(kwargs)

        success = self._calc(data, ret_obj=data, **self._k)
        return success

class ScaleErrCorrectSG:
    """
    Scale error correction using Savitky-Golay

    References
    -----------
    * C H Camp Jr, Y J Lee, and M T Cicerone, JRS (2016).
    """
    def __init__(self, win_size=601, order=2, rng=None):
        self.win_size = win_size
        self.order = order
        self.rng = _rng_is_pix_vec(rng)

    def _calc(self, data, ret_obj):
        try:
            if self.rng is None:
                correction_factor = _sg(data.real, window_length=self.win_size,
                                        polyorder=self.order, axis=-1)
            else:
                correction_factor = _sg(data[..., self.rng].real,
                                        window_length=self.win_size,
                                        polyorder=self.order, axis=-1)

            correction_factor[correction_factor == 0] = 1
            correction_factor **= -1

            if self.rng is None:
                ret_obj *= correction_factor
            else:
                ret_obj[..., self.rng] *= correction_factor
        except:
            return False
        else:
            return True

    def calculate(self, data):
        if self.rng is None:
            self.rng = _np.arange(data.shape[-1])
            
        data_copy = _np.zeros(data.shape, dtype=data.dtype)
        data_copy[..., self.rng] = 1*data[..., self.rng]

        # data_copy = _copy.deepcopy(data)
        success = self._calc(data, ret_obj=data_copy)
        if success:
            return data_copy
        else:
            return None

    def transform(self, data):
        if self.rng is None:
            self.rng = _np.arange(data.shape[-1])

        total_rng = _np.arange(data.shape[-1])

        not_in_rng = list(set(total_rng).difference(self.rng))
        not_in_rng.sort()
        not_in_rng = _np.array(not_in_rng)

        if not_in_rng.size != 0:
            data[..., not_in_rng] *= 0

        success = self._calc(data, ret_obj=data)
        return success


if __name__ == '__main__':  # pragma: no cover

    x = _np.linspace(-100, 100, 1000)

    phi_peak = 10*_np.imag(1/(25-x-1j*2))
    phi_bg = _np.exp(-x**2/(2*30**2))
    phi =  phi_peak + phi_bg
    y = 1*_np.exp(1j*phi)

    y = _np.dot(_np.ones((100,1)), y[None,:])
    # y = _np.reshape(y, (10,10,-1))
    # RSS
    # assert _np.sum((phi_peak-phi)**2) > 265.0
    
    rng = _np.arange(200, 800)
    # rng = None
    pec = PhaseErrCorrectALS(smoothness_param=1, asym_param=1e-3, 
                                redux=10, fix_end_points=True, rng=rng, 
                                verbose=False)

    y_pec = pec.calculate(y)
    # print(y_pec[...,:20])