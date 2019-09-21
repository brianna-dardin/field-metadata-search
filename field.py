import os
import pandas as pd

class Field:
    api_name = ''
    sobject_name = ''
    
    def __init__(self, api_name, sobject_name):
        self.api_name = api_name
        self.sobject_name = sobject_name
        
    def add_metadata(self, meta_dict, file_name):
        for key in meta_dict.keys():
            key_list = list(set(meta_dict[key]))
            rows = []
            for meta in key_list:
                meta_row = [self.api_name, key, meta, file_name]
                rows.append(meta_row)
                    
        meta_path = os.path.join(os.getcwd(),self.sobject_name+' metadata.csv')
        meta_df = pd.read_csv(meta_path,sep=',')
        
        new_df = pd.DataFrame(rows, columns=['Field Name','Data Type','Metadata Name','File Name'])
        meta_df = pd.concat([meta_df,new_df], join='inner', ignore_index=True)
        
        meta_df.to_csv(meta_path, index=False)