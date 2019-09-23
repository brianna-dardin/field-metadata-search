import requests
import os
from field import Field
import mmap
from bs4 import BeautifulSoup
from search import Search
import pandas as pd

class Object:
    sobject_name = ''
    standard = True
    fields = []
    
    def __init__(self, sobject_name):
        if '__c' in sobject_name or '__x' in sobject_name or '__mdt' in sobject_name:
            self.standard = False
        
        self.sobject_name = sobject_name
    
    def get_fields(self, token, instance, api_version):
        self.fields.clear()
        
        request_url = instance + '/services/data/v{}/tooling/query?q='.format(api_version)
        headers = {'Authorization' : 'OAuth ' + token}
        
        if self.standard:
            where_obj = self.sobject_name
        else:
            no_suffix = self.sobject_name.replace('__c','').replace('__x','').replace('__mdt','')
            
            object_query = "SELECT Id FROM CustomObject WHERE DeveloperName = '{}'".format(no_suffix)
            r = requests.get(request_url + object_query, headers=headers)
            r.raise_for_status()
            
            where_obj = r.json()['records'][0]['Id']
        
        field_query = "SELECT NamespacePrefix,DeveloperName,CreatedDate,LastModifiedDate "\
                    + "FROM CustomField WHERE TableEnumOrId='{}'".format(where_obj)
        r = requests.get(request_url + field_query, headers=headers)
        r.raise_for_status()
        
        rows = []
        for fld in r.json()['records']:
            if fld['NamespacePrefix']:
                field_name = fld['NamespacePrefix'] + '__' + fld['DeveloperName']
            else:
                field_name = fld['DeveloperName']
            
            api_name = field_name + '__c'
            
            field = Field(api_name, self.sobject_name)
            self.fields.append(field)
            
            created = fld['CreatedDate'].split('T')[0].replace('-','/')
            modified = fld['LastModifiedDate'].split('T')[0].replace('-','/')
            
            field_row = [api_name, created, modified]
            rows.append(field_row)
        
        field_path = os.path.join(os.getcwd(),self.sobject_name+' fields.csv')
        field_df = pd.DataFrame(rows,columns=['API Name','CreatedDate','LastModifiedDate'])
        field_df.to_csv(field_path,index=False)
        
    def search_fields(self):
        saved_objs = {'workflows' : {},
                      'approvalProcesses' : {},
                      'flows' : {},
                      'assignmentRules' : {},
                      'escalationRules' : {}}
        
        no_check_field = ['aura','classes','components','pages','triggers','layouts']
        no_search_obj = ['duplicateRules','email','approvalProcesses']
        search_obj_list = ['assignmentRules','autoResponseRules',
                           'escalationRules','matchingRules','objects',
                           'sharingRules','flows','workflows']
        
        meta_file = self.sobject_name+' metadata.csv'
        meta_path = os.path.join(os.getcwd(),meta_file)
        meta_df = pd.DataFrame(columns=['Field Name','Data Type','Metadata Name','File Name'])
        meta_df.to_csv(meta_path,index=False)
        
        for (dirpath, dirs, files) in os.walk(os.path.join(os.getcwd(),'src')):
            data_type = os.path.basename(dirpath)
            if data_type in no_search_obj or data_type in search_obj_list\
                    or data_type in no_check_field or 'email' in dirpath:
                for filename in files:
                    if '-meta.xml' in filename or '.png' in filename or '.jpg' in filename:
                        continue
                    print(data_type,filename)
                    
                    if filename.find('layout') == -1 or filename.find(self.sobject_name) != -1:     
                        with open(os.path.join(dirpath,filename), 'rb', 0) as file, \
                                mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
                            obj = BeautifulSoup(file.read(),'xml')
                            obj_text = obj.text
                            if data_type in saved_objs.keys():
                                saved_objs[data_type][filename] = obj
                                
                            for fld in self.fields:
                                byte_name = fld.api_name.encode('utf-8')
                                if s.find(byte_name) != -1:
                                    print(fld.api_name,'found in',filename)
                                    no_ext_file = filename[:filename.rfind('.')]
                                    
                                    if data_type in no_check_field:
                                        fld.add_metadata({data_type:[no_ext_file]},filename)
                                    elif fld.check_field(obj_text,filename):
                                        if data_type in no_search_obj:
                                            fld.add_metadata({data_type:[no_ext_file]},filename)
                                        elif 'email' in dirpath:
                                            fld.add_metadata({'email':[no_ext_file]},filename)
                                        else:
                                            search_obj = Search(obj,fld,filename)
                                            if 'flow' in data_type:
                                                if 'work' in data_type:
                                                    search_obj.search()
                                                else:
                                                    search_obj.search_flow()
                                            else:
                                                search_obj.search()
        
        self._search_actions(meta_path,saved_objs,True)
        self._search_actions(meta_path,saved_objs,False)
        
        meta_df = pd.read_csv(meta_path)
        meta_df.drop_duplicates(inplace=True)
        meta_df.to_csv(meta_path,index=False)
        print(meta_file,'created. Open file to see all the fields and the metadata they occur in.')
       
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