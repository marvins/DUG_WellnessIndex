import configparser

import pandas as pd
import numpy as np

import logging, os, sys

#  Load other DUG APIs
sys.path.insert(0,'..')
import dug_api.coordinate as crd
import dug_api.Database as Database


class Configuration:

    def __init__( self, config_path ):

        config = configparser.ConfigParser()
        config.read( config_path )
        self.config = config

        if os.path.exists( self.get_ls_collection_list_path() ):
            self.ls_collection_df = pd.read_excel( self.get_ls_collection_list_path() )
        else:
            logging.debug( f'No Landsat Collection List at {self.get_ls_collection_list_path()}' )
            self.ls_collection_df = None


    def get( self, section, value ):
        assert( self.config.has_option( section, value ) )
        return self.config[section][value]
        
    def get_ls_collection_list_path(self):
        '''
        Return the path to the Landsat Collection List (Excel file)
        '''
        return self.config['general']['landsat_collection_list_path']

    def get_planet_catalogue(self):
        path = self.config['general']['planet_catalogue']
        if os.path.exists( path ):
            self.planet_catalogue = pd.read_excel( path )
        else:
            self.planet_catalogue = self._create_default_planet_catalogue()

        return self.planet_catalogue

    def update_planet_catalogue(self, catalogue):
        self.planet_catalogue = catalogue
        self.planet_catalogue.to_excel( self.config['general']['planet_catalogue'], index=False ) 
        return self.planet_catalogue
    
    def _create_default_planet_catalogue(self):

        data = { 'pathname': [] }

        return pd.DataFrame( data )
    
    def get_ls_collection_config(self, cid):

        #  Get collection info
        collect_data = self.ls_collection_df.loc[self.ls_collection_df['cid'] == cid]

        # Create collection configuration file
        collect_dir = collect_data['pathname'].values[0]
        config_path = os.path.join( collect_dir, 'config.cfg' )

        # if file doesn't exist, we need a template
        if os.path.exists( config_path ) == False:
            logging.debug( f'CID ({cid}) config.cfg does not exist. Creating.' )
            return self._create_collection_config( config_path, collect_data )
        else:
            config = configparser.ConfigParser()
            config.read( config_path )
            return config

    def set_ls_collection_config(self, config):

        cid = config.get('general','cid')
        collect_dir = config.get('general','pathname')
        config_path = os.path.join( collect_dir, 'config.cfg' )
        logging.debug( f'Writing CID ({cid}) Configuration to {config_path}' )
        with open( config_path, 'w' ) as configfile:
            config.write(configfile)

    def _create_collection_config( self, config_path, collect_data ):

        #  import configparser
        cid = collect_data['cid'].values[0]
        logging.info( f'Building new ls config for cid: {cid}' )
        config = configparser.ConfigParser()
        config['general'] = {}

        for col in list(collect_data):
            if collect_data[col].isna().any() != True:
                config['general'][col] = str(collect_data[col].values[0])

        with open( config_path, 'w' ) as configfile:
            config.write(configfile)

        return config
        
    
    def get_point( self, section, key, is_latlon ):

        if is_latlon:
            point = [self.config.getfloat( section, f'{key}_lon' ),
                     self.config.getfloat( section, f'{key}_lat' ) ]
            return point

        return None
        
    def get_region( self, epsg = None ):

        bl = self.get_point( 'general', 'region_bl', True )
        tr = self.get_point( 'general', 'region_tr', True )
        points = [ [ min( bl[0], tr[0] ), min( bl[1], tr[1]) ],
                   [ max( bl[0], tr[0] ), max( bl[1], tr[1]) ] ]
        print( f'Points: {points}' )

        if epsg is None:
            epsg = self.get_output_epsg()
        
        poly = crd.convert_coord_bbox( points, 4326, epsg )

        return poly
        
        
    def get_output_epsg(self):
        '''
        EPSG code for all projected imagery.
        '''
        return self.config['general']['output_crs_epsg']

    def get_output_gsd(self):
        return self.config['general']['warp_gsd_mpp']
        
    def get_image_collection_path(self):
        '''
        Location of all imagery collection folders.
        '''
        return self.config['general']['image_collection_path']

    
    def update_table( self, table_name, new_entries, update_file=True ):
        '''
        Takes an input table or set of columns and adds them to the table. 
        If the table already has cells populated, they are ignored.
        '''

        #  First, load the table from SQLite
        if self.ls_collection_df is None and isinstance( new_entries, pd.DataFrame ):
            logging.debug( 'Setting Landsat Collection Dataframe to New Data.' )
            self.ls_collection_df = new_entries
            
        elif self.ls_collection_df is None:
            raise Exception( f'Unsupported input entry type: {type(new_entries)}' )

        #  otherwise, merge the columns
        else:
            self._process_rows( new_entries )

        if update_file:
            self.ls_collection_df.to_excel( self.get_ls_collection_list_path(),
                                            index=False )

        return self.ls_collection_df

    def _process_rows( self, new_entries ):
        
        for rdata in new_entries.itertuples(index=False):

            row = rdata._asdict()

            #  Check if the collection id is entered yet
            c = self.ls_collection_df.loc[self.ls_collection_df['cid'] == row['cid']]

            #  If the collection is not present, throw
            if c.shape[0] == 0:

                new_data = {}
                for temp_col in row:
                    new_data[temp_col] = [row[temp_col]]
                new_df = pd.DataFrame( new_data )
                
                self.ls_collection_df = pd.concat( [ self.ls_collection_df, new_df ], ignore_index=True)

            elif c.shape[0] > 1:
                raise Exception( f'Multiple CIDs found: {c["cid"].values}' )
            else:
                for c in row:
                    if '_path' in c:
                        src_val = row[c]
                        dst_val = self.ls_collection_df.loc[self.ls_collection_df['cid'] == row['cid'],c]

                        #  if neither is valid, then do nothing
                        if (dst_val.values[0] is None or dst_val.isna().any() ) and src_val is None:
                            pass
                    
                        #  if destination is empty, but source is valid, set it
                        elif (dst_val.values[0] is None or dst_val.isna().any() ) and src_val != None:
                            self.ls_collection_df.loc[self.ls_collection_df['cid'] == row['cid'],c] = src_val

                        #  If destination is set, and source is empty, do nothing
                        elif (dst_val.values[0] != None and dst_val.isna().any() == False) and src_val is None:
                            pass

                        elif src_val != dst_val.values[0]:
                            #print( f'Likely need to update col: {c}, CID: {row["cid"]}, Column: {c}, Dest: {dst_val}, Source: {src_val}' )
                            pass
        
        
    def is_valid( self ):
        '''
        Simple check to see if the config file was loaded
        properly.
        '''

        if not self.config.has_option('general','output_crs_epsg'):
            return False
        if not self.config.has_option('general','image_collection_path'):
            return False
        if not self.config.has_option('general','landsat_collection_list_path'):
            return False

        return True

    def create_garden_windows( self, affine, epsg, shape, win_width = 1000, win_height = 1000 ):

        #  Get the center coordinate
        xform = affine.__invert__()

        proj_xform = Transformer.from_crs( 4326, epsg_code, always_xy=True )
    
        #  Iterate over each row, creating a rasterio window
        windows = {}
        for index, row in garden_df.iterrows():

            #  Convert LLA to UTM
            utm = proj_xform.transform( row['Longitude'], row['Latitude'] )

            #  Convert UTM to Pixels
            pix = xform * utm

            if pix[0] < shape[1] and pix[0] >= 0 and pix[1] < shape[0] and pix[1] >= 0:

                start_x = pix[0] - (win_width / 2)
                start_y = pix[1] - (win_height / 2)

                name = row['Name']
            
                #  Compute window
                windows[name] = { 'window': Window( start_x, start_y, win_width, win_height ),
                                  'latitude': row['Latitude'],
                                  'longitude': row['Longitude'] }

        return windows
