def create(*args, **kwargs):
    
    from landslide_pipeline.pipeline import OUTPUT, MIN_AREA, CHIP_SIZE, MAP as map
    import os, ogr, subprocess
    from osgeo import gdal
    import json
    
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

    raster_ds = gdal.Open(colorbalanced_scene)
    (_, pixelSizeX, _, _, _, pixelSizeY) = raster_ds.GetGeoTransform()
    pixelSizeY = -pixelSizeY
    
    if not os.path.isdir('image_chips'):
        os.mkdir('image_chips')
    ds = ogr.Open(reprojected_map)
    lyr = ds.GetLayer(0)
    lyr.ResetReading()
    ft = lyr.GetNextFeature()
    
    while ft is not None:
        geom=ft.GetGeometryRef()
        extent = geom.GetEnvelope()
        centerX = (extent[1] + extent[0]) / 2.0
        centerY = (extent[3] + extent[2]) / 2.0
        
        left = centerX - CHIP_SIZE / 2.0 * pixelSizeX
        right = centerX + CHIP_SIZE / 2.0 * pixelSizeX
        top = centerY + CHIP_SIZE / 2.0 * pixelSizeY
        bottom = centerY - CHIP_SIZE / 2.0 * pixelSizeY
        
        width = right - left
        height = top - bottom
        
        normalized_coordinates = {'xmin': (extent[0] - left) / width,
                                  'xmax': (extent[1] - left) / width,
                                  'ymin': (extent[2] - bottom) / height,
                                  'ymax': (extent[3] - bottom) / height }
        iden = ft.GetField('id')
        chip_name = 'image_chips/chip_' + str(iden) 
        subprocess.call(['gdalwarp', colorbalanced_scene, chip_name + '.TIF', '-te', str(left), str(bottom), str(right), str(top)])
        json.dump(normalized_coordinates, open(chip_name + '.json', 'w'))
        ft = lyr.GetNextFeature() 
        
    
    return kwargs

def convert(*args, **kwargs):
    
    import os, subprocess, glob
    
    chips = glob.glob('image_chips/*.TIF')
    
    for chip in chips:
        chip_output = chip.replace('.TIF','.png')
        subprocess.call(['convert', chip, chip_output]);
        os.remove(chip)

    return kwargs
    
def resample(*args, **kwargs):

    from landslide_pipeline.pipeline import MAX_CHIP_DIMENSION
    from landslide_pipeline.utils import resample_image
    import glob
    from PIL import Image

    chips = glob.glob('image_chips/*.png')

    for chip in chips:
        image = Image.open(chip)
        image = resample_image(image, max_dim_size=MAX_CHIP_DIMENSION)
        image.save(chip)

    return kwargs

