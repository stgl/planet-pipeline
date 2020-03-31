def load_data(*args, **kwargs):

    if kwargs.get('item_ids', None) is not None and kwargs.get('items', None) is not None:
        return kwargs

    from .utils import get_bounding_info_from_geojson

    bounding_box, convex_hull = get_bounding_info_from_geojson(kwargs['LOCATION'])
    name = kwargs['NAME']
    times = kwargs['TIMES']
    api_key = kwargs['PL_API_KEY']
    satellite_info = kwargs['SATELLITE_INFO']

    import os
    import planet.api as api

    # Set up client:

    os.environ["PL_API_KEY"] = api_key

    client = api.ClientV1()

    # Set up query:

    sat_info = satellite_info

    coordinates = [
         [
            [
                bounding_box[0],
                bounding_box[2]
            ],
            [
                bounding_box[1],
                bounding_box[2]
            ],
            [
                bounding_box[1],
                bounding_box[3]
            ],
            [
                bounding_box[0],
                bounding_box[3]
            ],
            [
                bounding_box[0],
                bounding_box[2]
            ]
         ]
      ]
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
                        "config": {"lte": 0.5}
                    },
                    {
                        "type": "GeometryFilter",
                        "field_name": "geometry",
                        "config":convex_hull
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
            ids += [item['id']]
            num_items += 1
    print('Query returned ' + str(num_items) + ' items.')
    kwargs['item_ids'] = ids

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

def place_order(*args, **kwargs):
    name = kwargs['NAME']
    satellite_info = kwargs['SATELLITE_INFO']
    if len(satellite_info) > 1:
        raise Exception('Cannot place order with more than one asset type.')
    bundle = kwargs['BUNDLE']
    request = {'name': name,
               'products': [
                   {
                       "item_ids": kwargs['item_ids'],
                       "item_type": satellite_info[0],
                       "product_bundle": bundle
                   }
               ],
               'tools': kwargs['tools'],
               'notifications': {'email': kwargs.get('NOTIFICATION', False)}}
    import json

    api_key = kwargs['PL_API_KEY']
    import os

    os.environ["PL_API_KEY"] = api_key
    import requests
    from requests.auth import HTTPBasicAuth
    orders_url = 'https://api.planet.com/compute/ops/orders/v2'
    auth = HTTPBasicAuth(api_key, '')
    headers = {'content-type': 'application/json'}
    kwargs['order_response'] = requests.post(orders_url, data=json.dumps(request), auth=auth, headers=headers)
    return kwargs