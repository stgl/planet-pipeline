# pipeline.py
#
# Python script to implement landslide mapping download and processing pipeline.
import sys

DEBUG = True


LOCATION = {'min_latitude': 30.4,
            'min_longitude': 102.4,
            'max_latitude': 32.8,
            'max_longitude': 105.1}
'''

LOCATION = {'min_latitude': 37.4146,
            'min_longitude': -122.1834,
            'max_latitude': 37.4383,
            'max_longitude': -122.1561}
'''

SATELLITE_INFO = ['PSOrthoTile', 'REOrthoTile']
TIMES = {'start': "2019-06-01T00:00:00",
         'end': "2019-07-01T18:59:00"}

MAX_ACQUISITIONS = 10
TILE_MAX_PIXELS = 5000



OUTPUT = {'output_path': 'wenchuan',
          'output_projection': 32648}


'''
OUTPUT = {'output_path': 'stanford',
          'output_projection': 32610}
'''


CB_PERCENT = 5.0
'''
LS_PIPELINE = (#'landslide_pipeline.landsat_loader.load_data', # landsat_loader download
               #'landslide_pipeline.landsat_loader.rgb_scenes',
               #'landslide_pipeline.plcompositor.compositor', # merge image set into cloud-free(ish) mosaic
               #'landslide_pipeline.mosaic.mosaic',
               #'landslide_pipeline.color.correct',
               #'landslide_pipeline.image_chips.create',
               #'landslide_pipeline.image_chips.convert',
               #'landslide_pipeline.tensorflow.chips_to_tfrecords',
               #'landslide_pipeline.tensorflow.train',
               #'landslide_pipeline.tensorflow.export',
               'landslide_pipeline.tensorflow.classify',
               )

'''

LS_PIPELINE = ('landslide_pipeline.io.load_pipeline', 
               'landslide_pipeline.planet_mosaic_loader.load_data', # planet data download
               'landslide_pipeline.planet_mosaic_loader.reproject_assets', # planet reprojection
               'landslide_pipeline.io.save_pipeline',
               #'landslide_pipeline.plcompositor.compositor', # merge image set into cloud-free(ish) mosaic
               #'landslide_pipeline.mosaic.mosaic',
               #'landslide_pipeline.color.correct',
               #'landslide_pipeline.image_chips.create',
               #'landslide_pipeline.image_chips.convert',
               #'landslide_pipeline.image_chips.resample',
               #'landslide_pipeline.tensorflow.chips_to_tfrecords',
               #'landslide_pipeline.tensorflow.train',
               #'landslide_pipeline.tensorflow.export',
               #'landslide_pipeline.tensorflow.classify',
               )

MAX_CHIP_DIMENSION = 100

STRETCH_STD = 2.0

CHIP_SIZE = 300

TRAINING_FRACTION = 0.7
TRAINING_EXEC_PATH = '/Users/hilley/Documents/GitHub/models/research/object_detection/train.py'
EVAL_EXEC_PATH = '/Users/hilley/Documents/GitHub/models/research/object_detection/eval.py'
TRAINING_CONFIG_PATH = './models/faster_rcnn_resnet101_landslides.config'
TRAINING_PATH = './models/model/train'
EVAL_PATH = './models/model/eval'

TRAINING_EXPORT_EXEC_PATH = '/Users/hilley/Documents/GitHub/models/research/object_detection/export_inference_graph.py'
TRAINING_EXPORT_PATH = './models/model/export'

MAP = 'wenchuan_landslide_map'
MIN_AREA = 2.5E5

CLASSIFY_IMAGE = 'wenchuan/wenchuan_clip_cb.jpg'

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

