
import sqlite3
import pandas as pd

def init_db( pathname ):
    try:
   
        # Connect to DB and create a cursor
        conn = sqlite3.connect( pathname )
        cursor = conn.cursor()
        print('DB Init')
 
        # Write a query and execute it with cursor
        query = 'select sqlite_version();'
        cursor.execute(query)
 
        # Fetch and output result
        result = cursor.fetchall()
        print('SQLite Version is {}'.format(result))
        
        # Close the cursor
        cursor.close()
        
        return conn
 
    # Handle errors
    except sqlite3.Error as error:
        print('Error occurred - ', error)

def load_table( conn, table_name ):

    try:
        sql_query = pd.read_sql_query(f'SELECT * FROM {table_name}', conn )
    
        df = pd.DataFrame( sql_query )

        return df
    except Exception as e:
        return None

def resolve_entries( existing_table, new_columns ):

    new_data = { 'cid': [] }
    for cid in existing_table['cid'].values():
        print( f'CID: {cid}' )
    
    if existing_table is None:
        existing_table = new_entries

    else:
        for rdata in new_entries.itertuples():

            row = rdata._asdict()
            c = existing_table.loc[existing_table['cid'] == row['cid']]
            if c.shape[0] == 0:
                pass
            elif c.shape[0] > 1:
                raise Exception( f'Multiple CIDs found: {c["cid"].values}' )
            else:
                for c in row:
                    if 'file_' in c:
                        src_val = row[c]
                        dst_val = existing_table.loc[existing_table['cid'] == row['cid'],c].values[0]

                        #  if neither is valid, then do nothing
                        if dst_val is None and src_val is None:
                            pass
                        
                        #  if destination is empty, but source is valid, set it
                        elif dst_val is None and src_val != None:
                            existing_table.loc[existing_table['cid'] == row['cid'],c] = src_val

                        #  If destination is set, and source is empty, do nothing
                        elif dst_val != None and src_val is None:
                            pass

                        elif src_val != dst_val:
                            print( f'Likely need to update CID: {row["cid"]}, Column: {c}, Dest: {dst_val}, Source: {src_val}' )
    return existing_table
                        
    
def close_db( conn ):

    try:
        pass
        
    # Handle errors
    except sqlite3.Error as error:
        print('Error occurred - ', error)
        
    # Close DB Connection irrespective of success
    # or failure
    finally:
   
        if conn:
            conn.close()
            print('SQLite Connection closed')
            