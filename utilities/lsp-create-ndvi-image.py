#!/usr/bin/env python3

import argparse, configparser, logging, os, sys

import rasterio

from pylandtemp import ndvi

#  DUG API
sys.path.insert(0,'.')
import dug_api.coordinate as crd
from dug_api import Database, imagery
from dug_api.CollectID import CollectID, FileType
from dug_api.config import Configuration

def parse_command_line():

    parser = argparse.ArgumentParser(description='Create NDVI image.')

    parser.add_argument( '--red',
                         dest='red_path',
                         required=False,
                         help='Location of red band.' )

    parser.add_argument( '--nir',
                         dest='nir_path',
                         required=False,
                         help='Location of near-infrared band.' )

    parser.add_argument( '--ndvi',
                         dest='ndvi_path',
                         required=False,
                         help='Where to write output.' )

    parser.add_argument( '--mask',
                         dest='mask_path',
                         required=False,
                         help='Where to write output.' )

    parser.add_argument( '-v',
                         dest='verbose',
                         default=False,
                         action='store_true',
                         required=False,
                         help='Use verbose logging.' )
    
    parser.add_argument( '-vv',
                         dest='super_verbose',
                         default=False,
                         action='store_true',
                         required=False,
                         help='Use super verbose logging.' )
    
    parser.add_argument( '--cid',
                         dest = 'cid_path',
                         required=False,
                         help = 'Location of Collection ID.' )
    
    parser.add_argument( '-c',
                         dest='config_path',
                         required = False,
                         help = 'Config path' )
    
    return parser.parse_args()

def main():

    cmd_options = parse_command_line()

    #  Configure Logging
    if cmd_options.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('rasterio').setLevel(logging.INFO)

    elif cmd_options.super_verbose:
        logging.basicConfig(level=logging.DEBUG)
        
    else:
        logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger('Notebook')


    #  if CID provided, use it to solve for paths
    if cmd_options.cid_path is None:
        red_path = cmd_options.red_path
        nir_path = cmd_options.nir_path
        ndvi_path = cmd_options.ndvi_path

    else:
        config = Configuration( cmd_options.config_path )
        epsg = config.get_output_epsg()

        # Load the collection config, if it doesnt already exist
        cid_config_path = os.path.join( cmd_options.cid_path, 'config.cfg' )

        cid_config = configparser.ConfigParser()
        if os.path.exists( cid_config_path ) == False:
            logger.error( f'CID has no configuration file. Creating one at {cid_config_path}' )
            assert(False)
    
        logger.info( f'Loading CID Config: {cid_config_path}' )
        cid_config.read( cid_config_path )

        red_path  = cid_config['general'][f'b4_path_epsg_{epsg}']
        nir_path  = cid_config['general'][f'b5_path_epsg_{epsg}']
        ndvi_path = os.path.join( os.path.dirname(red_path), f'ndvi.epsg_{epsg}.tif' )

    assert( os.path.exists( red_path ) )
    assert( os.path.exists( nir_path ) )
    band04_handle = rasterio.open( red_path )
    band05_handle = rasterio.open( nir_path )

    #  Read images using rasterio
    band04_image = band04_handle.read(1).astype('f4')
    band05_image = band05_handle.read(1).astype('f4')

    #  Create Mask Image
    mask = (band04_image == 0)

    ndvi_image = ndvi( band05_image,
                       band04_image,
                       mask = mask )

    # Create Destination Band Metadata
    kwargs = band04_handle.meta.copy()
    kwargs.update({
        'crs': band04_handle.crs,
        'transform': band04_handle.transform,
        'width': band04_handle.width,
        'height': band04_handle.height,
        'dtype': ndvi_image.dtype } )
            
    logger.debug( f'Writing NDVI Image to {ndvi_path}' )
    ndvi_band = rasterio.open( ndvi_path, 'w', **kwargs)
    ndvi_band.write( ndvi_image.astype(rasterio.float32), 1 )
    ndvi_band.close()

    
if __name__ == '__main__':
    main()