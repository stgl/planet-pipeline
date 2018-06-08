def compositor(*args, **kwargs):
    
    import glob
    import subprocess
    from landslide_pipeline.pipeline import OUTPUT
    import os
    
    pathrow_dirs = glob.glob(OUTPUT['output_path'] + '/P*R*')
    for pathrow_dir in pathrow_dirs:
        scenes = glob.glob(pathrow_dir + '/*')
        first_image = glob.glob(scenes[0] + '/*_RGB.TIF')[0]
        arg = ['gdal_merge.py', '-o', pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF', '-createonly', first_image]
        subprocess.call(arg)
    
        arg = ['compositor', '-q', '-o', pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF']
        for scene in scenes:
            scene_filename = glob.glob(scene + '/*_RGB.TIF')[0]
            arg += ['-i', scene_filename]
    
        subprocess.call(arg)
    
        if kwargs.get('cloudless_scene', None) is None:
            kwargs['cloudless_scenes'] = [pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF']
        else:
            kwargs['cloudless_scenes'] += [pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF']
    
    return kwargs
    