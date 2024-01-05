#  Set of utilities for making it easier to work with OpenET data.
#
#

import datetime, logging, os, re

def create_path( base_dir, garden_id, date_str, file_type ):

    img_folder = 'geotiff'
    filename = f'openet_{garden_id}_{date_str}'

    if file_type == 'zip':
        filename = f'{filename}.zip'
        img_folder = 'raw'
    elif file_type == 'geotiff':
        filename = f'{filename}.tif'
        img_folder = 'geotiff'
    else:
        raise Exception( f'Unsupported file_type: {file_type}' )
    
    return os.path.join( base_dir, img_folder, filename )

def check_data_exists( base_dir, garden_id, date_start, num_days, file_type ):

    logger = logging.getLogger('OpenET')
    
    for x in range (0, num_days):

        date = date_start + datetime.timedelta( days = x )
        date_str = date.strftime('%Y%m%d')
        
        p = create_path( base_dir, garden_id, date_str, file_type )

        if os.path.exists( p ):
            logger.error( f'OpenET data exists for date: {date}' )
            return True
    
    return False

def get_frame_list( base_dir, garden_id ):

    #  Example path: openet_a211N000002Jm8Q_20230805.tif
    pattern = 'openet_[a-zA-Z0-9]{15}_[0-9]{8}.tif'

    output = []
    
    # Get list of files which meet the pattern
    for (root, d, files) in os.walk( os.path.join( base_dir, 'geotiff' ) ):

        # Check if matches pattern
        for f in files:
            if re.fullmatch( pattern, f ) is not None:

                parts = os.path.splitext( f )[0].split('_')
                assert(len(parts) == 3)

                if garden_id == parts[1]:
                    output.append( { 'path': os.path.join( root, f ),
                                     'date': datetime.datetime.strptime( parts[2], '%Y%m%d') } )
                    
    return output
                    
