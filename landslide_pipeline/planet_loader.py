import planet
from planet.scripts.v1 import download


def load_data(*args, **kwargs):
    from landslide_pipeline.pipeline import LOCATION, TIMES, SATELLITE_INFO, OUTPUT
    import os
    import planet.api as api

    # Set up client:

    api_key = "58613e03d31d4476ae132fbe8bd0afca"
    os.environ["PL_API_KEY"] = api_key

    client = api.ClientV1()

    # Set up query:

    sat_info = SATELLITE_INFO

    coordinates = [
         [
            [
                LOCATION['min_longitude'],
                LOCATION['min_latitude']
            ],
            [
                LOCATION['max_longitude'],
                LOCATION['min_latitude']
            ],
            [
                LOCATION['max_longitude'],
                LOCATION['max_latitude']
            ],
            [
                LOCATION['min_longitude'],
                LOCATION['max_latitude']
            ],
            [
                LOCATION['min_longitude'],
                LOCATION['min_latitude']
            ]
         ]
      ]
    query_and_geofilter = {
        "item_types": sat_info,
        "filter": {
            "type": "AndFilter",
            "config":
                [
                    {
                        "type": "RangeFilter",
                        "field_name": "cloud_cover",
                        "config": {"lte": 0.5}
                    },
                    {
                        "type": "GeometryFilter",
                        "field_name": "geometry",
                        "config":
                            {
                                "type": "Polygon",
                                "coordinates": coordinates
                            }
                    },
                    {
                        "type": "DateRangeFilter",
                        "field_name": "acquired",
                        "config":
                            {
                                "gt": TIMES['start'],
                                "lte": TIMES['end']
                            }
                    }
                ]
        }
    }

    items = client.quick_search(query_and_geofilter)

    # Download items:
    os.mkdir("image_prefixes")
    planet.api.dowloader.create(client, kwargs)
    download(items, "asset_types", "image_prefixes")




    # Save items (if not done so already, making sure they are stored in OUTPUT['output_path']):

    # Put all filenames of all assets into kwargs['image_prefixes']:

    this_args = {'start': TIMES['start'],
                 'end': TIMES['end'],
                 'satellite': SATELLITE_INFO['satellite'],
                 'output_path': OUTPUT['output_path']}
    #image_prefixes = downloads that i get from planet
    #kwargs['image_prefixes'] = <List of strings with location of each downloaded image>
    kwargs.update(this_args)

    return kwargs


'''
    pr = get_paths_rows((LOCATION['min_longitude'], LOCATION['min_latitude']),
                        (LOCATION['max_longitude'], LOCATION['max_latitude']))
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
'''




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
            arg = arg + ['-o', output_filename, '-co', 'PHOTOMETRIC=RGB', '-separate', '-ul_lr', str(union['xmin']),
                         str(union['ymax']), str(union['xmax']), str(union['ymin']), (scene_prefix + '_B3.TIF'),
                         (scene_prefix + '_B2.TIF'), (scene_prefix + '_B1.TIF')]
            import os.path
            if not os.path.isfile(output_filename):
                subprocess.call(arg)
            if kwargs.get('scene_prefixes') is None:
                kwargs['scene_prefixes'] = [scene_prefix]
            else:
                kwargs['scene_prefixes'] += [scene_prefix]
    return kwargs
