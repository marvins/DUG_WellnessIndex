#    File:    coordinate.py
#    Author:  Marvin Smith
#    Date:    11/1/2023
#
#    Purpose: Helper scripts for doing coordinate conversions. 
#


from pyproj import Transformer

import numpy as np

def convert_coord_point( point, input_epsg, output_epsg ):
    '''
    Convert a single coordinate from one EPSG into another.
    '''

    xform = Transformer.from_crs( input_epsg,
                                  output_epsg,
                                  always_xy=True )

    dest_point = xform.transform( point[0], point[1] )
    return dest_point

def convert_coord_list( point_list, 
                        input_epsg, 
                        output_epsg ):
    '''
    Convert a list of points from one EPSG into another.  Useful for Polygons and other shapes.
    '''
    output = []
    for point in point_list:
        output.append( convert_coord_point( point,
                                            input_epsg,
                                            output_epsg ) )
    return output

def convert_coord_bbox( bounds, input_epsg, output_epsg ):
    '''
    Convert a ROI from one EPSG to another. 
    Bounds come in the form [corner1, corner2] or [[x1,y1],[x2,y2]]
    '''

    output = []

    pts = []
    pts.append( list(convert_coord_point( [ min( bounds[0][0], bounds[1][0] ), 
                                            min( bounds[0][1], bounds[1][1] ) ], 
                                          input_epsg, output_epsg )) )
    pts.append( list(convert_coord_point( [ max( bounds[0][0], bounds[1][0] ), 
                                            max( bounds[0][1], bounds[1][1] ) ],
                                          input_epsg, output_epsg )) )

    dx = pts[1][0] - pts[0][0]
    dy = pts[1][1] - pts[1][1]
    return [ [ pts[0][0], pts[0][1]], 
             [ pts[1][0], pts[1][1]] ]

def convert_coord_roi( center_coord,
                       input_epsg,
                       window_size_pixels,
                       dest_gsd,
                       output_epsg = None ):

    #  Convert center to dest coords
    if output_epsg is None or output_epsg == input_epsg:
        center_dest = np.array( list( center_coord ) )
    else:
        center_dest = np.array( list( convert_coord_point( center_coord,
                                                           input_epsg,
                                                           output_epsg ) ) )

    #  Create window in coordinate system units
    win_dim = np.array( list( window_size_pixels ) ) / 2.0 * dest_gsd


    return [ center_dest - win_dim,
             center_dest + win_dim ]
    
    
def project_pix2world( xform, corner ):

    res = list( xform * ( corner[0], corner[1] ) )
    print( res )
    
def convert_from_transform( xform, shape, input_crs, output_crs ):

    #  First project corners
    print( project_pix2world( xform, (0,0) ) )


#def create_proj_transform(self):
#
#   utm_crs = CRS.from_epsg( epsg_code )
#   lla_crs = CRS.from_epsg( 4326 ) #  This is the universal geographic (WGS84) model
#
## When we need to convert from Lat/Lon to UTM
#lla_to_utm_xform = Transformer.from_crs( lla_crs, utm_crs, always_xy=True )
#
##  Convert Bottom-Left Corner
#bottom_left_utm = lla_to_utm_xform.transform( bottom_left_ll[0], bottom_left_ll[1] )
#top_right_utm   = lla_to_utm_xform.transform( top_right_ll[0], top_right_ll[1] )
#
#print( f'Bottom Left UTM: {bottom_left_utm}\nTop Right UTM: {top_right_utm}' )