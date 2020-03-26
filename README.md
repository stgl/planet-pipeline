# landslidePipeline

The landslide pipeline contains a group of python Files by George Hilley et. al to download and mosaic Plant Labs Imagery (there is also a pipeline for Landsat Imagery) 

The first thing one must do is to download the dependencies included in the environment. yml file into their base environment 

Next pip install planet to get access to the planet API 

once that is downloaded open a python shell using: python

then type 

   from landslide_pipline import run_pipeline, LS_pipeline
   run_pipeline(LS_pipeline, parameter_file  = 'stanford.json) 
   
   This should start downloading the raw imagery to a folder of your choice (specified in the .json) 
   
   ##Making mosaic