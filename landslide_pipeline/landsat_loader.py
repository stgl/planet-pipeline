from landsat import landsat_cli

def load_data(*args, **kwargs):

    from landslide_pipeline.pipeline import LOCATION, TIMES, SATELLITE_INFO, OUTPUT
    from landslide_pipeline.utils import get_paths_rows
    
    pr = get_paths_rows((LOCATION['min_longitude'], LOCATION['min_latitude']), (LOCATION['max_longitude'], LOCATION['max_latitude']))
    import glob
    for (path, row) in pr:
        
    
        this_args = {'row': str(row),
            'path': str(path),
            'start': TIMES['start'],
            'end': TIMES['end'],
            'satellite': SATELLITE_INFO['satellite'],
            'output_path': OUTPUT['output_path'] + '/P' + str(path) + 'R' + str(row)}
    
        landsat_cli.main(this_args)    
    
    this_args.pop('row', None)
    this_args.pop('path', None)
    kwargs['image_prefixes'] = glob.glob(OUTPUT['output_path'] + '/*/*')
    kwargs.update(this_args)
    return kwargs


def rgb_scenes(*args, **kwargs):
    import glob
    import subprocess
    from landslide_pipeline.pipeline import OUTPUT
    
    pathrow_dirs = glob.glob(OUTPUT['output_path'] + '/P*R*')
    
    for pathrow_dir in pathrow_dirs:
        scenes = glob.glob(pathrow_dir + '/*')
        band1_filenames = glob.glob(pathrow_dir + '/*/*_B1.TIF')
        from utils import extent_union_of_files
        union = extent_union_of_files(band1_filenames)
        
        for scene in scenes:
            arg = ['gdal_merge.py']
            scene_prefix = glob.glob(scene + '/*_B1.TIF')[0].replace('_B1.TIF', '')   
            output_filename = scene_prefix + '_RGB.TIF'   
            arg = arg + ['-o', output_filename, '-co', 'PHOTOMETRIC=RGB', '-separate', '-ul_lr', str(union['xmin']), str(union['ymax']), str(union['xmax']), str(union['ymin']), (scene_prefix + '_B3.TIF'), (scene_prefix + '_B2.TIF'), (scene_prefix + '_B1.TIF')]
            import os.path
            if not os.path.isfile(output_filename):
                subprocess.call(arg)        
            if kwargs.get('scene_prefixes') is None:
                kwargs['scene_prefixes'] = [scene_prefix]
            else:
                kwargs['scene_prefixes'] += [scene_prefix]

        
    return kwargs