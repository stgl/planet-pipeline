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
        