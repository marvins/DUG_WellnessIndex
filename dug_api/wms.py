
import pyproj

import rasterio
from rasterio import MemoryFile, crs, warp
from rasterio import Affine as A

from urllib.request import urlopen

class WMS:

    def __init__(self,
                 url          = None, 
                 epsg_code    = None,
                 center_ll    = None,
                 win_size_pix = None,
                 gsd          = None,
                 layers       = None,
                 transparent  = False,
                 format       = None ):

        if url:
            self.url = url
        if epsg_code:
            self.epsg_code = epsg_code
        if center_ll:
            self.center_ll = center_ll
        if win_size_pix:
            self.win_size_pix = win_size_pix
        if gsd:
            self.gsd = gsd
        if layers:
            self.layers = layers
        if transparent != None:
            self.transparent = transparent
        if format:
            self.format = format
            
    def get_bbox(self):

        if self.center_ll:

            #  Convert center to destination coordinate
            xform = pyproj.Transformer.from_crs( 4326, 
                                                 self.epsg_code,
                                                 always_xy=True )

            center_out = xform.transform( self.center_ll[0],
                                          self.center_ll[1] )

            #  Compute bounds
            min_x = center_out[0] - self.gsd * ( self.win_size_pix[0] / 2.0 )
            min_y = center_out[1] - self.gsd * ( self.win_size_pix[1] / 2.0 )
            max_x = center_out[0] + self.gsd * ( self.win_size_pix[0] / 2.0 )
            max_y = center_out[1] + self.gsd * ( self.win_size_pix[1] / 2.0 )

            return [ min_x, min_y, max_x, max_y ]
        
    def get_map_url( self ):

        bbox = self.get_bbox()
        
        layer_str = ''
        counter = 0
        for layer in self.layers:
            if counter > 0:
                layer_str += ','
            layer_str += layer
            counter += 1
        
        request_type = 'GetMap'
        url = f'{self.url}&request={request_type}'
        url = f'{url}&layers={layer_str}'

        if self.transparent is None:
            pass
        else:
            url = f'{url}&transparent={self.transparent}'
        
        url = f'{url}&crs=EPSG:{self.epsg_code}'
        url = f'{url}&format={self.format}'
        url = f'{url}&width={self.win_size_pix[0]}'
        url = f'{url}&height={self.win_size_pix[1]}'
        url = f'{url}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}'

        return url

def load_tile( base_url,
               epsg,
               center_ll,
               win_size_pix,
               gsd,
               layers,
               format ):

    wms_map = WMS( url          = base_url,
                   epsg_code    = epsg,
                   center_ll    = center_ll,
                   win_size_pix = win_size_pix,
                   gsd          = gsd,
                   layers       = layers,
                   format       = format )
    
    url = wms_map.get_map_url()

    profile = { 'transform': A.identity() }
    tif_bytes = urlopen(url).read()
    with MemoryFile(tif_bytes) as memfile:
        with memfile.open( **profile ) as dataset:
            return dataset.read()
    #            show(dataset)