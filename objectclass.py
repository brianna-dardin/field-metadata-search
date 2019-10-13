import requests
import os
from field import Field
import mmap
from bs4 import BeautifulSoup
from search import Search
import pandas as pd

class Object:
    sobject_name = ''
    fields = []
    
    def __init__(self, sobject_name):
        self.sobject_name = sobject_name
    
    def get_fields(self, token, instance, api_version):       
        self.fields.clear()
        
        request_url = instance + '/services/data/v{}/tooling/query?q='.format(api_version)
        headers = {'Authorization' : 'OAuth ' + token}
        
        field_query = "SELECT QualifiedApiName FROM FieldDefinition "\
            + "WHERE EntityDefinition.QualifiedApiName = '{}'".format(self.sobject_name)
        r = requests.get(request_url + field_query, headers=headers)
        r.raise_for_status()
        
        for fld in r.json()['records']:
            if '__c' in fld['QualifiedApiName']:
                field = Field(fld['QualifiedApiName'], self.sobject_name)
                self.fields.append(field)
        
    def search_fields(self, perm = False):
        saved_objs = {'workflows' : {},
                      'approvalProcesses' : {},
                      'flows' : {},
                      'assignmentRules' : {},
                      'escalationRules' : {}}
        
        permissions = ['profiles','permissionsets']
        no_check_field = ['classes','components','pages','triggers','layouts']
        no_search_obj = ['duplicateRules','email','approvalProcesses']
        search_obj_list = ['assignmentRules','autoResponseRules','quickActions',
                           'escalationRules','matchingRules','objects',
                           'sharingRules','flows','workflows']
        
        meta_file = self.sobject_name+' metadata.csv'
        meta_path = os.path.join(os.getcwd(),meta_file)
        meta_df = pd.DataFrame(columns=['Field Name','Data Type','Metadata Name','File Name'])
        meta_df.to_csv(meta_path,index=False)
        
        for (dirpath, dirs, files) in os.walk(os.path.join(os.getcwd(),'src')):
            data_type = os.path.basename(dirpath)
            if data_type in no_search_obj or data_type in search_obj_list\
                    or data_type in no_check_field or 'email' in dirpath\
                    or 'aura' in dirpath or data_type in permissions:
                for filename in files:
                    if '-meta.xml' in filename or '.png' in filename or '.jpg' in filename:
                        continue
                    if not perm and data_type in permissions:
                        continue
                    
                    if os.stat(os.path.join(dirpath,filename)).st_size > 0:
                        if filename.find('layout') == -1 or filename.find(self.sobject_name) != -1:     
                            print(data_type,filename)
                            with open(os.path.join(dirpath,filename), 'rb', 0) as file, \
                                    mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
                                obj = BeautifulSoup(file.read(), 'xml')
                                if data_type in saved_objs.keys():
                                    saved_objs[data_type][filename] = obj
                                
                                readables = []
                                if perm and data_type in permissions:
                                    readables = obj.find_all('readable', text='true')
                                    
                                for fld in self.fields:
                                    byte_name = fld.api_name.encode('utf-8')
                                    if s.find(byte_name) != -1:
                                        no_ext_file = filename[:filename.rfind('.')]
                                        
                                        if len(readables) > 0:
                                            for read in readables:
                                                if fld.check_field(read.parent,filename):
                                                    fld.add_metadata({data_type:[no_ext_file]},filename)
                                                    break
                                        elif data_type in no_check_field:
                                            fld.add_metadata({data_type:[no_ext_file]},filename)
                                        elif 'aura' in dirpath:
                                            fld.add_metadata({'aura':[no_ext_file]},filename)
                                        elif data_type in no_search_obj:
                                            if fld.check_field(obj,filename):
                                                fld.add_metadata({data_type:[no_ext_file]},filename)
                                        elif 'email' in dirpath:
                                            if fld.check_field(obj,filename):
                                                fld.add_metadata({'email':[no_ext_file]},filename)
                                        else:
                                            search_obj = Search(obj,fld,filename)
                                            search_obj.search()
        
        self._search_actions(meta_path,saved_objs,True)
        self._search_actions(meta_path,saved_objs,False)
        
        meta_df = pd.read_csv(meta_path)
        meta_df.drop_duplicates(inplace=True)
        meta_df.to_csv(meta_path,index=False)
        print(meta_file,'created. Open file to see all the metadata the fields appear in.')

        df_dict = {}
        types = sorted(list(meta_df['Data Type'].unique()))
        for fld in self.fields:
            df_dict[fld.api_name] = {}
            for t in types:
               df_dict[fld.api_name][t] = 0
               
        for i, row in meta_df.iterrows():
            if '__c' in row['Field Name']:
                df_dict[row['Field Name']][row['Data Type']] += 1
        
        rows = []
        for fld in df_dict.keys():
            row = [fld]
            for key in df_dict[fld].keys():
                row.append(df_dict[fld][key])
            rows.append(row)
            
        for row in rows:
            total = sum(row[1:])
            row.append(total)
                
        columns = ['Field Name']
        columns.extend(types)
        columns.append('Total')
        field_df = pd.DataFrame(rows, columns=columns)
        
        field_file = self.sobject_name+' fields.csv'
        field_path = os.path.join(os.getcwd(),field_file)
        field_df.to_csv(field_path,index=False)
        print(field_file,'created. Open file to see all the fields '\
              + 'and a summary of how many metadata types they appear in.')
       
    def _search_actions(self,meta_path,saved_objs,email):
        meta_df = pd.read_csv(meta_path,sep=',')
        
        data_types = None
        if email:
            data_types = ['email']
        else:
            data_types = ['fieldUpdates','alerts','classes']
        
        for fld in self.fields:
            fld_df = meta_df.loc[(meta_df['Field Name'] == fld.api_name)\
                                 & (meta_df['Data Type'].isin(data_types))]
            
            if len(fld_df) > 0:
                for data_type in saved_objs:
                    for file in saved_objs[data_type].keys():
                        search_obj = Search(saved_objs[data_type][file],fld,file)
                        if email:
                            search_obj.find_templates(list(fld_df['Metadata Name']))
                        else:
                            search_obj.find_actions(list(fld_df['Metadata Name']))