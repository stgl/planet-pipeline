# pipeline.py
#
# Python script to implement landslide mapping download and processing pipeline.
import sys


LOCATION = {'latitude': 31.021,
            'longitude': 103.367}
TIMES = {'start': '2008-05-22',
         'end': '2009-05-22'}

SATELLITE_INFO = {'satellite': 5}

OUTPUT = {'output_path': 'wenchuan'}

LS_PIPELINE = ('landslide_pipeline.landsat_loader.load_data', # landsat_loader download
               'landslide_pipeline.landsat_loader.rgb_scenes',
               'landslide_pipeline.plcompositor.compositor', # merge image set into cloud-free(ish) mosaic
               #'pipeline.record_last_time_instrument_was_contacted',
               #'pipeline.transfer_new_data',
               #'pipeline.record_new_data_that_was_transferred',
#               'pipeline.load_summary_ec_data',
#               'pipeline.filter_data',
#               'pipeline.write_excel_spreadsheet',
#               'pipeline.plot_data_within_time_window',
#               'ec_inversion.invert_data',
#               'ec_inversion.plot_inversion_results_within_time_window',
               )

def import_module(name):
    __import__(name)
    return sys.modules[name]

def module_member(name):
    mod, member = name.rsplit('.', 1)
    module = import_module(mod)
    return getattr(module, member)

def run_pipeline(pipeline, pipeline_index=0, *args, **kwargs):
    out = kwargs.copy()

    for idx, name in enumerate(pipeline):
        out['pipeline_index'] = pipeline_index + idx
        func = module_member(name)
        result = func(*args, **out) or {}
        if not isinstance(result, dict):
            return result
        out.update(result)
    return out
