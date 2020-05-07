def compositor(*args, **kwargs):
    
    import glob
    import subprocess
    from landslide_pipeline.pipeline import OUTPUT, LOCATION
    import os
    
    if kwargs.get('cloudless_scenes', None) is not None:
        return kwargs

    # Check for planet data:

    is_planet = True if kwargs.get('items', None) is not None else False

    ul = (LOCATION['min_longitude'], LOCATION['max_latitude'])
    lr = (LOCATION['max_longitude'], LOCATION['min_latitude'])

    from landslide_pipeline.utils import get_projected_bounds

    (ulp, lrp) = get_projected_bounds(ul, lr)

    if is_planet:
        visual_filenames = [os.path.join(OUTPUT['output_path'], prefix) for prefix in kwargs.get('image_prefixes') if "Visual" in prefix]
        analytic_filenames = [os.path.join(OUTPUT['output_path'], prefix) for prefix in kwargs.get('image_prefixes') if "Analytic" in prefix]
        kwargs['cloudless_scenes'] = {}
        if len(visual_filenames) > 0:
            output_name = os.path.join(OUTPUT['output_path'],OUTPUT['output_path'] + "_Visual.tif")
            arg = ['gdal_merge.py', '-o', output_name, '-createonly', '-of', 'GTiff', '-co',
                   'COMPRESS=LZW', '-ul_lr', ulp[0], ulp[1], lrp[0], lrp[1]] + visual_filenames
            subprocess.call(arg)
            compositor_index = 0
            for visual_filename in visual_filenames:
                arg = ['gdal_merge.py', '-o', '/tmp/visual_' + str(compositor_index) + '.tif', '-of', 'GTiff', '-co',
                       'COMPRESS=LZW', '-ul_lr', ulp[0], ulp[1], lrp[0], lrp[1], output_name, visual_filename]
                subprocess.call(arg)
                compositor_index += 1
            arg = ['compositor', '-q', '-o', output_name]
            for index in range(compositor_index):
                arg += ['-i', '/tmp/visual_' + str(index) + '.tif']
            subprocess.call(arg)
            for index in range(compositor_index):
                os.remove('/tmp/visual_' + str(index) + '.tif')
            kwargs['cloudless_scenes']['visual'] = OUTPUT['output_path'] + '_Visual.tif'
        if len(analytic_filenames) > 0:
            output_name = os.path.join(OUTPUT['output_path'], OUTPUT['output_path'] + "_Analytic.tif")
            arg = ['gdal_merge.py', '-o', output_name, '-createonly', '-of', 'GTiff', '-co',
                   'COMPRESS=LZW', '-ul_lr', ulp[0], ulp[1], lrp[0], lrp[1]] + analytic_filenames
            subprocess.call(arg)
            compositor_index = 0
            for visual_filename in visual_filenames:
                arg = ['gdal_merge.py', '-o', '/tmp/analytic_' + str(compositor_index) + '.tif', '-of', 'GTiff', '-co',
                       'COMPRESS=LZW', '-ul_lr', ulp[0], ulp[1], lrp[0], lrp[1], output_name, visual_filename]
                subprocess.call(arg)
                compositor_index += 1
            arg = ['compositor', '-q', '-o', output_name]
            for index in range(compositor_index):
                arg += ['-i', '/tmp/analytic_' + str(index) + '.tif']
            subprocess.call(arg)
            for index in range(compositor_index):
                os.remove('/tmp/analytic_' + str(index) + '.tif')
            kwargs['cloudless_scenes']['analytic'] = OUTPUT['output_path'] + '_Analytic.tif' 
    else:
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
    
            if kwargs.get('cloudless_scenes', None) is None:
                kwargs['cloudless_scenes'] = [pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF']
            else:
                kwargs['cloudless_scenes'] += [pathrow_dir + '/' + os.path.basename(pathrow_dir) + '.TIF']
    
    return kwargs


def orders_compositor(*args, **kwargs):
    import subprocess, os
    from .utils import get_bounding_box_from_files

    if kwargs.get('cloudless_scene', None) is not None:
        return kwargs

    out = kwargs['OUTPUT']
    filenames = [os.path.join(out['output_path'], out['output_path'] + '_' + str(counter) + '.tif') for counter in range(len(kwargs['item_ids']))]
    bounding_box = get_bounding_box_from_files(filenames)
    output_name = os.path.join(out['output_path'], out['output_path'] + "_composite.tif")

    arg = ['gdal_merge.py', '-o', output_name, '-createonly', '-of', 'GTiff', '-co',
           'COMPRESS=LZW', '-co', 'BIGTIFF=YES', '-ul_lr',str(bounding_box[0]),str(bounding_box[3]),str(bounding_box[1]),str(bounding_box[2]), '-a_nodata', '0', ''] + filenames
    subprocess.call(arg)

    for filename in filenames:
        arg = ['gdal_merge.py', '-o',filename + '_tmp.tif', '-of', 'GTiff', '-co',
               'COMPRESS=LZW', '-ul_lr', str(bounding_box[0]),str(bounding_box[3]),str(bounding_box[1]),str(bounding_box[2]), '-a_nodata', '0', output_name, filename]
        subprocess.call(arg)

    arg = ['compositor', '-q', '-s', 'quality', 'greenest', '-o', output_name]
    for filename in filenames:
        arg += ['-i', filename + '_tmp.tif']
    subprocess.call(arg)

    for filename in filenames:
        os.remove(filename + '_tmp.tif')
    kwargs['cloudless_scene'] = output_name

    return kwargs



