from __future__ import division, print_function

import pytest
import numpy as np
from numpy.testing import (assert_almost_equal, assert_array_equal,
                           assert_allclose)
from astropy.io import fits as pyfits
from ..lightcurve import (LightCurve, KeplerLightCurve, TessLightCurve,
                          iterative_box_period_search)
from ..lightcurvefile import KeplerLightCurveFile, TessLightCurveFile

# 8th Quarter of Tabby's star
TABBY_Q8 = ("https://archive.stsci.edu/missions/kepler/lightcurves"
            "/0084/008462852/kplr008462852-2011073133259_llc.fits")
TABBY_TPF = ("https://archive.stsci.edu/missions/kepler/target_pixel_files"
             "/0084/008462852/kplr008462852-2011073133259_lpd-targ.fits.gz")
K2_C08 = ("https://archive.stsci.edu/missions/k2/lightcurves/c8/"
          "220100000/39000/ktwo220139473-c08_llc.fits")
KEPLER10 = ("https://archive.stsci.edu/missions/kepler/lightcurves/"
            "0119/011904151/kplr011904151-2010009091648_llc.fits")
TESS_SIM = ("https://archive.stsci.edu/missions/tess/ete-6/tid/00/000/"
            "004/104/tess2019128220341-0000000410458113-0016-s_lc.fits")


def test_LightCurve():
    err_string = ("Input arrays have different lengths."
                  " len(time)=5, len(flux)=4")
    time = np.array([1, 2, 3, 4, 5])
    flux = np.array([1, 2, 3, 4])

    with pytest.raises(ValueError) as err:
        LightCurve(time=time, flux=flux)
    assert err_string == err.value.args[0]


def test_math_operators():
    lc = LightCurve(time=np.arange(1, 5), flux=np.arange(1, 5), flux_err=np.arange(1, 5))
    lc_add = lc + 1
    lc_sub = lc - 1
    lc_mul = lc * 2
    lc_div = lc / 2
    assert_array_equal(lc_add.flux, lc.flux + 1)
    assert_array_equal(lc_sub.flux, lc.flux - 1)
    assert_array_equal(lc_mul.flux, lc.flux * 2)
    assert_array_equal(lc_div.flux, lc.flux / 2)


def test_rmath_operators():
    lc = LightCurve(time=np.arange(1, 5), flux=np.arange(1, 5), flux_err=np.arange(1, 5))
    lc_add = 1 + lc
    lc_sub = 1 - lc
    lc_mul = 2 * lc
    lc_div = 2 / lc
    assert_array_equal(lc_add.flux, lc.flux + 1)
    assert_array_equal(lc_sub.flux, 1 - lc.flux)
    assert_array_equal(lc_mul.flux, lc.flux * 2)
    assert_array_equal(lc_div.flux, 2 / lc.flux)


@pytest.mark.remote_data
@pytest.mark.parametrize("path, mission", [(TABBY_Q8, "Kepler"), (K2_C08, "K2")])
def test_KeplerLightCurveFile(path, mission):
    lcf = KeplerLightCurveFile(path, quality_bitmask=None)
    hdu = pyfits.open(path)
    kplc = lcf.get_lightcurve('SAP_FLUX')

    assert kplc.channel == lcf.channel
    assert kplc.mission.lower() == mission.lower()
    if kplc.mission.lower() == 'kepler':
        assert kplc.campaign is None
        assert kplc.quarter == 8
    elif kplc.mission.lower() == 'k2':
        assert kplc.campaign == 8
        assert kplc.quarter is None

    assert_array_equal(kplc.time, hdu[1].data['TIME'])
    assert_array_equal(kplc.flux, hdu[1].data['SAP_FLUX'])


@pytest.mark.remote_data
@pytest.mark.parametrize("quality_bitmask",
                         ['hardest', 'hard', 'default', None,
                          1, 100, 2096639])
def test_TessLightCurveFile(quality_bitmask):
    tess_file = TessLightCurveFile(TESS_SIM, quality_bitmask=quality_bitmask)
    hdu = pyfits.open(TESS_SIM)
    tlc = tess_file.SAP_FLUX

    assert tlc.mission.lower() == 'tess'
    assert_array_equal(tlc.time, hdu[1].data['TIME'])
    assert_array_equal(tlc.flux, hdu[1].data['SAP_FLUX'])


@pytest.mark.remote_data
@pytest.mark.parametrize("quality_bitmask, answer", [('hardest', 2661),
    ('hard', 2706), ('default', 3113), (None, 3279),
    (1, 3279), (100, 3252), (2096639, 2661)])
def test_bitmasking(quality_bitmask, answer):
    """Test whether the bitmasking behaves like it should"""
    lcf = KeplerLightCurveFile(TABBY_Q8, quality_bitmask=quality_bitmask)
    flux = lcf.get_lightcurve('SAP_FLUX').flux
    assert len(flux) == answer


def test_lightcurve_fold():
    """Test the ``LightCurve.fold()`` method."""
    lc = LightCurve(time=np.linspace(0, 10, 100), flux=np.zeros(100)+1)
    fold = lc.fold(period=1)
    assert_almost_equal(fold.phase[0], -0.5, 2)
    assert_almost_equal(np.min(fold.phase), -0.5, 2)
    assert_almost_equal(np.max(fold.phase), 0.5, 2)
    fold = lc.fold(period=1, phase=-0.1)
    assert_almost_equal(fold.time[0], -0.5, 2)
    assert_almost_equal(np.min(fold.phase), -0.5, 2)
    assert_almost_equal(np.max(fold.phase), 0.5, 2)


def test_lightcurve_append():
    """Test ``LightCurve.append()``."""
    lc = LightCurve(time=[1, 2, 3], flux=[1, .5, 1])
    lc = lc.append(lc)
    assert_array_equal(lc.flux, 2*[1, .5, 1])
    assert_array_equal(lc.time, 2*[1, 2, 3])
    # KeplerLightCurve has extra data
    lc = KeplerLightCurve(time=[1, 2, 3], flux=[1, .5, 1], quality=[10, 20, 30])
    lc = lc.append(lc)
    assert_array_equal(lc.quality, 2*[10, 20, 30])


def test_lightcurve_append_multiple():
    """Test ``LightCurve.append()`` for multiple lightcurves at once."""
    lc = LightCurve(time=[1, 2, 3], flux=[1, .5, 1])
    lc = lc.append([lc, lc, lc])
    assert_array_equal(lc.flux, 4*[1, .5, 1])
    assert_array_equal(lc.time, 4*[1, 2, 3])


@pytest.mark.remote_data
def test_lightcurve_plot():
    """Sanity check to verify that lightcurve plotting works"""
    lcf = KeplerLightCurveFile(TABBY_Q8)
    lcf.plot()
    lcf.SAP_FLUX.plot()


def test_cdpp():
    """Test the basics of the CDPP noise metric."""
    # A flat lightcurve should have a CDPP close to zero
    assert_almost_equal(LightCurve(np.arange(200), np.ones(200)).cdpp(), 0)
    # An artificial lightcurve with sigma=100ppm should have cdpp=100ppm
    lc = LightCurve(np.arange(10000), np.random.normal(loc=1, scale=100e-6, size=10000))
    assert_almost_equal(lc.cdpp(transit_duration=1), 100, decimal=-0.5)
    # Transit_duration must be an integer (cadences)
    with pytest.raises(ValueError):
        lc.cdpp(transit_duration=6.5)


@pytest.mark.remote_data
def test_cdpp_tabby():
    """Compare the cdpp noise metric against the pipeline value."""
    lcf = KeplerLightCurveFile(TABBY_Q8)
    # Tabby's star shows dips after cadence 1000 which increase the cdpp
    lc = LightCurve(lcf.PDCSAP_FLUX.time[:1000], lcf.PDCSAP_FLUX.flux[:1000])
    assert(np.abs(lc.cdpp() - lcf.header(ext=1)['CDPP6_0']) < 30)


def test_bin():
    lc = LightCurve(time=np.arange(10), flux=2*np.ones(10),
                    flux_err=2**.5*np.ones(10))
    binned_lc = lc.bin(binsize=2)
    assert_allclose(binned_lc.flux, 2*np.ones(5))
    assert_allclose(binned_lc.flux_err, np.ones(5))
    assert len(binned_lc.time) == 5
    with pytest.raises(ValueError):
        lc.bin(method='doesnotexist')


def test_normalize():
    """Does the `LightCurve.normalize()` method normalize the flux?"""
    lc = LightCurve(time=np.arange(10), flux=5*np.ones(10), flux_err=0.05*np.ones(10))
    assert_allclose(np.median(lc.normalize().flux), 1)
    assert_allclose(np.median(lc.normalize().flux_err), 0.05/5)


@pytest.mark.remote_data
def test_iterative_box_period_search():
    """Can we recover the orbital period of Kepler-10b?"""
    answer = 0.837495  # wikipedia
    klc = KeplerLightCurveFile(KEPLER10)
    pdc = klc.PDCSAP_FLUX
    flat, trend = pdc.flatten(return_trend=True)

    _, _, kepler10b_period = iterative_box_period_search(flat, min_period=.5, max_period=1,
                                                         nperiods=101, period_scale='log')
    assert abs(kepler10b_period - answer) < 1e-2


def test_to_pandas():
    """Test the `LightCurve.to_pandas()` method."""
    time, flux, flux_err = range(3), np.ones(3), np.zeros(3)
    lc = LightCurve(time, flux, flux_err)
    try:
        df = lc.to_pandas()
        assert_allclose(df.index, time)
        assert_allclose(df.flux, flux)
        assert_allclose(df.flux_err, flux_err)
    except ImportError:
        # pandas is an optional dependency
        pass


def test_to_table():
    """Test the `LightCurve.to_table()` method."""
    time, flux, flux_err = range(3), np.ones(3), np.zeros(3)
    lc = LightCurve(time, flux, flux_err)
    tbl = lc.to_table()
    assert_allclose(tbl['time'], time)
    assert_allclose(tbl['flux'], flux)
    assert_allclose(tbl['flux_err'], flux_err)


def test_to_csv():
    """Test the `LightCurve.to_csv()` method."""
    time, flux, flux_err = range(3), np.ones(3), np.zeros(3)
    try:
        lc = LightCurve(time, flux, flux_err)
        assert(lc.to_csv() == 'time,flux,flux_err\n0,1.0,0.0\n1,1.0,0.0\n2,1.0,0.0\n')
    except ImportError:
        # pandas is an optional dependency
        pass


def test_date():
    '''Test the lc.date() function'''
    lcf = KeplerLightCurveFile(TABBY_Q8)
    date = lcf.timeobj.iso
    assert len(date) == len(lcf.time)
    assert date[0] == '2011-01-06 20:45:08.811'
    assert date[-1] == '2011-03-14 20:18:16.734'


def test_lightcurve_repr():
    """Do __str__ and __repr__ work?"""
    time, flux = range(3), np.ones(3)
    str(LightCurve(time, flux))
    str(KeplerLightCurve(time, flux))
    str(TessLightCurve(time, flux))
    repr(LightCurve(time, flux))
    repr(KeplerLightCurve(time, flux))
    repr(TessLightCurve(time, flux))


def test_lightcurvefile_repr():
    """Do __str__ and __repr__ work?"""
    lcf = KeplerLightCurveFile(TABBY_Q8)
    str(lcf)
    repr(lcf)
    lcf = TessLightCurveFile(TESS_SIM)
    str(lcf)
    repr(lcf)


def test_slicing():
    """Does LightCurve.__getitem__() allow slicing?"""
    time = np.linspace(0, 10, 10)
    flux = np.linspace(100, 200, 10)
    flux_err = np.linspace(5, 50, 10)
    lc = LightCurve(time, flux, flux_err)
    assert_array_equal(lc[0:5].time, time[0:5])
    assert_array_equal(lc[2::2].flux, flux[2::2])
    assert_array_equal(lc[5:9:-1].flux_err, flux_err[5:9:-1])

    # KeplerLightCurves contain additional data arrays that need to be sliced
    centroid_col = np.linspace(40, 50, 10)
    centroid_row = np.linspace(50, 60, 10)
    quality = np.linspace(70, 80, 10)
    lc = KeplerLightCurve(time, flux, flux_err,
                          centroid_col=centroid_col,
                          centroid_row=centroid_row,
                          quality=quality)
    assert_array_equal(lc[::3].centroid_col, centroid_col[::3])
    assert_array_equal(lc[4:].centroid_row, centroid_row[4:])
    assert_array_equal(lc[10:2].quality, quality[10:2])

    # The same is true for TessLightCurve
    lc = TessLightCurve(time, flux, flux_err,
                        centroid_col=centroid_col,
                        centroid_row=centroid_row,
                        quality=quality)
    assert_array_equal(lc[::4].centroid_col, centroid_col[::4])
    assert_array_equal(lc[5:].centroid_row, centroid_row[5:])
    assert_array_equal(lc[10:3].quality, quality[10:3])


def test_boolean_masking():
    lc = KeplerLightCurve(time=[1, 2, 3], flux=[1, 1, 10], quality=[0, 0, 200])
    assert_array_equal(lc[lc.flux < 5].time, [1, 2])
    assert_array_equal(lc[lc.flux < 5].quality, [0, 0])


def test_remove_nans():
    """Does LightCurve.__getitem__() allow slicing?"""
    time, flux = [1, 2, 3, 4], [100, np.nan, 102, np.nan]
    lc_clean = LightCurve(time, flux).remove_nans()
    assert_array_equal(lc_clean.time, [1, 3])
    assert_array_equal(lc_clean.flux, [100, 102])


def test_remove_outliers():
    time, flux = [1, 2, 3, 4], [1, 1, 1000, 1]
    lc_clean = LightCurve(time, flux).remove_outliers(sigma=1)
    assert_array_equal(lc_clean.time, [1, 2, 4])
    assert_array_equal(lc_clean.flux, [1, 1, 1])


@pytest.mark.remote_data
def test_properties(capfd):
    '''Test if the describe function produces an output.
    The output is 624 characters at the moment, but we might add more properties.'''
    lcf = KeplerLightCurveFile(TABBY_Q8)
    kplc = lcf.get_lightcurve('SAP_FLUX')
    kplc.properties()
    out, err = capfd.readouterr()
    assert len(out) > 500


def test_flatten():
    """Flatten should not remove NaNs."""
    lc = LightCurve(time=[1, 2, 3, 4, 5],
                    flux=[np.nan, 1.1, 1.2, np.nan, 1.4],
                    flux_err=[1.0, np.nan, 1.2, 1.3, np.nan])
    flat_lc = lc.flatten(window_length=3)
    assert(len(flat_lc.time) == 5)
    assert(np.isfinite(flat_lc.flux).sum() == 3)
    assert(np.isfinite(flat_lc.flux_err).sum() == 3)
