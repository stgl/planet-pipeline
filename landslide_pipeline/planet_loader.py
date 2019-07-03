
def load_data(**kwargs):
    from landslide_pipeline.pipeline import LOCATION, TIMES, SATELLITE_INFO, OUTPUT, DEBUG
    import os
    import planet.api as api
    import requests
    from landslide_pipeline.pipeline import OUTPUT

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

    items = client.quick_search(query_and_geofilter, page_size=250)

    num_items = 0
    for _ in items.items_iter(250):
        num_items += 1
    print('Query returned ' + str(num_items) + ' items.')

    # Download items:
    output_directory = os.path.join(os.getcwd(), OUTPUT['output_path'])
    try:
        os.mkdir(output_directory)
    except:
        pass

    from concurrent.futures import ThreadPoolExecutor, as_completed
    executor = ThreadPoolExecutor(5)

    all_futures = []

    def activate_and_download(item):

        # setup auth
        session = requests.Session()
        session.auth = (api_key, '')

        assets = client.get_assets(item).get()
        asset_futures = []

        def activate_and_download_asset_type(asset_type):
            activated = False
            while not activated:
                dataset = \
                    session.get(
                        ("https://api.planet.com/data/v1/item-types/" +
                        "{}/items/{}/assets/").format(item['properties']['item_type'], item['id']))
                # extract the activation url from the item for the desired asset
                item_activation_url = dataset.json()[asset_type]["_links"]["activate"]
                # request activation
                response = session.post(item_activation_url)
                activated = (response.status_code == 204)
                if not activated:
                    print("Waiting for activation of: ", item['id'])
                    import time
                    time.sleep(30.0)
            asset = client.get_assets(item).get()[asset_type]
            callback = api.write_to_file(directory=output_directory, callback=None, overwrite=True)
            name = client.download(asset, callback=callback).wait().name
            return name, item

        if assets.get('visual', None) is not None:
            asset_futures += [executor.submit(activate_and_download_asset_type, 'visual')]
        if assets.get('analytic', None) is not None and not DEBUG:
            asset_futures += [executor.submit(activate_and_download_asset_type, 'analytic')]

        return asset_futures

    for item_i in items.items_iter(250):
        all_futures += activate_and_download(item_i)

    results = []

    for result in as_completed(all_futures):
        results += [result.result()]
        print('Finished downloading asset.', result.result()[0])

    # Put all filenames of all assets into kwargs['image_prefixes']:

    this_args = {'start': TIMES['start'],
                 'end': TIMES['end'],
                 'satellite': SATELLITE_INFO,
                 'output_path': OUTPUT['output_path']}
    image_prefixes = []
    items_list = []
    for result in results:
        image_prefixes += [result[0]]
        items_list += [result[1]]
    kwargs['image_prefixes'] = image_prefixes
    kwargs['items'] = items_list
    kwargs.update(this_args)
    return kwargs

def reproject_assets(**kwargs):

    from landslide_pipeline.pipeline import OUTPUT
    # Save items (if not done so already, making sure they are stored in OUTPUT['output_path']):
    output_projection = OUTPUT['output_projection']
    for item in kwargs['items']:
        if item['properties']['epsg_code'] == output_projection:
            print("True")
        else:
            print("False")

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
'''
