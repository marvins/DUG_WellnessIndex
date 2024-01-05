
import rasterio
import datetime, os

class PlanetImageParser:

    def __init__( self, pathname ):

        self.pathname = pathname

    def get_timestamp(self):

        #  Datetime
        img_driver = rasterio.open( self.pathname )
        date_str = str(img_driver.tags(0)['TIFFTAG_DATETIME'])

        pattern = '%Y:%m:%d %H:%M:%S'
        ts = datetime.datetime.strptime( date_str, pattern )
        return ts

    def get_gsd(self):

        img_driver = rasterio.open( self.pathname )
        xform = img_driver.transform
        return min(abs(xform.a), abs(xform.e))

    def get_type(self):

        parts = self.pathname.split('.')
        #print(parts)
        if len(parts) < 4:
            return 'IMAGE'
        if parts[-2] == 'ndvi':
            return 'NDVI'
        return None
        
    def get_fields(self):

        ts = self.get_timestamp()

        return { 'pathname': [self.pathname],
                 'type':     [self.get_type()],
                 'datetime': [self.get_timestamp()],
                 'gsd':      [self.get_gsd()] }

    def to_log_string(self):

        str  =  'PlanetImage:\n'
        str += f'    Date: {self.get_timestamp()}\n'
        str += f'    GSD: {self.get_gsd()} m/pix'

        return str
        