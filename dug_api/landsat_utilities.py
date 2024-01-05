import xml.etree.ElementTree as ET 
from xml.etree.ElementTree import Element, SubElement

import rasterio
from rasterio import MemoryFile, crs, warp
from rasterio.windows import Window
from rasterio import Affine as A

from urllib.request import urlopen

from pyproj import Transformer

import sys

import numpy as np

from . import wms

import matplotlib as mpl
import matplotlib.pyplot as plt

def parse_kvp_entry( line ):
    
    idx = line.find('=')
    key = line[0:idx-1].strip('\'" \n')
    value = line[idx+1:].strip('\'" \n')
    return key, value
    
def add_kvp_entry( MTL, group_queue, key, value ):

    # if the group_queue is empty, done
    if len(group_queue) <= 0:
        MTL[key] = value;
        return MTL

    #  Check if the group is added
    if group_queue[0] not in MTL:
        MTL[group_queue[0]] = {}

    MTL[group_queue[0]] = add_kvp_entry( MTL[group_queue[0]],
                                         group_queue[1:],
                                         key,
                                         value )
    return MTL
    
    
def load_metadata_table( pathname ):
    '''
    Parse a Landsat MTL file and return a large dictionary of Key/Value pairs
    '''
    
    #  Full list of MTL data
    MTL = {}

    group_queue = []
    with open( pathname, 'r' ) as fin:
        for line in fin.readlines():
            key, value = parse_kvp_entry( line )
            
            #  Don't bother with parent node
            if ( key == 'GROUP' or key == 'END_GROUP' ) and value == 'LANDSAT_METADATA_FILE':
                continue
            if key == 'GROUP':
                group_queue.append( value )
            elif key == 'END_GROUP':
                group_queue.pop(-1)
            else:
                MTL = add_kvp_entry( MTL, group_queue, key, value )
    return MTL

def print_mtl( mtl, offset = 0 ):

    tag = ' ' * offset
    for key in mtl:
        if isinstance( mtl[key], dict ):
            print( tag + key )
            Print_MTL( mtl[key], offset + 4 )
        else:
            print( tag + key + ' = ' + mtl[key] )

def parse_placemark_node( placemark_node, ns ):

    coords = placemark_node.find( 'kml:Point', ns ).find( 'kml:coordinates', ns ).text.split(',')

    results = { 'name':       placemark_node.find( 'kml:name', ns ).text,
                'coordinate': [ float(x) for x in coords ] }

    return results
    
def find_all_nodes( base_node, node_to_find ):

    ns = { 'kml': 'http://www.opengis.net/kml/2.2' }

    results = []
    node_list = base_node.findall( 'kml:Placemark', ns )
    for node in node_list:
        results.append( parse_placemark_node( node, ns ) )
    return results        
    
def parse_kml( kml_path ):
    
    tree = ET.parse( kml_path )
    root = tree.getroot()

    ns = { 'kml': 'http://www.opengis.net/kml/2.2' }
    
    #  Iterate over nodes, looking for a Placemark
    placemark_nodes = []
    
    for child in root:        
        placemark_nodes += find_all_nodes( child, 'Placemark' )

    return placemark_nodes    



def load_landsat_tile( lst_path,
                       epsg_code,
                       center_ll,
                       window_size,
                       gsd ):

    src_band = rasterio.open( lst_path )
    dst_crs = crs.CRS.from_epsg( epsg_code )
    
    #  Compute the source bounds 
    bl_pt = src_band.transform * (0,0)
    br_pt = src_band.transform * ( src_band.width -1, 0 )
    tl_pt = src_band.transform * ( 0, src_band.height-1)
    tr_pt = src_band.transform * ( src_band.width-1,src_band.height-1)

    #  Create output bounds in destination coordinate system
    dest_xform = Transformer.from_crs( 4326, epsg_code, always_xy=True )
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



def merge_tiles( top_image, base_image, t, temp_range = None ):

    #  Convert Basemap to Float32 with 8-bit pixel range
    bs_max = np.max( base_image )
    bs_min = np.min( base_image )
    bs_img = base_image.astype('float32')

    #  Convert Top image to heatmap
    if temp_range is None:
        hm_max = np.max( top_image )
        hm_min = np.min( top_image )
    else:
        hm_min = temp_range[0]
        hm_max = temp_range[1]
        
    hm = ( top_image - hm_min ) / (hm_max - hm_min)
    cm = mpl.colormaps['jet']
    hm_col = ( cm(hm) * 255 ).astype('float32')[:,:,:3]

    res_img = ((hm_col * t) + (bs_img * (1-t))).astype('uint8')

    return res_img, [hm_min, hm_max]

def create_lst_heatmap_tile( config, garden, lst_path, window_size, gsd, ratio = 0.75, temp_range = None ):

    epsg_code = config['general']['output_crs_epsg']

    idx = garden.index.tolist()[0]
    name    = garden.loc[idx,'Name']
    win_lat = garden.loc[idx,'Latitude']
    win_lon = garden.loc[idx,'Longitude']
    
    #  First load the landsat tile
    lst_arr = load_landsat_tile( lst_path, 
                                 epsg_code   = epsg_code,
                                 center_ll   = [win_lon, win_lat],
                                 window_size = window_size,
                                 gsd         = gsd )
    shp = lst_arr.shape
    lst_arr = lst_arr.reshape( shp[0], shp[1] )

    #  Load NAIP image
    naip_arr = load_naip_wms_tile( naip_url    = config['naip']['wms_url'],
                                   epsg_code   = epsg_code,
                                   center_ll   = [win_lon, win_lat],
                                   window_size = [1000,1000],
                                   gsd         = gsd,
                                   layers      = config['naip']['wms_layers'].split(','),
                                   format      = config['naip']['wms_format'] )

    naip_arr = np.transpose( naip_arr, axes=[1,2,0] )[:,:,:3]

    mosaic, r = merge_tiles( lst_arr, naip_arr, ratio, temp_range )

    return mosaic, r
