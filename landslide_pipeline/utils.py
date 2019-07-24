def GetExtent(gt,cols,rows):
    ''' Return list of corner coordinates from a geotransform

        @type gt:   C{tuple/list}
        @param gt: geotransform
        @type cols:   C{int}
        @param cols: number of columns in the dataset
        @type rows:   C{int}
        @param rows: number of rows in the dataset
        @rtype:    C{[float,...,float]}
        @return:   coordinates of each corner
    '''
    ext=[]
    xarr=[0,cols]
    yarr=[0,rows]

    for px in xarr:
        for py in yarr:
            x=gt[0]+(px*gt[1])+(py*gt[2])
            y=gt[3]+(px*gt[4])+(py*gt[5])
            ext.append([x,y])
        yarr.reverse()
    return ext

def get_extent_for_file(filename):
    from osgeo import gdal
    raster = gdal.Open(filename)
    gt = raster.GetGeoTransform()
    cols = raster.RasterXSize
    rows = raster.RasterYSize
    return GetExtent(gt, cols, rows)
    

def extent_union_of_files(files):
    union = {'xmin': None,
             'ymin': None,
             'xmax': None,
             'ymax': None}
    
    for filename in files:
        extent = get_extent_for_file(filename)
        for [x,y] in extent:
            if union['xmin'] is None:
                union['xmin'] = x
                union['xmax'] = x
                union['ymin'] = y
                union['ymax'] = y
            if x < union['xmin']:
                union['xmin'] = x
            if x > union['xmax']:
                union['xmax'] = x
            if y < union['ymin']:
                union['ymin'] = y
            if y > union['ymax']:
                union['ymax'] = y
                
    return union

def get_statistics_for_file(filename):
    from osgeo import gdal
    raster = gdal.Open(filename)
    return_dict = {}
    for i in range(1, 4):
        (r_min, r_max, r_mean, r_std) = raster.GetRasterBand(i).GetStatistics(True, True)
        data_type = gdal.GetDataTypeName(raster.GetRasterBand(i).DataType)
        range_min = 0.0
        range_max = 255.0
        if data_type == 'byte':
            range_min = 0.0
            range_max = 255.0
        return_dict[str(i)] = {'min': r_min,
                               'max': r_max,
                               'mean': r_mean,
                               'std': r_std,
                               'range_min': range_min,
                               'range_max': range_max} 
    return return_dict
 
 
import cv2
import math
import numpy as np

def apply_mask(matrix, mask, fill_value):
    masked = np.ma.array(matrix, mask=mask, fill_value=fill_value)
    return masked.filled()

def apply_threshold(matrix, low_value, high_value):
    low_mask = matrix < low_value
    matrix = apply_mask(matrix, low_mask, low_value)

    high_mask = matrix > high_value
    matrix = apply_mask(matrix, high_mask, high_value)

    return matrix

def simplest_cb(img, percent):
    assert img.shape[2] == 3
    assert percent > 0 and percent < 100

    half_percent = percent / 200.0

    channels = cv2.split(img)

    out_channels = []
    for channel in channels:
        assert len(channel.shape) == 2
        # find the low and high precentile values (based on the input percentile)
        height, width = channel.shape
        vec_size = width * height
        flat = channel.reshape(vec_size)

        assert len(flat.shape) == 1

        flat = np.sort(flat)

        n_cols = flat.shape[0]

        low_val  = flat[int(math.floor(n_cols * half_percent))]
        high_val = flat[int(math.ceil( n_cols * (1.0 - half_percent)))]

        # saturate below the low percentile and above the high percentile
        thresholded = apply_threshold(channel, low_val, high_val)
        # scale the channel
        normalized = cv2.normalize(thresholded, thresholded.copy(), 0, 255, cv2.NORM_MINMAX)
        out_channels.append(normalized)

    return cv2.merge(out_channels)

def get_path_row(lat, lon):
    """
    :param lat: Latitude float
    :param lon: Longitude float
        'convert_pr_to_ll' [path, row to coordinates]
    :return: lat, lon tuple or path, row tuple
    """
    from requests import get
    from lxml import html
    import re
    
    conversion_type = 'convert_ll_to_pr'
    base = 'https://landsat.usgs.gov/landsat/lat_long_converter/tools_latlong.php'
    unk_number = 1508518830987

    full_url = '{}?rs={}&rsargs[]={}&rsargs[]={}&rsargs[]=1&rsrnd={}'.format(base, conversion_type,
                                                                                 lat, lon,
                                                                                 unk_number)
    r = get(full_url)
    tree = html.fromstring(r.text)

    # remember to view source html to build xpath
    # i.e. inspect element > network > find GET with relevant PARAMS
    # > go to GET URL > view source HTML
    p_string = tree.xpath('//table/tr[1]/td[2]/text()')
    p = int(re.search(r'\d+', p_string[0]).group())

    r_string = tree.xpath('//table/tr[1]/td[4]/text()')
    r = int(re.search(r'\d+', r_string[0]).group())
    
    return (p, r)
           
def get_paths_rows(min, max):
    (min_lon, min_lat) = min
    (max_lon, max_lat) = max
    pr = []
    for x in np.arange(min_lon, max_lon, 0.3):
        for y in np.arange(min_lat, max_lat, 0.3):
            pr += [get_path_row(y, x)]
    
    return set(pr)

           
def resample_image(image, max_dim_size = 100):

    aspect_ratio = image.size[1] / image.size[0]
    return image.resize((int(round(float(max_dim_size)/aspect_ratio)),max_dim_size)) if aspect_ratio >= 1 \
        else image.resize((max_dim_size, int(round(float(max_dim_size)*aspect_ratio))))


def get_projected_bounds(upper_left, lower_right, epsg_code_source, epsg_code_target):

    from osgeo import osr

    def reproject_coords(coords,src_srs,tgt_srs):

        trans_coords=[]
        transform = osr.CoordinateTransformation(src_srs, tgt_srs)
        for x,y in coords:
            x,y,z = transform.TransformPoint(x,y)
            trans_coords.append((x,y))
        return tuple(trans_coords)

    src_srs = osr.SpatialReference()
    src_srs.ImportFromEPSG(epsg_code_source)

    tgt_srs = osr.SpatialReference()
    tgt_srs.ImportFromEPSG(epsg_code_target)

    return reproject_coords((upper_left, lower_right), src_srs, tgt_srs)

def get_map_bounds_in_projection(map_name, epsg_code):

    import ogr
    import os
    from osgeo import osr

    def reproject_coords(coords,src_srs,tgt_srs):

        trans_coords=[]
        transform = osr.CoordinateTransformation(src_srs, tgt_srs)
        for x,y in coords:
            x,y,z = transform.TransformPoint(x,y)
            trans_coords.append((x,y))
        return tuple(trans_coords)

    path = os.path.join(map_name,map_name + '.shp')
    ds = ogr.Open(path, 1)
    lyr = ds.GetLayer(0)
    extent = lyr.GetExtent()
    ul_lr = ((extent[0], extent[3]), (extent[1], extent[2]))
    tgt_srs = osr.SpatialReference()
    tgt_srs.ImportFromEPSG(epsg_code)
    ul_lr_reproj = reproject_coords(ul_lr, lyr.GetSpatialRef(), tgt_srs)
    return min(ul_lr_reproj[0][0], ul_lr_reproj[1][0]), max(ul_lr_reproj[0][0], ul_lr_reproj[1][0]), \
           min(ul_lr_reproj[1][1], ul_lr_reproj[0][1]), max(ul_lr_reproj[1][1], ul_lr_reproj[0][1])

def set_extent_from_landslide_map(**kwargs):

    if kwargs.get('LOCATION') is not None:
        return kwargs

    map_name = kwargs['LANDSLIDE_MAP']['name']
    epsg_code = 4326

    (min_y, max_y, min_x, max_x) = get_map_bounds_in_projection(map_name, epsg_code)

    kwargs['LOCATION'] = {'max_longitude': max_x,
                          'min_longitude': min_x,
                          'min_latitude': min_y,
                          'max_latitude': max_y}
    return kwargs