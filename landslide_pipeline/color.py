def correct(*args, **kwargs):
    
    import cv2, gdal
    from landslide_pipeline.pipeline import OUTPUT
    
    cloudless_scene = OUTPUT['output_path'] + "/" + OUTPUT['output_path'] + '.TIF'
    colorbalanced_scene = OUTPUT['output_path'] + "/" + OUTPUT['output_path'] + '_cb.TIF'
    
    img = cv2.imread(cloudless_scene,1)
    
    from landslide_pipeline.utils import simplest_cb
    from landslide_pipeline.pipeline import CB_PERCENT
    
    img = simplest_cb(img, CB_PERCENT)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lab_planes = cv2.split(lab)
    lab_planes[0] = clahe.apply(lab_planes[0])
    lab = cv2.merge(lab_planes)
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    ds = gdal.Open(cloudless_scene)
    drvr = ds.GetDriver()
    gdal_type = gdal.GDT_Byte
    #if img.dtype == np.uint16:
        #gdal_type = gdal.GDT_UInt16
    outraster = drvr.Create(colorbalanced_scene, ds.RasterXSize, ds.RasterYSize, 3, gdal_type, ['COMPRESS=LZW'])
    outraster.SetGeoTransform(ds.GetGeoTransform())
    outraster.SetProjection(ds.GetProjection())
    outraster.GetRasterBand(1).WriteArray(img[:,:,2])
    outraster.GetRasterBand(2).WriteArray(img[:,:,1])
    outraster.GetRasterBand(3).WriteArray(img[:,:,0])
    
    kwargs['colorbalanced_scene'] = colorbalanced_scene
                
    return kwargs