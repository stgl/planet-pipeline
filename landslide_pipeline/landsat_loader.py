from landsat import landsat_cli

def load_data(*args, **kwargs):

    from landslide_pipeline.pipeline import LOCATION, TIMES, SATELLITE_INFO, OUTPUT
    
    this_args = {'latitude': LOCATION['latitude'],
            'longitude': LOCATION['longitude'],
            'start': TIMES['start'],
            'end': TIMES['end'],
            'satellite': SATELLITE_INFO['satellite'],
            'output_path': OUTPUT['output_path']}
    
    landsat_cli.main(this_args)
    
    import os
    kwargs['image_prefixes'] = os.listdir(OUTPUT['output_path'])
    kwargs.update(this_args)
    return kwargs


def rgb_scenes(*args, **kwargs):
    import glob
    band1_filenames = glob.glob(kwargs['output_path'] + '/*/*_B1.TIF')
    from utils import extent_union_of_files
    union = extent_union_of_files(band1_filenames)
    
    for prefix in kwargs['image_prefixes']:
        import subprocess
        arg = ['gdal_merge.py']
        
        base_path = kwargs['output_path'] + '/' + prefix
        scene_prefix = glob.glob(base_path + '/' + '*_B1.TIF')[0].replace('_B1.TIF', '')
        arg = arg + ['-o', (scene_prefix + '_RGB.TIF'), '-co', 'PHOTOMETRIC=RGB', '-separate', '-ul_lr', str(union['xmin']), str(union['ymax']), str(union['xmax']), str(union['ymin']), (scene_prefix + '_B3.TIF'), (scene_prefix + '_B2.TIF'), (scene_prefix + '_B1.TIF')]
        subprocess.call(arg)
        arg = ['gdal_translate']
        arg = arg + [(scene_prefix + '_RGB.TIF'), (scene_prefix + '_RGB_scaled.TIF'), '-scale', '0', '255', '0', '255', '-exponent', '0.5', '-co', 'PHOTOMETRIC=RGB']
        subprocess.call(arg)
        if kwargs.get('scene_prefixes') is None:
            kwargs['scene_prefixes'] = [scene_prefix]
        else:
            kwargs['scene_prefixes'] += [scene_prefix]
        
    return kwargs