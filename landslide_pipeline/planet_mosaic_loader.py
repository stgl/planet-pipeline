import os
from shapely.geometry import shape, Polygon, box
from shapely.ops import transform
import pyproj
import requests
from datetimerange import DateTimeRange
from functools import partial

PL_API_KEY = "58613e03d31d4476ae132fbe8bd0afca"
os.environ["PL_API_KEY"] = PL_API_KEY


def query_planet_mosaic():

    def handle_page(response, ul, lr, start, end):
        return_items = []
        for items in response['mosaics']:
            bd = items['bbox']
            mosgeom = shape(Polygon(box(bd[0], bd[1], bd[2], bd[3]).exterior.coords))
            boundgeom = shape(Polygon(box(ul[0], lr[1], lr[0], ul[1])))
            proj = partial(pyproj.transform, pyproj.Proj(init='epsg:4326'), pyproj.Proj(init='epsg:3857'))
            boundgeom = transform(proj, boundgeom)
            mosgeom = transform(proj, mosgeom)
            if boundgeom.intersection(mosgeom).is_empty:
                pass
            else:
                id = items['id']
                r = requests.get('https://api.planet.com/mosaic/experimental/mosaics/' + str(id) + '/quads?bbox=' + str(ul[0])+'%2C'+str(lr[1])+'%2C'+str(lr[0])+'%2C'+str(ul[1]),auth=(PL_API_KEY,''))
                resp = r.json()
                if len(resp['items']) > 0:
                    time_range = DateTimeRange(items['first_acquired'].split('T')[0], items['last_acquired'].split('T')[0])
                    x = DateTimeRange(start, end)
                    if time_range.is_intersection(x) is True:
                        return_items += [{"name": str(items['name']),
                                          "mosaic_id": str(items['id']),
                                          "quad_ids": tuple(set([it['id'] for it in resp['items']])),
                                          "first_acquired": str(items['first_acquired']).split('T')[0],
                                          "last_acquired": str(items['last_acquired']).split('T')[0],
                                          "coordinate_system": int(items['coordinate_system'].split(':')[1]),
                                          "resolution": format(float(str(items['grid']['resolution'])),'.3f')}]
        return return_items

    def metadata(ul, lr, start, end):

        r = requests.get('https://api.planet.com/basemaps/v1/mosaics', auth=(PL_API_KEY, ''))
        response = r.json()
        final_list = []
        try:
            if response['mosaics'][0]['quad_download'] ==True:
                final_list += handle_page(response, ul, lr, start, end)
        except KeyError:
            print('No Download permission for: '+str(response['mosaics'][0]['name']))
        try:
            while response['_links'].get('_next') is not None:
                page_url = response['_links'].get('_next')
                r = requests.get(page_url)
                response = r.json()
                try:
                    if response['mosaics'][0]['quad_download'] ==True:
                        final_list += handle_page(response, ul, lr, start, end)
                except KeyError:
                    print('No Download permission for: '+str(response['mosaics'][0]['name']))
        except Exception as e:
            print(e)

        return final_list

    from landslide_pipeline.pipeline import LOCATION, TIMES
    ul = (LOCATION['min_longitude'], LOCATION['max_latitude'])
    lr = (LOCATION['max_longitude'], LOCATION['min_latitude'])
    start = TIMES['start']
    end = TIMES['end']

    return metadata(ul, lr, start, end)

def load_data(**kwargs):

    from landslide_pipeline.pipeline import LOCATION, OUTPUT
    import os

    cloudless_scenes = []

    output_directory = os.path.join(os.getcwd(), OUTPUT['output_path'])
    try:
        os.mkdir(output_directory)
    except:
        pass


    metadata = query_planet_mosaic()

    for mosaic in metadata:
        tilenames = []
        counter = 0
        for tile in mosaic['quad_ids']:
            url = "https://api.planet.com/basemaps/v1/mosaics/" + mosaic['mosaic_id'] + '/quads/' + tile \
                + '/full?api_key=' + PL_API_KEY
            r = requests.get(url)

            tilename = '/tmp/' + str(counter)
            counter += 1
            tilenames += [tilename]
            with open(tilename, 'wb') as f:
                f.write(r.content)

        ul = (LOCATION['max_latitude'], LOCATION['min_longitude'])
        lr = (LOCATION['min_latitude'], LOCATION['max_longitude'])

        from landslide_pipeline.utils import get_projected_bounds

        (ulp, lrp) = get_projected_bounds(ul, lr, 4326, mosaic['coordinate_system'])
        output_name = os.path.join(OUTPUT['output_path'], mosaic['name'] + '.tif')
        cloudless_scenes += [{"filename": output_name,
                              "coordinate_system": mosaic['coordinate_system']}]

        arg = ['gdal_merge.py', '-o', output_name, '-of', 'GTiff', '-co',
               'COMPRESS=LZW', '-co', 'BIGTIFF=IF_SAFER', '-ul_lr', str(ulp[0]), str(ulp[1]), str(lrp[0]),
               str(lrp[1])] + tilenames

        import subprocess
        subprocess.call(arg)
        for tilename in tilenames:
            os.remove(tilename)

    kwargs['cloudless_scenes'] = cloudless_scenes
    return kwargs


def reproject_assets(**kwargs):

    from landslide_pipeline.pipeline import OUTPUT
    cloudless_scenes = kwargs['cloudless_scenes']
    output_projection = OUTPUT['output_projection']
    for cloudless_scene in cloudless_scenes:
        if cloudless_scene['coordinate_system'] != output_projection:
            import subprocess as sp
            arg = ['gdalwarp', '-s_srs', 'EPSG:' + str(cloudless_scene['coordinate_system']), \
                   '-t_srs', 'EPSG:' + str(OUTPUT['output_projection']), cloudless_scene['filename'], \
                   '/tmp/tmpreproj.tif']
            sp.call(arg)
            arg = ['rm', '-f', cloudless_scene['filename']]
            sp.call(arg)
            arg = ['mv', '/tmp/tmpreproj.tif', cloudless_scene['filename']]
            sp.call(arg)
            print('Reprojected: ', cloudless_scene['filename'])
        else:
            print('Did not reproject: ', cloudless_scene['filename'])

    return kwargs
