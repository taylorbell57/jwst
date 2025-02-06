import pytest
from jwst.regtest.st_fitsdiff import STFITSDiff as FITSDiff
from astropy.table import Table, setdiff

from jwst.lib.set_telescope_pointing import add_wcs
from jwst.stpipe import Step


@pytest.fixture(scope="module")
def run_pipelines(rtdata_module):
    """Run stage 2-3 tso pipelines on NIRCAM TSO grism data."""
    rtdata = rtdata_module

    # Run tso-spec2 pipeline on the _rateints file, saving intermediate products
    rtdata.get_data("nircam/tsgrism/jw01366002001_04103_00001-seg001_nrcalong_rateints.fits")
    args = ["calwebb_spec2", rtdata.input,
            "--steps.flat_field.save_results=True",
            "--steps.extract_2d.save_results=True",
            "--steps.srctype.save_results=True"
            ]
    Step.from_cmdline(args)

    # Get the level3 association json file (though not its members) and run
    # the tso3 pipeline on all _calints files listed in association
    rtdata.get_data("nircam/tsgrism/jw01366-o002_20230107t004627_tso3_00001_asn.json")
    args = ["calwebb_tso3", rtdata.input]
    Step.from_cmdline(args)

    return rtdata


@pytest.fixture(scope="module",
                params=["jw01185015001_03104_00001-seg004_nrcalong_rate.fits",
                        "jw01185013001_04103_00001-seg003_nrcalong_rate.fits"])
def run_pipeline_offsetSR(request, rtdata_module):
    rtdata = rtdata_module
    rtdata.get_data("nircam/tsgrism/" + request.param)
    args = ["calwebb_spec2", rtdata.input,
            "--steps.extract_1d.save_results=True",]
    Step.from_cmdline(args)
    return rtdata


@pytest.mark.bigdata
def test_nircam_tsgrism_stage2_offsetSR(run_pipeline_offsetSR, fitsdiff_default_kwargs):
    """
    Test coverage for offset special requirement specifying nonzero offset in X.

    Test data are two observations of Gliese 436, one with offset specified and one without.
    Quantitatively we just ensure that the outputs are identical to the inputs, but qualitatively
    can check that the spectral lines fall at the same wavelengths in both cases,
    which is why the zero-offset case is also included here."""
    rtdata = run_pipeline_offsetSR
    rtdata.output = rtdata.input.replace("rate", "x1d")
    rtdata.get_truth("truth/test_nircam_tsgrism_stages/" + rtdata.output.split('/')[-1])

    diff = FITSDiff(rtdata.output, rtdata.truth, **fitsdiff_default_kwargs)
    assert diff.identical, diff.report()


@pytest.mark.bigdata
@pytest.mark.parametrize("suffix", ["calints", "extract_2d", "flat_field",
                                    "o002_crfints", "srctype", "x1dints"])
def test_nircam_tsgrism_stage2(run_pipelines, fitsdiff_default_kwargs, suffix):
    """Regression test of tso-spec2 pipeline performed on NIRCam TSO grism data."""
    rtdata = run_pipelines
    rtdata.input = "jw01366002001_04103_00001-seg001_nrcalong_rateints.fits"
    output = "jw01366002001_04103_00001-seg001_nrcalong_" + suffix + ".fits"
    rtdata.output = output

    rtdata.get_truth("truth/test_nircam_tsgrism_stages/" + output)

    diff = FITSDiff(rtdata.output, rtdata.truth, **fitsdiff_default_kwargs)
    assert diff.identical, diff.report()


@pytest.mark.bigdata
def test_nircam_tsgrism_stage3_x1dints(run_pipelines, fitsdiff_default_kwargs):
    rtdata = run_pipelines
    rtdata.input = "jw01366-o002_20230107t004627_tso3_00001_asn.json"
    rtdata.output = "jw01366-o002_t001_nircam_f322w2-grismr-subgrism256_x1dints.fits"
    rtdata.get_truth("truth/test_nircam_tsgrism_stages/jw01366-o002_t001_nircam_f322w2-grismr-subgrism256_x1dints.fits")

    diff = FITSDiff(rtdata.output, rtdata.truth, **fitsdiff_default_kwargs)
    assert diff.identical, diff.report()


@pytest.mark.bigdata
def test_nircam_tsgrism_stage3_whtlt(run_pipelines):
    rtdata = run_pipelines
    rtdata.input = "jw01366-o002_20230107t004627_tso3_00001_asn.json"
    rtdata.output = "jw01366-o002_t001_nircam_f322w2-grismr-subgrism256_whtlt.ecsv"
    rtdata.get_truth("truth/test_nircam_tsgrism_stages/jw01366-o002_t001_nircam_f322w2-grismr-subgrism256_whtlt.ecsv")

    table = Table.read(rtdata.output)
    table_truth = Table.read(rtdata.truth)

    # setdiff returns a table of length zero if there is no difference
    assert len(setdiff(table, table_truth)) == 0


@pytest.mark.bigdata
def test_nircam_setpointing_tsgrism(rtdata, fitsdiff_default_kwargs):
    """
    Regression test of the set_telescope_pointing script on a level-1b NIRCam file.
    """
    rtdata.get_data("nircam/tsgrism/jw02459001001_03103_00001-seg001_nrcalong_uncal.fits")
    # The add_wcs function overwrites its input
    rtdata.output = rtdata.input

    # Call the WCS routine
    add_wcs(rtdata.input)

    rtdata.get_truth("truth/test_nircam_setpointing/jw02459001001_03103_00001-seg001_nrcalong_uncal.fits")

    fitsdiff_default_kwargs['rtol'] = 1e-6
    diff = FITSDiff(rtdata.output, rtdata.truth, **fitsdiff_default_kwargs)
    assert diff.identical, diff.report()
