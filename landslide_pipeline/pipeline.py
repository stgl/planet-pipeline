# pipeline.py
#
# Python script to implement landslide mapping download and processing pipeline.

LS_PIPELINE = ('landslide_pipeline.utils.set_extent_from_landslide_map',
               'landslide_pipeline.planet_loader.load_data', # planet data download
               #'landslide_pipeline.planet_mosaic_loader.reproject_assets', # planet reprojection
               #'landslide_pipeline.image_chips.define',
               #'landslide_pipeline.image_chips.refine',
               #'landslide_pipeline.image_chips.create',
               #'landslide_pipeline.image_chips.resample',
               #'landslide_pipeline.tensorflow.chips_to_tfrecords',
               #'landslide_pipeline.tensorflow.train',
               #'landslide_pipeline.tensorflow.export',
               #'landslide_pipeline.tensorflow.classify',
               )

MONTHLY_ANALYTIC_PIPELINE = ('landslide_pipeline.planet_orders_loader.load_data',
                             'landslide_pipeline.planet_orders_loader.clip',
                             'landslide_pipeline.planet_orders_loader.toar',
                             'landslide_pipeline.planet_orders_loader.compositor',
                             'landslide_pipeline.planet_orders_loader.cycle_orders',
                             'landslide_pipeline.plcompositor.orders_compositor',
                             'landslide_pipeline.planet_orders_loader.clean_up_orders',
                             'landslide_pipeline.utils.clip_cloudless_scene')

SINGLE_MONTHLY_ANALYTIC_PIPELINE = ('landslide_pipeline.planet_orders_loader.load_data',
                             'landslide_pipeline.planet_orders_loader.clip',
                             'landslide_pipeline.planet_orders_loader.toar',
                             'landslide_pipeline.planet_orders_loader.compositor',
                             'landslide_pipeline.planet_orders_loader.cycle_orders',
                             'landslide_pipeline.planet_orders_loader.clean_up_orders')


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

    # load parameters from file:
    if out.get('parameter_file', None) is not None:
        import json
        parameters = json.load(open(out['parameter_file'], 'r'))
        out.update(parameters)

    # Remove API key from out if it exists:
    out.pop('PL_API_KEY', None)

    # Read API key from environmental variable:
    import os
    out['PL_API_KEY'] = os.environ['PL_API_KEY']

    # load parameters from pickle if present:

    import pickle, os
    if not os.path.exists(os.path.join(out['OUTPUT']['output_path'])):
        os.makedirs(os.path.join(out['OUTPUT']['output_path']))
    try:
        pipeline_parameters = pickle.load(open(os.path.join(out['OUTPUT']['output_path'], out['OUTPUT']['output_path']+'.p'), 'rb'))
        out.update(pipeline_parameters)
    except FileNotFoundError:
        pass

    # load parameters from file:

    if out.get('parameter_file', None) is not None:
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

def load_template(filename):

    import json
    return json.load(open(filename, 'r'))

