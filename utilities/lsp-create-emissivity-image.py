#!/usr/bin/env python3

import argparse, configparser, glob, logging, os, re, sys

import rasterio

from pylandtemp import ndvi, emissivity

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

def main():

    cmd_options = parse_command_line()

    #  Configure Logging
    if cmd_options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger('Emissivity')
    logging.getLogger('rasterio').setLevel(logging.INFO)

    #  Load the configuration file
    config = Configuration( cmd_options.config_path )

    #  Get some baseline parameters
    cid      = os.path.basename( cmd_options.cid_path )
    epsg     = config.get_output_epsg()
    bbox_utm = config.get_region()
    dest_gsd = config.get_output_gsd()

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
                  'ndvi':   { 'key': f'ndvi_path_epsg_{epsg}' } }

    # Make sure we have enough bands
    for id in band_info:
        if cid_config.has_option('general',band_info[id]['key']):
            band_info[id]['path']  = cid_config['general'][band_info[id]['key']]
            band_info[id]['valid'] = True
        else:
            band_info[id]['valid'] = True
            

    assert( band_info['band04']['valid'] )
    assert( band_info['ndvi']['valid'] )

    assert( os.path.exists( band_info['band04']['path'] ) )
    assert( os.path.exists( band_info['ndvi']['path'] ) )

    #  Load requisite bands
    for id in band_info:
        if band_info[id]['valid']:
            logger.debug( f'Loading Key: {id}, Image: {os.path.basename(band_info[id]["path"])}' )
            band_info[id]['handle'] = rasterio.open( band_info[id]['path'] )
            band_info[id]['image']  = band_info[id]['handle'].read(1).astype('f4')

    
    #  Create Mask Image
    #mask = (band04_image == 0)

    mode_list = [ 'avdan',
                  'xiaolei',
                  'gopinadh' ]
    for mode in mode_list:

        code = mode[0:3]

        em_img_10, em_img_11 = emissivity( landsat_band_4 = band_info['band04']['image'],
                                           ndvi_image     = band_info['ndvi']['image'],
                                           emissivity_method = mode )

        # Create Destination Band Metadata
        kwargs = band_info['band04']['handle'].meta.copy()
        kwargs.update({
            'crs':       band_info['band04']['handle'].crs,
            'transform': band_info['band04']['handle'].transform,
            'width':     band_info['band04']['handle'].width,
            'height':    band_info['band04']['handle'].height,
        })

        #  Write EM band10 image to Disk
        kwargs.update( { 'dtype': rasterio.float32 } )
        
        out_path = os.path.join( os.path.dirname( band_info['band04']['path'] ),
                                 f'emissivity_{code}10.epsg_{epsg}.tif' )
        
        logger.debug( f'Writing Emissivity (Band 10) image to {out_path}' )
        
        if os.path.exists(out_path) == False or config.overwrite == True:
            em_10_band = rasterio.open( out_path, 'w', **kwargs)
            em_10_band.write( em_img_10, 1 )
            em_10_band.close()

        #  Write NDVI Image to Disk
        kwargs.update( { 'dtype': band_info['ndvi']['image'].dtype } )

        out_path = os.path.join( os.path.dirname( band_info['band04']['path'] ),
                                 f'emissivity_{code}11.epsg_{epsg}.tif' )
        
        logger.debug( f'Writing Emissivity (Band 11) Image to {out_path}' )
        
        if os.path.exists(out_path) == False or config.overwrite == True:
            em_11_band = rasterio.open( out_path, 'w', **kwargs)
            em_11_band.write( em_img_11, 1 )
            em_11_band.close()

    
if __name__ == '__main__':
    main()