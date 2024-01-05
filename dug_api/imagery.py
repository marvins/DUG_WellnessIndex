
import rasterio
from rasterio import crs, MemoryFile, warp
from rasterio.windows import Window

import logging, math, os

import numpy as np

import pyproj

import matplotlib as mpl

def get_window_from_coords( bl_corner,
                            tr_corner,
                            coord_epsg,
                            band,
                            ret_type = 'int' ):

    xform = band.transform.__invert__()

    bl_pix = xform * bl_corner
    tr_pix = xform * tr_corner
        
    return Window( bl_pix[0],
                   bl_pix[1],
                   math.ceil(abs(tr_pix[0] - bl_pix[0])),
                   math.ceil(abs(tr_pix[1] - bl_pix[1])) )
    
    
def get_image_bbox( band ):

    pass
    
def reproject_image( path_out,
                     epsg,
                     bbox_utm,
                     dest_gsd,
                     path_in  = None,
                     src_band = None ):

    if ( path_in is None or not os.path.exists( path_in ) ) and src_band is None:
        raise Exception( f'Cannot open {path_in} as image does not exist.' )

    #  Open the input image path
    if src_band is None:
        logging.debug( f'Opening input image: {path_in}' )
        src_band = rasterio.open( path_in )

    dst_crs = crs.CRS.from_epsg( epsg )


    #  Solve for a transform that takes us to the preferred output dimensions
    dst_xform, dst_width, dst_height = warp.calculate_default_transform( src_crs = src_band.crs,
                                                                         dst_crs = dst_crs,
                                                                         width = src_band.width,
                                                                         height = src_band.height,
                                                                         left   = min( bbox_utm[0][0], bbox_utm[1][0] ),
                                                                         right  = max( bbox_utm[0][0], bbox_utm[1][0] ),
                                                                         bottom = min( bbox_utm[0][1], bbox_utm[1][1] ), 
                                                                         top    = max( bbox_utm[0][1], bbox_utm[1][1] ),
                                                                         resolution = dest_gsd )
    
    # Create Destination Band
    kwargs = src_band.meta.copy()
    kwargs.update({
        'crs': dst_crs,
        'transform': dst_xform,
        'width': dst_width,
        'height': dst_height,
        'compress': 'lzw'
    })

    #open destination raster   
    destBand = rasterio.open( path_out, 'w', **kwargs)

    # Now actually warp the image
    bilinear = rasterio.enums.Resampling.bilinear
    dst_img, affine = warp.reproject( source         = rasterio.band(src_band, 1),
                                      destination    = rasterio.band(destBand, 1),
                                      dst_transform  = dst_xform,
                                      dst_crs        = dst_crs,
                                      dst_resolution = dest_gsd,
                                      resampling     = bilinear )

    destBand.close()

    #  Grab the image for grins
    tmpBand = rasterio.open( path_out )
    dst_img_copy = tmpBand.read().astype('f4')
    return dst_img_copy

def reproject_image2( src_band,
                      epsg,
                      center_ll,
                      window_size,
                      gsd ):

    dst_crs = crs.CRS.from_epsg( epsg )

    #  Compute the source bounds 
    bl_pt = src_band.transform * (0,0)
    br_pt = src_band.transform * ( src_band.width -1, 0 )
    tl_pt = src_band.transform * ( 0, src_band.height-1)
    tr_pt = src_band.transform * ( src_band.width-1,src_band.height-1)
    
    #  Create output bounds in destination coordinate system
    dest_xform = pyproj.Transformer.from_crs( 4326, 
                                              epsg, 
                                              always_xy=True )
    center_utm = dest_xform.transform( center_ll[0], center_ll[1] )
    dest_window = { 'left':   center_utm[0] - gsd * (window_size[0]-1)/2.0,
                    'right':  center_utm[0] + gsd * (window_size[0])/2.0,
                    'top':    center_utm[1] + gsd * (window_size[1])/2.0,
                    'bottom': center_utm[1] - gsd * (window_size[1]-1)/2.0 }
    
    dst_xform, dx, dy = warp.calculate_default_transform( src_crs = src_band.crs,
                                                          dst_crs = dst_crs,
                                                          width   = src_band.width,
                                                          height  = src_band.height,
                                                          left    = dest_window['left'],
                                                          right   = dest_window['right'],
                                                          top     = dest_window['top'],
                                                          bottom  = dest_window['bottom'],
                                                          resolution = gsd )
    
    #  Create temporary file
    kwargs = src_band.meta.copy()
    kwargs.update({
        'crs':       dst_crs,
        'transform': dst_xform,
        'width':     dx,
        'height':    dy
    })
    dst_file = MemoryFile()
    dst_band = dst_file.open( **kwargs )
    
    #  Create reprojection
    for idx in range( 0, src_band.count):
        warp.reproject( source         = rasterio.band( src_band, idx + 1 ),
                        destination    = rasterio.band( dst_band, idx + 1 ),
                        dst_transform  = dst_xform,
                        dst_crs        = dst_crs,
                        dst_resolution = gsd,
                        resampling     = rasterio.enums.Resampling.bilinear )

    
    center_dest = dst_xform.__invert__() * (center_utm[0], center_utm[1])
    
    win = Window( center_dest[0] - window_size[0]/2,
                  center_dest[0] - window_size[1]/2,
                  window_size[0],
                  window_size[1] )
    
    return np.transpose( dst_band.read(), axes=[1,2,0] )

def create_merged_heatmap_tile( top_image,
                                base_image, 
                                t, 
                                temp_range = None ):

    #  Convert Basemap to Float32 with 8-bit pixel range
    bs_max = np.nanmax( base_image )
    bs_min = np.nanmin( base_image )
    bs_img = base_image.astype('float32')

    #  Convert Top image to heatmap
    if temp_range is None:
        hm_max = np.nanmax( top_image )
        hm_min = np.nanmin( top_image )
    else:
        hm_min = temp_range[0]
        hm_max = temp_range[1]
        
    hm = ( top_image - hm_min ) / (hm_max - hm_min)
    cm = mpl.colormaps['jet']
    hm_col = ( cm(hm) * 255 ).astype('float32')[:,:,:3]

    res_img = ((hm_col * t) + (bs_img * (1-t))).astype('uint8')

    return res_img, [hm_min, hm_max]
