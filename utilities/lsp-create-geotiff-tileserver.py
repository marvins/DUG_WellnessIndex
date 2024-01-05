#!/usr/bin/env python
#
#  Application which takes a huge directory of geotiffs and does the following:
# 
# 1. Reprojects all images to the same CRS and GSD
# 2. Optionally create overviews for all images
# 3. Build a VRT file


import argparse, itertools, os, subprocess
from operator import itemgetter
import rasterio
from rasterio import crs, warp
import pyproj

def parse_command_line():

    parser = argparse.ArgumentParser(description='Build really big VRT files, then tile everything.')

    parser.add_argument( '-i', '--image-list-file',
                         required=False,
                         default=None,
                         dest='image_list_path',
                         help='Path to image list in txt format.' )
    
    parser.add_argument( '-s', '--source-folder',
                         required=True,
                         dest='src_folder',
                         help='Location of imagery to build tile index for.' )

    parser.add_argument( '-d', '--destination-folder',
                         required=True,
                         dest='dst_folder',
                         help='Location where to put reprojected imagery.' )

    parser.add_argument( '-e', '--epsg-code',
                         dest='epsg_code',
                         required=True,
                         help='EPSG code to use.',
                         type=int )

    parser.add_argument( '-g','--gsd',
                         dest='gsd',
                         required=True,
                         help='Ground Sample Distance (Meters per Pixel)' )
    
    parser.add_argument( '-n', '--vrt-name',
                         dest='vrt_name',
                         required=True,
                         help='Name of VRT file.' )

    parser.add_argument( '--skip-if-exists',
                         dest='skip_reprojection_if_exists',
                         default=False,
                         action='store_true',
                         required=False,
                         help='Skip reprojecting imagery if destination image exists.' )

    parser.add_argument( '-b', '--build-pyramids',
                         dest='build_pyramids',
                         default=False,
                         action = 'store_true',
                         required=False,
                         help = 'Build pyramids if they don\'t already exist.' )

    return parser.parse_args()


def estimate_gsd( src_band,
                  dst_epsg ):

    #  Grab band information
    xform = src_band.transform
    shape = src_band.shape

    #  Get the source coordinates
    src_pixels = list(itertools.product( [ 0, src_band.width - 1 ],
                                         [ 0, src_band.height - 1 ]))
    
    src_points = [ xform * p for p in src_pixels ]

    src_extent_x = max( src_points, key = itemgetter(0) )[0] - min( src_points, key = itemgetter(0) )[0]
    src_extent_y = max( src_points, key = itemgetter(1) )[1] - min( src_points, key = itemgetter(1) )[1]

    #  Create PyProj transformer and convert to destination
    prj_xform = pyproj.Transformer.from_crs( src_band.crs.to_epsg(),
                                             dst_epsg,
                                             always_xy=True )

    dst_points = [ prj_xform.transform( p[0], p[1] ) for p in src_points ]

    #  Sort tuples by x
    dst_extent_x = max( dst_points, key = itemgetter(0) )[0] - min( dst_points, key = itemgetter(0) )[0]
    dst_extent_y = max( dst_points, key = itemgetter(1) )[1] - min( dst_points, key = itemgetter(1) )[1]

    return max( dst_extent_x / shape[1], dst_extent_y / shape[0] )


    
def find_geotiffs( image_folder ):

    ext_list = ['.tif','.tiff']
    results = []
    for base, dirs, files in os.walk(image_folder):
        for f in files:

            if os.path.splitext( f )[-1].lower() in ext_list:
                fpath = os.path.join( base, f )
                results.append(fpath)

    return results

def load_image_list( list_path ):

    data = []
    with open( list_path ) as fin:
        for line in fin.readlines():
            data.append( line.strip() )
    return data

def reproject_imagery( options ):

    #  Locate all GeoTiffs within the folder
    if options.image_list_path is None:
        image_list = find_geotiffs( options.src_folder )
    else:
        image_list = load_image_list( options.image_list_path )

    #  Create Destination CRS
    dest_crs = crs.CRS.from_epsg( options.epsg_code )

    #  Iterate through each image
    for image in image_list:

        dest_path = os.path.join( options.dst_folder, 'gtiff', f'{os.path.splitext( os.path.basename( image ) )[0]}.tif' )

        if os.path.exists( dest_path ) and options.skip_reprojection_if_exists:
            print( f' -> Skipping reprojection of {image} as it already exists at {dest_path}' )
            continue

        #  Load image band
        band = rasterio.open( image )

        src_xform = band.transform

        #  Transform corners to source coordinates
        bl = src_xform * ( 0, 0 )
        br = src_xform * ( band.width-1, 0 )
        tl = src_xform * ( 0, band.height-1 )
        tr = src_xform * ( band.width-1, band.height-1 )

        left    = min( bl[0], tl[0], br[0], tr[0] )
        right   = max( bl[0], tl[0], br[0], tr[0] )
        top     = max( bl[1], tl[1], br[1], tr[1] )
        bottom  = min( bl[1], tl[1], br[1], tr[1] )

        #  Transform corners to destination coordinates
        left, bottom, right, top = warp.transform_bounds( src_crs = band.crs,
                                                          dst_crs = dest_crs,
                                                          left    = min( bl[0], tl[0], br[0], tr[0] ),
                                                          right   = max( bl[0], tl[0], br[0], tr[0] ),
                                                          top     = max( bl[1], tl[1], br[1], tr[1] ),
                                                          bottom  = min( bl[1], tl[1], br[1], tr[1] ) )
        
        print( f''' -> Processing Image: {os.path.basename(image)}
        Width: {band.width}
        Height: {band.height}
        Left: {left}
        Right: {right}
        Top:   {top}
        Bottom: {bottom}
        Extend (m) [X: {left - right}, Y: {top-bottom}''')

        #  Solve for a transform that takes us to the preferred output dimensions
        dst_xform, dst_width, dst_height = warp.calculate_default_transform( src_crs    = band.crs,
                                                                             dst_crs    = dest_crs,
                                                                             width      = band.width,
                                                                             height     = band.height,
                                                                             resolution = options.gsd,
                                                                             left       = left,
                                                                             right      = right,
                                                                             top        = top,
                                                                             bottom     = bottom )

        print( f'''     Transform: {dst_xform}
        Width: {dst_width}
        Height: {dst_height}''' )

        
        # Create Destination Band
        kwargs = band.meta.copy()
        kwargs.update({
            'crs': dest_crs,
            'transform': dst_xform,
            'width': dst_width,
            'height': dst_height
        })

        # open destination raster
        gtiff_folder = os.path.join( options.dst_folder, 'gtiff' )
        if not os.path.exists( gtiff_folder ):
            os.makedirs( gtiff_folder )
        print( f'    -> Writing output to {dest_path}' )
        
        # Now actually warp the image
        with rasterio.open( dest_path, 'w', **kwargs ) as dst:

            metadata = band.tags(0)
            dst.update_tags( **metadata )
            for i in range(1, band.count + 1):

                warp.reproject( source        = rasterio.band( band, i ),
                                destination   = rasterio.band( dst, i ),
                                src_transform = band.transform,
                                src_crs       = band.crs,
                                dst_transform = dst_xform,
                                dst_crs       = dest_crs,
                                resampling    = warp.Resampling.bilinear )

def build_pyramids( options ):

     #  Navigate to destination folder
    current_path = os.getcwd()

    os.chdir( os.path.join( options.dst_folder, 'gtiff' ) )

    gtiff_list = find_geotiffs( '.' )

    print( ' -> Creating Overviews' )

    for gtiff in gtiff_list:

        ovr_path = f'{gtiff}.ovr'
        if os.path.exists( ovr_path ):
            print( f'    -> Skipping Overview for {ovr_path} as it already exists.' )
            continue

        command = f'gdaladdo -ro -r bilinear {gtiff}'
        print(  '    -> Creating Overview' )
        print( f'       CMD: {command}' )
        subprocess.call( command, shell=True )

    os.chdir( current_path )

def build_vrt( options ):

    vrt_path = f'{options.vrt_name}.vrt'
    if os.path.exists( vrt_path ):
        os.remove( vrt_path )
    
    #  Create gdal command
    command = f'gdalbuildvrt {vrt_path} ./gtiff/*.tif'

    #  Navigate to destination folder
    current_path = os.getcwd()

    os.chdir( options.dst_folder )

    print(command)
    subprocess.call( command, shell=True )

def build_tiles( options ):

    pass

def main():

    #  Parse command-line options
    options = parse_command_line()
    
    #  Make sure all imagery has the same projection
    reproject_imagery( options )

    if options.build_pyramids:
        build_pyramids( options )

    #  Construct VRT dataset
    build_vrt( options )

    #  Construct tile set
    build_tiles( options )

if __name__ == '__main__':
    main()
