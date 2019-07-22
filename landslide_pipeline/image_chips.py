def create(**kwargs):

    if kwargs.get('chips') is not None:
        return kwargs

    import os, ogr, subprocess

    cloudless_scenes = kwargs['cloudless_scenes']
    output = kwargs['OUTPUT']
    map_name = kwargs['LANDSLIDE_MAP']['name']
    map_area_field = kwargs['LANDSLIDE_MAP']['area_field']
    min_area = kwargs['LANDSLIDE_MAP']["minimum_area"]
    reprojected_map = os.path.join(map_name, map_name + '_reproj.shp')

    subprocess.call(['ogr2ogr', '-s_srs', os.path.join(map_name, map_name + '.prj'), '-t_srs', 'EPSG:' +
                     str(output['output_projection']), reprojected_map, os.path.join(map_name, map_name + '.shp')])

    if not os.path.isdir('image_chips'):
        os.mkdir('image_chips')

    chips = []

    ds = ogr.Open(reprojected_map, 1)
    lyr = ds.GetLayer(0)
    lyr.ResetReading()
    ft = lyr.GetNextFeature()

    feature_count = 0

    while ft is not None:
        if ft.GetField(map_area_field) >= min_area:

            geom = ft.GetGeometryRef()
            extent = geom.GetEnvelope()

            for cloudless_scene in cloudless_scenes:

                raster_count = 0

                left = extent[0]
                right = extent[1]
                top = extent[2]
                bottom = extent[3]

                coordinates = {'xmin': left,
                               'xmax': right,
                               'ymin': bottom,
                               'ymax': top}

                chip_name = 'chip_' + str(feature_count) + '_' + str(raster_count)
                import os
                subprocess.call(['gdalwarp', cloudless_scene, os.path.join('image_chips', chip_name + '.TIF'), '-te',
                                 str(left), str(bottom), str(right), str(top)])
                chips += [{'name': chip_name,
                           'coordinates': coordinates}]
                raster_count += 1
            feature_count += 1
        ft = lyr.GetNextFeature()

    kwargs['chips'] = chips
    return kwargs


def convert(**kwargs):
    
    import os, subprocess, glob
    
    chips = glob.glob(os.path.join('image_chips', '*.TIF'))
    
    for chip in chips:
        chip_output = chip.replace('.TIF','.png')
        subprocess.call(['convert', chip, chip_output])
        os.remove(chip)

    return kwargs


def resample(*args, **kwargs):

    from landslide_pipeline.utils import resample_image
    import glob, os
    from PIL import Image

    max_chip_dimension = kwargs['MAX_CHIP_DIMENSION']
    chips = glob.glob(os.path.join('image_chips','*.png'))

    for chip in chips:
        image = Image.open(chip)
        image = resample_image(image, max_dim_size=max_chip_dimension)
        image.save(chip)

    return kwargs

