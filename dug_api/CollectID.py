
import datetime, enum, os, re
import pandas as pd

class Sensor(enum.Enum):
    C = 'C' # OLI/TIRS Combined
    O = 'O' # OLI-only
    T = 'T' # TIRS-only
    E = 'E' # ETM+

    @staticmethod
    def from_str( value ):
        if value == 'C':
            return Sensor.C
        if value == 'O':
            return Sensor.O
        if value == 'T':
            return Sensor.T
        if value == 'E':
            return Sensor.E
        return None

class ProductType(enum.Enum):
    L1GT   = enum.auto()
    L1TP   = enum.auto()
    L2SP   = enum.auto()
    ARD_CU = enum.auto()

    def is_ard(self):
        if self == ProductType.ARD_CU:
            return True
        return False

    def type(self):
        if self.is_ard():
            return 'ARD'
        return self.name

    def description(self):

        if self == Product.L1GT:
            return 'Collection 2, Level 1, Systematic Terrain Correction'
            
        if self == Product.L1TP:
            return 'Collection 2, Level 1, Precision and Terrain Correction'
            
        if self == Product.L2SP:
            return 'Collection 2, Level 2, Science Product'
            
        if self == Product.ARD_CU:
            return 'Analysis Ready Data (ARD), CONUS'
        raise Exception('Unknown type')

    @staticmethod
    def from_str( value ):
        if value == 'L1GT':
            return ProductType.L1GT
        if value == 'L1TP':
            return ProductType.L1TP
        if value == 'L2SP':
            return ProductType.L2SP
        if value == 'CU':
            return ProductType.ARD_CU
        raise Exception( f'Unsupported type: {value}' )


class FileType(enum.Enum):

    ANG      = enum.auto()
    B1       = enum.auto()
    B2       = enum.auto()
    B3       = enum.auto()
    B4       = enum.auto()
    B5       = enum.auto()
    B6       = enum.auto()
    B7       = enum.auto()
    B8       = enum.auto()
    B9       = enum.auto()
    B10      = enum.auto()
    B11      = enum.auto()
    BT_B6    = enum.auto()
    ST_B6    = enum.auto()
    ST_CDIST = enum.auto()
    ST_EMIS  = enum.auto()
    ST_QA    = enum.auto()
    UNKNOWN  = enum.auto() # For everything else

    def description(self):
        raise Exception( f'Unsupported type{self}' )

    def to_file_key(self):
        return f'{self.name}_path'
        
    @staticmethod
    def create_empty_dict():
        data = {}
        for f in filter( lambda x: x != FileType.UNKNOWN, list(FileType)):
            data[f'{f.name}_path'] = None

        return data
        
    @staticmethod
    def from_str( value ):
        return FileType[value]

    @staticmethod
    def check_collection_column_is_file( column_name,
                                         is_reprojected,
                                         is_image ):

        regex = '[a-zA-Z0-9]{1,}_path'
        if is_reprojected:
            raise Exception('No longer working.')
            regex = '[a-zA-Z0-9]{1,}_reprojected_path'
        
        res = re.match( regex, column_name )
        if res is None:
            return False
        sp = res.span()
        if (sp[1]-sp[0]) != len(column_name):
            return False

        # If the type must be an image, check against the master list
        if is_image:
            img_types = [ f'B{x}' for x in range(1,12) ]
            for img_type in img_types:
                if img_type in column_name:
                    return True
            return False
                
        return True
        
class CollectID:

    def __init__( self, pathname, is_file = False ):

        self.m_pathname = pathname
        self.m_is_file  = is_file

    def pathname(self):
        return self.m_pathname

    def cid(self):
        '''
        Return the Collection ID. 

        This method is really weird and super customized based on product-type.
        '''
        if self.m_is_file:
            bname = os.path.basename(self.pathname())

            #  Locate the processing-level, without calling processing_level() function
            proc_level = self.pathname().split('_')[1]
            
            #  Ignore the collection number
            proc_levels = [ 'L1TP', 'L1GT', 'CU' ]
            if proc_level in proc_levels:
                regex = 'L[COTE][0-9]{2}_[a-zA-Z0-9]{2,4}_[0-9]{6}_[0-9]{8}_[0-9]{8}_[0-9]{2}'
                res = re.match( regex, os.path.basename( self.pathname() ) )
                return res[0]

        else:
            # Stop at the 6th underscore
            regex = 'L[COTE][0-9]{2}_[a-zA-Z0-9]{2,4}_[0-9]{6}_[0-9]{8}_[0-9]{8}_[0-9]{2}'
            res = re.match( regex, os.path.basename( self.pathname() ) )
            return res[0]

    def sensor(self):
        return Sensor.from_str( self.cid()[1] )

    def satellite(self):
        return int(self.cid()[2:4])

    def processing_level(self):

        substr = self.cid()[5:]
        idx = substr.find('_')
        return ProductType.from_str(substr[0:idx])
        

    def wrs2_path(self):

        if self.processing_level().is_ard():
            return None

        tpstr = self.processing_level().name[0:2]
        if tpstr == 'L1' or tpstr == 'L2':

            pl_us = self.cid()[5:].find('_')
            wrs_substr = self.cid()[5:][pl_us+1:pl_us+7]
            return int(wrs_substr[0:3])

    def wrs2_row(self):

        if self.processing_level().is_ard():
            return None

        tpstr = self.processing_level().name[0:2]
        if tpstr == 'L1' or tpstr == 'L2':

            pl_us = self.cid()[5:].find('_')
            wrs_substr = self.cid()[5:][pl_us+1:pl_us+7]
            return int(wrs_substr[3:6])
        
    def ard_col(self):

        if not self.processing_level().is_ard():
            return None

        tpstr = self.processing_level()
        if tpstr == ProductType.ARD_CU:

            pl_us = self.cid()[5:].find('_')
            ard_substr = self.cid()[5:][pl_us+1:pl_us+7]
            return int(ard_substr[0:3])

    def ard_row(self):

        if not self.processing_level().is_ard():
            return None

        tpstr = self.processing_level()
        if tpstr == ProductType.ARD_CU:

            pl_us = self.cid()[5:].find('_')
            ard_substr = self.cid()[5:][pl_us+1:pl_us+7]
            return int(ard_substr[3:6])

    def acquisition_date( self ):

        #  We need the substring after the third underscore
        sub = self.cid()
        for x in range( 0, 3 ):
            us_idx = sub.find('_')
            sub = sub[us_idx+1:]

        return datetime.date( year=int(sub[0:4]),
                              month = int(sub[4:6]),
                              day = int(sub[6:8]) )
    def production_date( self ):

        #  We need the substring after the fourth underscore
        sub = self.cid()
        for x in range( 0, 4 ):
            us_idx = sub.find('_')
            sub = sub[us_idx+1:]

        return datetime.date( year=int(sub[0:4]),
                              month = int(sub[4:6]),
                              day = int(sub[6:8]) )

    def collection_number(self):
        
        #  We need the substring after the fifth underscore
        sub = self.cid()
        for x in range( 0, 5 ):
            us_idx = sub.find('_')
            sub = sub[us_idx+1:]
        return int(sub[0:2])

    def file_type(self):
        if self.m_is_file:
            
            #  We need the substring after the seventh underscore
            sub = os.path.splitext( os.path.basename(self.pathname()))[0]

            #  For ARD, we don't have a "tier"
            if self.processing_level().is_ard():

                for x in range( 0, 6 ):
                    us_idx = sub.find('_')
                    sub = sub[us_idx+1:]

                return FileType.from_str(sub)

            else:
                for x in range( 0, 7 ):
                    us_idx = sub.find('_')
                    sub = sub[us_idx+1:]

                #  Landsat 7 likes to add B6_VCID_1 or things like that.
                if self.satellite() == 7:
                    if sub == 'B6_VCID_1':
                        sub = 'B6'
                    elif sub == 'B6_VCID_2':
                        sub = 'B10'
                
                #  Some sensor types (L2SP for example), add SR_B5 or a product
                #  designation with it.
                if self.processing_level() == ProductType.L2SP:
                    us_idx = sub.find('_')
                    sub = sub[us_idx+1:]

                return FileType.from_str(sub)
        
        return None

    def to_cid_folder(self):

        #  Remove the file type
        if self.file_type() is not None:
            raise Exception('Not ready to figure this out yet.')
        if self.m_is_file:
            raise Exception('Not ready to deal with files yet.')

        # Stop at the 6th underscore
        regex = 'L[COTE][0-9]{2}_[a-zA-Z0-9]{2,4}_[0-9]{6}_[0-9]{8}_[0-9]{8}_[0-9]{2}'
        res = re.match( regex, os.path.basename( self.pathname() ) )
        return res[0]
            
    @staticmethod
    def from_pathname( pathname ):

        #  Convert to directory name
        cid = os.path.basename( pathname )

        #  Check against regex list
        regex = 'L[COTE][0-9]{2}_[a-zA-Z0-9]{2,4}_[0-9]{6}_[0-9]{8}_[0-9]{8}_[0-9]{2}'
        res = re.match( regex, cid )
        if res is None:
            return None
        
        sp = res.span()
        if sp[0] != 0 or (sp[1]-sp[0]) != len( cid ):
            return None

        #  Otherwise, valid CID
        return CollectID( pathname )

    @staticmethod
    def list_to_dataframes( cid_list ):

        data = { 'pathname': [],
                 'cid': [],
                 'sensor': [],
                 'satellite': [],
                 'product_type': [],
                 'processing_level': [],
                 'wrs2_path': [],
                 'wrs2_row': [],
                 'ard_col': [],
                 'ard_row': [],
                 'acquisition_date': [],
                 'production_date': [] }

        #  File types are managed by the enum
        ftypes = FileType.create_empty_dict()
        for ftype in ftypes:
            data[ftype] = []
        
        for cid in cid_list:
            data['pathname'].append( cid.pathname() )
            data['cid'].append( cid.cid() )
            data['sensor'].append( cid.sensor().name )
            data['satellite'].append( cid.satellite() )
            data['product_type'].append( cid.processing_level().type() )
            data['processing_level'].append( cid.processing_level().name )
            data['wrs2_path'].append( cid.wrs2_path() )
            data['wrs2_row'].append( cid.wrs2_row() )
            data['ard_col'].append( cid.ard_col() )
            data['ard_row'].append( cid.ard_row() )
            data['acquisition_date'].append( cid.acquisition_date() )
            data['production_date'].append( cid.production_date() )

            #  Create dictionary we can update with files we discover
            available_files = FileType.create_empty_dict()
                
            #  Check all files in folder
            for (root,d,files) in os.walk( cid.pathname() ):
                for f in files:
                    pname = os.path.join( root, f )
                    fkey = None
                    try:
                        c = CollectID( pname, is_file=True )

                        #  Landsat 7 adds VCID_# to the end of the file
                        fkey = c.file_type().to_file_key()
                    except Exception as e:
                        continue

                    if available_files[fkey] != None:
                        raise Exception( f'File cannot be set for key ({fkey}) with existing path: {available_files[fkey]}. New {c.pathname()}' )
                    available_files[fkey] = c.pathname()
                    
            #  Update the list
            for key in available_files:
                data[key].append( available_files[key] )
        
        collect_list_df = pd.DataFrame( data )
        return collect_list_df
        