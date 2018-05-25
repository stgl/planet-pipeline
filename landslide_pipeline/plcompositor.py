def compositor(*args, **kwargs):
    
    import subprocess
    base_path = kwargs['output_path']
    first_image = kwargs['scene_prefixes'][0] + '_RGB_scaled.TIF'
    arg = ['gdal_merge.py', '-o', base_path + '/' + base_path + '.TIF', '-createonly', first_image]
    subprocess.call(arg)
    
    arg = ['compositor', '-q', '-o', base_path + '/' + base_path + '.TIF']
    for prefix in kwargs['scene_prefixes']:
        arg += ['-i', prefix + '_RGB_scaled.TIF']
    
    subprocess.call(arg)
    