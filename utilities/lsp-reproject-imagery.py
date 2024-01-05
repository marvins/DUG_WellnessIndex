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


def is_band_key( keyname ):
    if re.fullmatch( 'b[0-9]{1,2}_path', keyname ) is None:
        return False
    return True

def parse_command_line():
    '''Parse command-line options'''

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

    logger = logging.getLogger('Reprojection')
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

    #  Get only band keys (non EPSG keys)
    band_keys = list( filter( is_band_key, list(cid_config['general'] ) ) )
    for band_key in band_keys:

        # Key for output path
        key_out = f'{band_key}_epsg_{epsg}'

        #  Check if the image path exists
        path_in  = cid_config.get('general',band_key)

        filename_out = f'{os.path.splitext( os.path.basename( path_in ) )[0]}.epsg_{epsg}.TIF'
        path_out = os.path.join( os.path.dirname( path_in ), filename_out )
        assert( os.path.exists( path_in ) )

        logging.debug( f'Reprojecting {os.path.basename(path_in)} to {os.path.basename(path_out)}' )
        if os.path.exists( path_out ):
            logging.debug( f'Skipping {band_key} as destination image already exists.' )

        else:
            # Reproject image
            imagery.reproject_image( path_in  = path_in,
                                     path_out = path_out,
                                     epsg     = epsg,
                                     bbox_utm = bbox_utm,
                                     dest_gsd = dest_gsd )


if __name__ == '__main__':
    main()
