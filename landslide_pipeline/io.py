def save_pipeline(*args, **kwargs):
    from landslide_pipeline.pipeline import OUTPUT
    import pickle as p
    import os
    filename = os.path.join(OUTPUT['output_path'], OUTPUT['output_path'] + '.p') 
    p.dump(kwargs, open(filename, 'wb'))
    return kwargs

def load_pipeline(*args, **kwargs):
    try:
        from landslide_pipeline.pipeline import OUTPUT
        import os
        filename = os.path.join(OUTPUT['output_path'], OUTPUT['output_path'] + '.p')
        import pickle as p
        kwargs = p.load(open(filename, 'rb'))
    except:
        kwargs = kwargs
    return kwargs

