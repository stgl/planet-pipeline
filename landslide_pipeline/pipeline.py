# pipeline.py
#
# Python script to implement landslide mapping download and processing pipeline.

LS_PIPELINE = ('landslide_pipeline.utils.set_extent_from_landslide_map',
               'landslide_pipeline.planet_mosaic_loader.load_data', # planet data download
               'landslide_pipeline.planet_mosaic_loader.reproject_assets', # planet reprojection
               #'landslide_pipeline.image_chips.create',
               #'landslide_pipeline.image_chips.convert',
               #'landslide_pipeline.image_chips.resample',
               #'landslide_pipeline.tensorflow.chips_to_tfrecords',
               #'landslide_pipeline.tensorflow.train',
               #'landslide_pipeline.tensorflow.export',
               #'landslide_pipeline.tensorflow.classify',
               )


def run_pipeline(pipeline, pipeline_index=0, *args, **kwargs):
    def module_member(name):

        def import_module(name):
            import sys
            __import__(name)
            return sys.modules[name]

        mod, member = name.rsplit('.', 1)
        module = import_module(mod)
        return getattr(module, member)

    out = kwargs.copy()

    # load parameters from pickle if present:

    import pickle, os
    try:
        pipeline_parameters = pickle.load(open(os.path.join(
            out['OUTPUT']['output_path'], out['OUTPUT']['output_path'] + '.p'), 'rb'))
        out.update(pipeline_parameters)
    except FileNotFoundError:
        pass

    # load parameters from file:

    import json
    parameters = json.load(open(out['parameter_file'], 'r'))
    out.update(parameters)

    for idx, name in enumerate(pipeline):
        out['pipeline_index'] = pipeline_index + idx
        func = module_member(name)
        result = func(*args, **out) or {}
        if not isinstance(result, dict):
            return result
        out.update(result)

    # save pipeline parameters to pickle:
    pickle.dump(out, open(os.path.join(
        out['OUTPUT']['output_path'], out['OUTPUT']['output_path'] + '.p'), 'wb'))

    return out

