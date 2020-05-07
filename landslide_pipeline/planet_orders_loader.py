def load_data(*args, **kwargs):

    if kwargs.get('item_ids', None) is not None:
        return kwargs

    tile_data = kwargs.get('TILE_DATA', False)

    from .utils import get_bounding_info_from_geojson

    bounding_box, convex_hull = get_bounding_info_from_geojson(kwargs['LOCATION'])
    name = kwargs['NAME']
    times = kwargs['TIMES']
    api_key = kwargs['PL_API_KEY']
    satellite_info = kwargs['SATELLITE_INFO']
    cloud_cover = kwargs.get('CLOUD_COVER', 0.1)
    sun_elevation = kwargs.get('SUN_ELEVATION', 65)
    ground_control = kwargs.get('GROUND_CONTROL', True)
    usable_data = kwargs.get('USABLE_DATA', 0.75)
    view_angle = kwargs.get('VIEW_ANGLE', 4.0)

    import os
    import planet.api as api

    if tile_data:
        bounding_boxes = []
        lat_center = (bounding_box[2] + bounding_box[3])/2.0
        import numpy as np
        d_theta = np.rad2deg(13.322 / (6371 * np.cos(np.deg2rad(lat_center))))
        long = np.arange(bounding_box[0], bounding_box[1], d_theta)
        lat = np.arange(bounding_box[2], bounding_box[3], d_theta)
        long = np.append(long, bounding_box[1]) if long[-1] != bounding_box[1] else long
        lat = np.append(lat, bounding_box[3]) if lat[-1] != bounding_box[3] else lat
        for i in range(len(lat)-2):
            for j in range(len(long)-2):
                bounding_boxes += [{'type': 'Polygon',
                        'coordinates': [
                            [
                                [long[j], lat[i]],
                                [long[j+2], lat[i]],
                                [long[j+2], lat[i+2]],
                                [long[j], lat[i+2]],
                                [long[j], lat[i]]
                            ]
                        ]}]
    else:
        bounding_boxes = [{'type': 'Polygon',
                        'coordinates': [
                            [
                                [bounding_box[0], bounding_box[2]],
                                [bounding_box[1], bounding_box[2]],
                                [bounding_box[1], bounding_box[3]],
                                [bounding_box[0], bounding_box[3]],
                                [bounding_box[0], bounding_box[2]]
                            ]
                        ]}]

    # Set up client:

    os.environ["PL_API_KEY"] = api_key

    client = api.ClientV1()

    # Set up query:

    sat_info = satellite_info

    kwargs['item_ids'] = []
    kwargs['bounding_boxes'] = []

    for bb in bounding_boxes:
        this_usable = usable_data
        num_items = 0

        while num_items == 0:
            query_and_geofilter = {
                "name": name,
                "item_types": sat_info,
                "filter": {
                    "type": "AndFilter",
                    "config":
                        [
                            {
                                "type": "RangeFilter",
                                "field_name": "cloud_cover",
                                "config": {"lte": cloud_cover}
                            },
                            {
                                "type": "RangeFilter",
                                "field_name": "sun_elevation",
                                "config": {"gte": sun_elevation}
                            },
                            {
                                "type": "RangeFilter",
                                "field_name": "usable_data",
                                "config": {"gte": this_usable}
                            },
                            {
                                "type": "RangeFilter",
                                "field_name": "view_angle",
                                "config": {"gte": -view_angle}
                            },
                            {
                                "type": "RangeFilter",
                                "field_name": "view_angle",
                                "config": {"lte": view_angle}
                            },
                            {
                                "type": "StringInFilter",
                                "field_name": "instrument",
                                "config": ["PS2.SD"]
                            },
                            {
                                "type": "GeometryFilter",
                                "field_name": "geometry",
                                "config": bb
                            },
                            {
                                "type": "DateRangeFilter",
                                "field_name": "acquired",
                                "config":
                                    {
                                        "gt": times['start'],
                                        "lte": times['end']
                                    }
                            }
                        ]
                }
            }

            response = client.quick_search(query_and_geofilter)

            ids = []

            num_items = 0
            for page in response.iter():
                for item in page.items_iter(250):
                    if (ground_control and item['properties']['ground_control']) or not ground_control:
                        ids += [item['id']]
                        num_items += 1

            if num_items < 12 and this_usable >= 0:
                this_usable -= 0.05
                num_items = 0
            elif num_items > 20:
                this_usable += 0.05
                num_items = 0

        print('Query returned ' + str(num_items) + ' items.')
        kwargs['item_ids'].append(ids)
        kwargs['bounding_boxes'] += [bb]

    return kwargs

def compositor(*args, **kwargs):
    tools = kwargs.get('tools',[])
    tools.append({'composite':{}})
    kwargs['tools'] = tools
    return kwargs

def clip(*args, **kwargs):
    from .utils import get_bounding_info_from_geojson
    _, convex_hull = get_bounding_info_from_geojson(kwargs['LOCATION'])
    tools = kwargs.get('tools', [])
    tools.append({'clip': {'aoi': convex_hull}})
    kwargs['tools'] = tools
    return kwargs

def reproject(*args, **kwargs):
    epsg = kwargs['OUTPUT']['output_projection']
    tools = kwargs.get('tools',[])
    tools.append({'reproject':{'projection':'EPSG:'+str(epsg),
                               'kernel': kwargs.get('OUTPUT',{}).get('KERNEL','NEAR')}})
    kwargs['tools'] = tools
    return kwargs

def toar(*args, **kwargs):
    scale = kwargs.get('TOAR_SCALE',10000)
    tools = kwargs.get('tools',[])
    tools.append({'toar': {'scale_factor': scale}})
    kwargs['tools'] = tools
    return kwargs

def harmonize(*args, **kwargs):
    target_sensor = kwargs.get('TARGET_SENSOR', 'PS2.SD')
    tools = kwargs.get('tools', [])
    tools.append({'harmonize': {'target_sensor': target_sensor}})
    kwargs['tools'] = tools
    return kwargs

def place_order(*args, **kwargs):
    name = kwargs['NAME']
    satellite_info = kwargs['SATELLITE_INFO']
    if len(satellite_info) > 1:
        raise Exception('Cannot place order with more than one asset type.')
    import json

    api_key = kwargs['PL_API_KEY']
    import os

    os.environ["PL_API_KEY"] = api_key
    import requests
    from requests.auth import HTTPBasicAuth
    orders_url = 'https://api.planet.com/compute/ops/orders/v2'
    auth = HTTPBasicAuth(api_key, '')
    headers = {'content-type': 'application/json'}

    bundle = kwargs['BUNDLE']

    kwargs['order_responses'] = []
    for [item_id_set, bb] in zip(kwargs['item_ids'],kwargs['bounding_boxes']):
        if len(item_id_set) > 0:
            tools = kwargs['tools']
            tools.append({'clip': {'aoi': bb}})
            request = {'name': name,
                       'products': [
                           {
                               "item_ids": item_id_set,
                               "item_type": satellite_info[0],
                               "product_bundle": bundle
                           }
                       ],
                       'tools': kwargs['tools'],
                       'notifications': {'email': kwargs.get('NOTIFICATION', False)}}

            kwargs['order_responses'] += [requests.post(orders_url, data=json.dumps(request), auth=auth, headers=headers)]

    return kwargs

def get_order(*args, **kwargs):

    import requests, os, time
    recheck_interval = kwargs.get('RECHECK_INTERVAL', 15.0)
    api_key = kwargs['PL_API_KEY']
    out = kwargs['OUTPUT']
    session = requests.Session()
    session.auth = (api_key, '')

    orders = kwargs['order_responses']
    order_complete = [False for o in orders]

    while not all(order_complete):
        for (order, counter) in zip(orders,range(len(orders))):
            if not order_complete[counter]:
                check_link = order.json()['_links']['_self']
                try:
                    poll = session.get(check_link).json()
                    if poll['state'] == 'failed':
                        order_complete[counter] = True
                    elif poll['state'] == 'running' and len(poll['_links'].get('results', [])) > 0:
                        order_complete[counter] = True
                        for result in poll['_links']['results']:
                            if 'composite.tif' in result['name']:
                                r = requests.get(result['location'], allow_redirects=True)
                                open(os.path.join(out['output_path'], out['output_path']+'_'+str(counter)+'.tif'), 'wb').write(r.content)
                    print('Checked order ' + str(counter))
                except:
                    print('Skipped order ' + str(counter))
                    time.sleep(1.0)
                time.sleep(0.25)
        time.sleep(recheck_interval)

def cycle_orders(*args, **kwargs):

    import os
    all_files_loaded = True
    for counter in range(len(kwargs['item_ids'])):
        if len(kwargs['item_ids'][counter]) > 0 and not os.path.exists(os.path.join(kwargs['OUTPUT']['output_path'], kwargs['OUTPUT']['output_path'] + '_' + str(counter) + '.tif')):
            all_files_loaded = False

    if all_files_loaded:
        return kwargs

    import requests, time, json, datetime
    from requests.auth import HTTPBasicAuth

    api_key = kwargs['PL_API_KEY']
    os.environ["PL_API_KEY"] = api_key
    session = requests.Session()
    session.auth = (api_key, '')
    headers = {'content-type': 'application/json'}
    auth = HTTPBasicAuth(api_key, '')

    def place_order(counter, order_list):
        name = kwargs['NAME']
        satellite_info = kwargs['SATELLITE_INFO']
        if len(satellite_info) > 1:
            raise Exception('Cannot place order with more than one asset type.')
        orders_url = 'https://api.planet.com/compute/ops/orders/v2'
        bundle = kwargs['BUNDLE']

        (item_id_set, bb) = (kwargs['item_ids'][counter], kwargs['bounding_boxes'][counter])
        if len(item_id_set) > 0:
            tools = kwargs['tools'].copy()
            for tool in tools:
                if tool.get('clip') is not None:
                    tool['clip']['aoi'] = bb
            request = {'name': name,
                       'products': [
                           {
                               "item_ids": item_id_set,
                               "item_type": satellite_info[0],
                               "product_bundle": bundle
                           }
                       ],
                       'tools': tools,
                       'notifications': {'email': kwargs.get('NOTIFICATION', False)}}
            response_completed = False
            while not response_completed:
                response = requests.post(orders_url, data=json.dumps(request), auth=auth, headers=headers)
                if response.status_code == 202:
                    order_list += [(response, counter, datetime.datetime.now())]
                    response_completed = True
                    print('Launched order', counter)
                elif response.status_code == 400 or response.status_code == 401:
                    print('Request was invalid.  Not trying again.', counter)
                    response_completed = True
                else:
                    print('There was a problem with the request.  Trying again in 10 seconds (response follows) ', counter, response.json())
                    time.sleep(10.0)

        return order_list

    def check_orders(order_list):
        these_orders = []
        for (order, counter, launch_time) in order_list:
            check_link = order.json()['_links']['_self']
            try:
                poll = session.get(check_link).json()
                if (poll['state'] == 'running' or poll['state'] == 'success') and len(poll['_links'].get('results', [])) > 0:
                    for result in poll['_links']['results']:
                        if 'composite.tif' in result['name']:
                            r = requests.get(result['location'], allow_redirects=True)
                            open(os.path.join(out['output_path'], out['output_path']+'_'+str(counter)+'.tif'), 'wb').write(r.content)
                            print('Completed order: ', counter)
                elif poll['state'] != 'failed' and ((datetime.datetime.now() - launch_time).seconds) / 60 < 30:
                    these_orders += [(order, counter, launch_time)]
                elif poll['state'] != 'failed':
                    print('Timeout, relaunching', counter, poll)
                    these_orders = place_order(counter, these_orders)
                else:
                    print('Order failed', counter, poll)
            except:
                these_orders += [(order, counter, launch_time)]
                time.sleep(1.0)
            time.sleep(0.25)
        return these_orders

    recheck_interval = kwargs.get('RECHECK_INTERVAL', 15.0)
    out = kwargs['OUTPUT']
    max_number_of_orders = kwargs.get('MAX_NUMBER_OF_ORDERS', 2)
    current_counter = 0
    current_orders = None

    total_number_of_orders = len(kwargs['item_ids'])

    while current_orders is None or len(current_orders) > 0:
        current_orders = current_orders if current_orders is not None else []
        while len(current_orders) < max_number_of_orders and current_counter < total_number_of_orders:
            if not os.path.exists(os.path.join(kwargs['OUTPUT']['output_path'], kwargs['OUTPUT']['output_path'] + '_' + str(current_counter) + '.tif')):
                print('Placing order: ' + str(current_counter))
                current_orders = place_order(current_counter, current_orders)
            current_counter += 1
        time.sleep(recheck_interval)
        current_orders = check_orders(current_orders)

def clean_up_orders(**kwargs):

    if kwargs.get('item_ids') is not None:
        import os
        for i in range(len(kwargs['item_ids'])):
            filename = os.path.join(kwargs['OUTPUT']['output_path'], kwargs['OUTPUT']['output_path'] + '_' + str(i) + '.tif')
            if os.path.exists(filename):
                os.remove(filename)
    return kwargs