# pipeline.py
#
# Python script to implement landslide mapping download and processing pipeline.
import sys


LOCATION = {'min_latitude': 30.4,
            'min_longitude': 102.4,
            'max_latitude': 32.8,
            'max_longitude': 105.1}

TIMES = {'start': '2008-05-22',
         'end': '2009-05-22'}

SATELLITE_INFO = {'satellite': 5}

OUTPUT = {'output_path': 'wenchuan'}

CB_PERCENT = 5.0

LS_PIPELINE = ('landslide_pipeline.landsat_loader.load_data', # landsat_loader download
               'landslide_pipeline.landsat_loader.rgb_scenes',
               'landslide_pipeline.plcompositor.compositor', # merge image set into cloud-free(ish) mosaic
               'landslide_pipeline.mosaic.mosaic',
               'landslide_pipeline.color.correct',
               'landslide_pipeline.image_chips.create',
               )

STRETCH_STD = 2.0

MAP = 'wenchuan_landslide_map'
MIN_AREA = 2.5E5

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
