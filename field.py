import re
import os
import pandas as pd

class Field:
    api_name = ''
    sobject_name = ''
    _pattern = None
    
    def __init__(self, api_name, sobject_name):
        self.api_name = api_name
        self.sobject_name = sobject_name
        self._pattern = re.compile(r'[^a-zA-Z_]')
        
    def check_field(self, meta, file_name):
        meta_text = meta.text
        if self.api_name.lower() in meta_text.lower():
            if '.quick' in file_name:
                rel_obj = self.sobject_name
            else:
                rel_obj = self.sobject_name.replace('__c','__r')
            
            relationships = self.check_relationship(meta_text)
            if len(relationships) > 0:
                present = []
                for rel in relationships:
                    if self.sobject_name in file_name or rel_obj in rel:
                        present.append(1)
                    else:
                        if rel_obj in rel:
                            present.append(1)
                        else:
                            present.append(0)
                return sum(present) > 0
            else:
                return self.sobject_name in file_name
        else:
            return False
    
    def check_relationship(self,meta_text):
        relationships = []
        indices = re.finditer(self.api_name,meta_text)
        for i in indices:
            if i.start():
                trun_text = meta_text[:i.start()]
                if '.' in trun_text[-1]:
                    trun_text = trun_text[:-1]
                    pattern_found = self._pattern.findall(trun_text)
                    if len(pattern_found) > 0:
                        char = pattern_found[::-1][0]
                        reverse_idx = trun_text[::-1].find(char)
                        char_idx = len(trun_text)-reverse_idx
                        rel = trun_text[char_idx:]
                        relationships.append(rel)
                    else:
                        relationships.append(trun_text)
        return relationships
        
    def add_metadata(self, meta_dict, file_name):
        for key in meta_dict.keys():
            key_list = list(set(meta_dict[key]))
            rows = []
            for meta in key_list:
                print(self.api_name, 'found in', key, meta)
                meta_row = [self.api_name, key, meta, file_name]
                rows.append(meta_row)
                
        meta_path = os.path.join(os.getcwd(),self.sobject_name+' metadata.csv')
        meta_df = pd.read_csv(meta_path,sep=',')
        
        new_df = pd.DataFrame(rows, columns=['Field Name','Data Type','Metadata Name','File Name'])
        meta_df = pd.concat([meta_df,new_df], join='inner', ignore_index=True)
        
        meta_df.to_csv(meta_path, index=False)