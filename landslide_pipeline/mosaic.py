def mosaic(*args, **kwargs):
    
    import glob
    import subprocess
    from landslide_pipeline.pipeline import OUTPUT
    import os
    
    pathrow_dirs = glob.glob(OUTPUT['output_path'] + '/P*R*')
    arg = ['gdalwarp', '-srcnodata', '"0 0 0"']
    
    for pathrow_dir in pathrow_dirs:
        compositor_scene = pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF'
        arg += [compositor_scene]
    
    arg += [OUTPUT['output_path'] + "/" + OUTPUT['output_path'] + '.TIF' ]
    subprocess.call(arg)
    
    kwargs['cloudless_mosaic'] = OUTPUT['output_path'] + "/" + OUTPUT['output_path'] + '.TIF'
    
    return kwargs
    