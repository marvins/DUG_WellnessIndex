#!/usr/bin/env python3

import argparse, configparser, glob, logging, os, re, sys

import rasterio

from pylandtemp import ndvi, emissivity, split_window

#  DUG API
sys.path.insert(0,'.')
import dug_api.coordinate as crd
from dug_api import Database, imagery
from dug_api.CollectID import CollectID, FileType
from dug_api.config import Configuration

def parse_command_line():

    parser = argparse.ArgumentParser(description='Create NDVI image.')

    parser.add_argument( '-v',
                         dest='verbose',
                         default=False,
                         action='store_true',
                         required=False,
                         help='Use verbose logging.' )
    
    parser.add_argument( '--cid',
                         dest = 'cid_path',
                         required=True,
                         help = 'Location of Collection ID.' )
    
    parser.add_argument( '-c',
                         dest='config_path',
                         required = True,
                         help = 'Config path' )
    
    parser.add_argument( '-o',
                         dest='overwrite',
                         default=False,
                         action='store_true',
                         required = False,
                         help = 'Flag if we wish to overwrite image.' )

    return parser.parse_args()

lst_str_lut = { 'jiminez-munoz': 'jiminez',
                'sobrino-1993':  'sobrino',
                'kerr':          'kerr',
                'mc-clain':      'mcclain',
                'price':         'price' }

def create_land_surface_temp_image( band04,
                                    band05,
                                    band10,
                                    band11,
                                    band_meta,
                                    lst_method,
                                    em_method,
                                    epsg,
                                    logger,
                                    output_dir,
                                    overwrite ):

    #  Get a string for writing the LST method to pathnames
    tag = lst_str_lut[lst_method]

    #  Skip if we don't need to process the imagery
    key_c = f'lst_{tag}_{em_method}_epsg_{epsg}_c'
    key_f = f'lst_{tag}_{em_method}_epsg_{epsg}_f'
    bands = { 'lst_c': { 'key': key_c,
                         'default': f'lst_{tag}_{em_method}_c.epsg_{epsg}.tif' },
              'lst_f': { 'key': key_f,
                         'default': f'lst_{tag}_{em_method}_f.epsg_{epsg}.tif' } }
    
    outpath_c = f'{output_dir}/{bands["lst_c"]["default"]}'
    outpath_f = f'{output_dir}/{bands["lst_f"]["default"]}'

    if overwrite == False and os.path.exists( outpath_c ) and os.path.exists( outpath_f ):
        logger.info( f'Destination images already exist.' )
        return

    #  Read images
    band04_image = band04.read(1).astype('f4')
    band05_image = band05.read(1).astype('f4')
    band10_image = band10.read(1).astype('f4')
    band11_image = band11.read(1).astype('f4')

    #  Run the split window algorithm
    img_c = split_window( band10_image,
                          band11_image,
                          band04_image,
                          band05_image,
                          lst_method = lst_method,
                          emissivity_method = em_method,
                          unit = 'kelvin' ) - 273.15

    #  Get the baseline projection data to copy
    kwargs = band_meta
    
    # Write the celcius image
    kwargs.update({ 'dtype': img_c.dtype })

    logger.debug( f'Building LST image for Celcius. Path: {outpath_c}' )
    if overwrite or os.path.exists( outpath_c ) == False:
        img_c_band = rasterio.open( outpath_c, 'w', **kwargs)
        img_c_band.write( img_c, 1 )
        img_c_band.close()

    #  Convert image to fahrenheit
    img_f = img_c * 9.0/5.0 + 32

    # Write the celcius image
    outpath_f = f'{output_dir}/{bands["lst_f"]["default"]}'
    logger.debug( f'Building LST image for Fahrenheit. Path: {outpath_f}' )
    kwargs.update({ 'dtype': img_f.dtype })
    if overwrite or os.path.exists( outpath_f ) == False:
        img_f_band = rasterio.open( outpath_f, 'w', **kwargs)
        img_f_band.write( img_f, 1 )
        img_f_band.close()

def main():

    cmd_options = parse_command_line()

    #  Configure Logging
    if cmd_options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger('LandSurfaceTemp')
    logging.getLogger('rasterio').setLevel(logging.INFO)

    #  Load the configuration file
    config = Configuration( cmd_options.config_path )

    #  Get some baseline parameters
    cid      = os.path.basename( cmd_options.cid_path )
    epsg     = config.get_output_epsg()

    # Load the collection config, if it doesnt already exist
    cid_config_path = os.path.join( cmd_options.cid_path, 'config.cfg' )

    cid_config = configparser.ConfigParser()
    if os.path.exists( cid_config_path ) == False:
        logger.error( f'CID has no configuration file. Creating one at {cid_config_path}' )
        assert(False)
    
    logger.info( f'Loading CID Config: {cid_config_path}' )
    cid_config.read( cid_config_path )

    #  Create the required keys
    band_info = { 'band04': { 'key': f'b4_path_epsg_{epsg}'  },
                  'band05': { 'key': f'b5_path_epsg_{epsg}' },
                  'band10': { 'key': f'b10_path_epsg_{epsg}' },
                  'band11': { 'key': f'b11_path_epsg_{epsg}' } }

    # Make sure we have enough bands
    for id in band_info:
        assert( cid_config.has_option( 'general',band_info[id]['key'] ) )
        assert( os.path.exists( cid_config['general'][band_info[id]['key']] ) )

        band_info[id]['path']  = cid_config['general'][band_info[id]['key']]
        
        #  Load requisite bands
        logger.debug( f'Loading Key: {id}, Image: {os.path.basename(band_info[id]["path"])}' )
        band_info[id]['handle'] = rasterio.open( band_info[id]['path'] )
        band_info[id]['image']  = band_info[id]['handle'].read(1).astype('f4')


    em_mode_list = [ 'avdan', 'xiaolei' ]
    lt_mode_list = [ 'jiminez-munoz', 'sobrino-1993' ]
    band_meta = band_info['band04']['handle'].meta.copy()
    output_dir = os.path.dirname( band_info['band04']['path'])
    for em_mode in em_mode_list:

        for lt_mode in lt_mode_list:
            
            create_land_surface_temp_image( band_info['band04']['handle'],
                                            band_info['band05']['handle'],
                                            band_info['band10']['handle'],
                                            band_info['band11']['handle'],
                                            band_meta,
                                            lt_mode,
                                            em_mode,
                                            epsg,
                                            logger,
                                            output_dir,
                                            cmd_options.overwrite )

    
if __name__ == '__main__':
    main()