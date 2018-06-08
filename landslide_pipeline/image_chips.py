def create(*args, **kwargs):
    
    from landslide_pipeline.pipeline import OUTPUT, MIN_AREA, MAP as map
    import os, ogr, subprocess
    
    colorbalanced_scene = OUTPUT['output_path'] + "/" + OUTPUT['output_path'] + '_cb.TIF'
    
    proc = subprocess.Popen(['gdalsrsinfo', '-o', 'wkt', colorbalanced_scene], stdout=subprocess.PIPE)
    projection_info = proc.stdout.read()
    reprojected_map = map + '/' + map + '_reproj.shp'

    subprocess.call(['ogr2ogr', '-s_srs', map + '/' + map + '.prj', '-t_srs', projection_info, '-where', '"Area">={0}'.format(MIN_AREA), reprojected_map, map + '/' + map + '.shp'])

    ds = ogr.Open(reprojected_map, 1)
    lyr = ds.GetLayer(0)
    lyr.ResetReading()
    ft = lyr.GetNextFeature()
    counter = 0
    while ft is not None:
        ft.SetField('id', counter)
        lyr.SetFeature(ft)
        ft = lyr.GetNextFeature()
        counter += 1
    ds = None

    if not os.path.isdir('image_chips'):
        os.mkdir('image_chips')
    ds = ogr.Open(reprojected_map)
    lyr = ds.GetLayer(0)
    lyr.ResetReading()
    ft = lyr.GetNextFeature()
    
    while ft is not None:
        geom=ft.GetGeometryRef()
        extent = geom.GetEnvelope()
        iden = ft.GetField('id')
        chip_name = 'image_chips/chip_' + str(iden) + '.TIF'
        print('chip name: ' + chip_name)
        subprocess.call(['gdalwarp', colorbalanced_scene, chip_name, '-te', str(extent[0]), str(extent[2]), str(extent[1]), str(extent[3])])
        ft = lyr.GetNextFeature() 
        
    
    return kwargs

