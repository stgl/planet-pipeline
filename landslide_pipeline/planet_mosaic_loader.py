import os
from shapely.geometry import shape, Polygon, box
from shapely.ops import transform
import pyproj
import requests
from datetimerange import DateTimeRange
from functools import partial


def query_planet_mosaic(location, times, api_key):

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
                quad_ids = []
                r = requests.get('https://api.planet.com/basemaps/v1/mosaics/' + str(id) + '/quads?bbox=' +
                                 str(ul[0])+'%2C'+str(lr[1])+'%2C'+str(lr[0])+'%2C'+str(ul[1]) +
                                 '&api_key=' + api_key)
                resp = r.json()
                if len(resp['items']) > 0:
                    time_range = DateTimeRange(items['first_acquired'].split('T')[0],
                                               items['last_acquired'].split('T')[0])
                    x = DateTimeRange(start, end)
                    if time_range.is_intersection(x) is True:
                        quad_ids += [it['id'] for it in resp['items']]
                        while resp['_links'].get('_next') is not None:
                            r = requests.get(resp['_links'].get('_next'))
                            resp = r.json()
                            time_range = DateTimeRange(items['first_acquired'].split('T')[0],
                                                       items['last_acquired'].split('T')[0])
                            x = DateTimeRange(start, end)
                            if time_range.is_intersection(x) is True:
                                quad_ids += [it['id'] for it in resp['items']]
                    if len(quad_ids) > 0:
                        return_items += [{"name": str(items['name']),
                                          "mosaic_id": str(items['id']),
                                          "quad_ids": tuple(set(quad_ids)),
                                          "first_acquired": str(items['first_acquired']).split('T')[0],
                                          "last_acquired": str(items['last_acquired']).split('T')[0],
                                          "coordinate_system": int(items['coordinate_system'].split(':')[1]),
                                          "resolution": format(float(str(items['grid']['resolution'])),'.3f')}]
        return return_items

    def metadata(ul, lr, start, end):

        r = requests.get('https://api.planet.com/basemaps/v1/mosaics?api_key=' + api_key)
        response = r.json()
        final_list = []
        try:
            if response['mosaics'][0]['quad_download']:
                final_list += handle_page(response, ul, lr, start, end)
        except KeyError:
            print('No Download permission for: '+str(response['mosaics'][0]['name']))
        try:
            while response['_links'].get('_next') is not None:
                page_url = response['_links'].get('_next')
                r = requests.get(page_url)
                response = r.json()
                try:
                    if response['mosaics'][0]['quad_download']:
                        final_list += handle_page(response, ul, lr, start, end)
                except KeyError:
                    print('No Download permission for: '+str(response['mosaics'][0]['name']))
        except Exception as e:
            print(e)

        return final_list

    ul = (location['min_longitude'], location['max_latitude'])
    lr = (location['max_longitude'], location['min_latitude'])
    start = times['start']
    end = times['end']

    if start[-1] == 'Z':
        start = start[0:-1]
    if end[-1] == 'Z':
        end = end[0:-1]

    return metadata(ul, lr, start, end)


def load_data(**kwargs):

    if kwargs.get('cloudless_scenes') is not None:
        return kwargs

    location = kwargs['LOCATION']
    times = kwargs['TIMES']
    output = kwargs['OUTPUT']
    api_key = kwargs['PL_API_KEY']

    import os

    cloudless_scenes = []

    output_directory = os.path.join(os.getcwd(), output['output_path'])
    try:
        os.mkdir(output_directory)
    except:
        pass

    try:
        os.mkdir('.tmp')
    except:
        pass

    metadata = query_planet_mosaic(location, times, api_key)
    kwargs['query_metadata'] = metadata

    for mosaic in metadata:
        tilenames = []
        counter = 0
        for tile in mosaic['quad_ids']:
            url = "https://api.planet.com/basemaps/v1/mosaics/" + mosaic['mosaic_id'] + '/quads/' + tile \
                + '/full?api_key=' + api_key
            r = requests.get(url)

            tilename = os.path.join('.tmp', str(counter))
            counter += 1
            tilenames += [tilename]
            with open(tilename, 'wb') as f:
                f.write(r.content)

        ul = (location['max_latitude'], location['min_longitude'])
        lr = (location['min_latitude'], location['max_longitude'])

        from landslide_pipeline.utils import get_projected_bounds

        (ulp, lrp) = get_projected_bounds(ul, lr, 4326, mosaic['coordinate_system'])
        output_name = os.path.join(output['output_path'], mosaic['name'] + '.tif')
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

    if kwargs.get('reprojected') is not None:
        return kwargs
    import os
    output = kwargs['OUTPUT']
    cloudless_scenes = kwargs['cloudless_scenes']
    output_projection = output['output_projection']
    for cloudless_scene in cloudless_scenes:
        if cloudless_scene['coordinate_system'] != output_projection:
            import subprocess as sp
            arg = ['gdalwarp', '-s_srs', 'EPSG:' + str(cloudless_scene['coordinate_system']),
                   '-t_srs', 'EPSG:' + str(output['output_projection']), '-of', 'GTiff', '-co', 'COMPRESS=LZW',
                   '-co', 'BIGTIFF=IF_SAFER', cloudless_scene['filename'], os.path.join('.tmp','tmpreproj.tif')]
            sp.call(arg)
            arg = ['rm', '-f', cloudless_scene['filename']]
            sp.call(arg)
            arg = ['mv', os.path.join('.tmp','tmpreproj.tif'), cloudless_scene['filename']]
            sp.call(arg)
            print('Reprojected: ', cloudless_scene['filename'])
        else:
            print('Did not reproject: ', cloudless_scene['filename'])

    kwargs['reprojected'] = True

    return kwargs
