import requests
from bs4 import BeautifulSoup
import time
from base64 import b64decode
from zipfile import ZipFile
import io
import os

class Retrieval:
    api_version = ''
    session_id = ''
    instance = ''
    req_url = ''
    
    def __init__(self, api_version, response):
        self.api_version = api_version
        self.session_id = response['access_token']
        self.instance = response['instance_url']
        
        org_id = response['id'].split('/')[-2]
        self.req_url = response['instance_url'] + '/services/Soap/m/'\
                        + api_version + '/' + org_id
    
    def retrieve(self):
        action = 'retrieve'
        env = self._create_envelope({'type' : action})
        headers = {'Content-type': 'text/xml', 'SOAPAction': action}
        
        print('Beginning the process to retrieve metadata files')
        ret_req = requests.post(self.req_url, headers=headers, data=env)
        ret_req.raise_for_status()
        print('Retrieve request successful')
        
        req_env = BeautifulSoup(ret_req.text, "xml")
        process_id = req_env.find('id').text
        
        action = 'checkRetrieveStatus'
        headers['SOAPAction'] = action
        status_env = self._create_envelope({'asyncProcessId' : process_id, 'type' : action})
        
        # turns into 20 minutes; may need to be adjusted for bigger orgs
        max_requests = 15
        num_requests = 1
        sleep_time = 10
        stat_res = None
        
        while True:
            print('Retrieve status check',num_requests)
            stat_res = self._check_retrieve_status(headers, status_env)
            
            if 'true' in stat_res.find('done').text:
                break
            else:
                num_requests += 1
                if num_requests > max_requests:
                    raise Exception("Request timed out. Please try again.")
                
                time.sleep(sleep_time)
                sleep_time += 10
        
        status = stat_res.find('status').text
        if 'Failed' in status:
            raise Exception(stat_res.find('errorStatusCode').text + ': '\
                            + stat_res.find('errorMessage').text)
        elif 'Succeeded' in status:
            details = stat_res.find_all('details')
            if len(details) > 0:
                for msg in details:
                    with open('retrieve_log.txt', 'a') as log:
                        log.write(msg.find('fileName').text + ': ' + msg.find('problem').text + '\n')
                print('Some items came with warnings. Check retrieve_log.txt for details.')
            
            file = b64decode(stat_res.find('zipFile').text)
            z = ZipFile(io.BytesIO(file))
            z.extractall(os.path.join(os.getcwd(),'src'))
            print('Files successfully downloaded')
    
    def _check_retrieve_status(self, headers, env):
        stat_req = requests.post(self.req_url, headers=headers, data=env)
        stat_req.raise_for_status()
        
        stat_env = BeautifulSoup(stat_req.text, "xml")
        stat_res = stat_env.find('result')
        
        return stat_res
    
    def _create_envelope(self, params):
        env = '<?xml version="1.0" encoding="UTF-8"?>'
        env += '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '\
                + 'xmlns:met="http://soap.sforce.com/2006/04/metadata">'
        
        env += '<soapenv:Header>'
        env += '<met:SessionHeader>'
        env += '<met:sessionId>' + self.session_id + '</met:sessionId>'
        env += '</met:SessionHeader>'
        env += '</soapenv:Header>'
        
        env += '<soapenv:Body>'
        if 'Status' in params['type']:
            env += '<met:checkRetrieveStatus>'
            env += '<met:asyncProcessId>' + params['asyncProcessId'] + '</met:asyncProcessId>'
            env += '<met:includeZip>True</met:includeZip>'
            env += '</met:checkRetrieveStatus>'
        elif 'list' in params['type']:
            env += '<met:listMetadata>'
            env += '<met:queries><type>' + params['meta'] + '</type></met:queries>'
            env += '<met:asOfVersion>' + self.api_version + '</met:asOfVersion>'
            env += '</met:listMetadata>'
        else:
            env += '<met:retrieve>'
            env += '<met:retrieveRequest>'
            env += '<met:apiVersion>' + self.api_version + '</met:apiVersion>'
            env += '<met:singlePackage>True</met:singlePackage>'
            env += '<met:unpackaged>' + self._create_package() + '</met:unpackaged>'
            env += '</met:retrieveRequest>'
            env += '</met:retrieve>'
        env += '</soapenv:Body>'
        
        env += '</soapenv:Envelope>'
        return env
    
    def _create_package(self):
        pkg = ''
        
        # the * wildcard doesn't work for standard objects or managed object workflows
        pkg += self._compile_meta_xml('CustomObject')
        pkg += self._compile_meta_xml('Workflow')
        
        # managed layouts are a special case and so need additional processing
        pkg += '<types><members>*</members>'
        layout_names = self._get_layouts()
        for name in layout_names:
            pkg += '<members>' + name + '</members>'
        pkg += '<name>Layout</name></types>'
        
        # including everything in one package to reduce API calls, which is fine
        # for smaller orgs. This probably needs to be split up for bigger orgs
        # due to the 10k file limit for each retrieve call
        metadata_types = ['Workflow','ApexClass','ApexTrigger','ApexPage',
                          'ApprovalProcess','EmailTemplate','ApexComponent',
                          'AutoResponseRules','DuplicateRule','AssignmentRules',
                          'MatchingRule','SharingRules','Flow','QuickAction',
                          'AuraDefinitionBundle','EscalationRules',
                          'Profile','PermissionSet']
        
        for mt in metadata_types:
            pkg += '<types>'
            pkg += '<members>*</members>'
            pkg += '<name>' + mt + '</name>'
            pkg += '</types>'
            
        pkg += '<version>' + self.api_version + '</version>'
        return pkg
    
    def _compile_meta_xml(self, meta):
        pkg = '<types>'
        objects = self._get_meta_names(meta)
        for obj in objects:
            pkg += '<members>' + obj + '</members>'
        pkg += '<name>' + meta + '</name></types>'
        return pkg
    
    def _get_meta_names(self, meta):
        action = 'listMetadata'
        params = {'type' : action,
                  'meta' : meta}
        env = self._create_envelope(params)
        headers = {'Content-type': 'text/xml', 'SOAPAction': action}
        
        list_req = requests.post(self.req_url, headers=headers, data=env)
        list_req.raise_for_status()
        
        list_env = BeautifulSoup(list_req.text, "xml")
        list_results = list_env.find_all('result')
        
        meta_names = []
        for res in list_results:
            name = res.find('fullName').text
            meta_names.append(name)
        
        return meta_names
    
    def _get_layouts(self):
        request_url = self.instance + '/services/data/v{}/tooling/query?q='.format(self.api_version)
        headers = {'Authorization' : 'OAuth ' + self.session_id}
        
        layout_query = 'SELECT TableEnumOrId, Name, NamespacePrefix FROM Layout WHERE NamespacePrefix != null'
        r = requests.get(request_url + layout_query, headers=headers)
        r.raise_for_status()
        layouts = r.json()['records']
        
        obj_query = 'SELECT DurableId, QualifiedApiName FROM EntityDefinition WHERE IsCustomizable = true'
        r = requests.get(request_url + obj_query, headers=headers)
        r.raise_for_status()
        
        obj_dict = {}
        for obj in r.json()['records']:
            obj_dict[obj['DurableId']] = obj['QualifiedApiName']
        
        names = []
        for lay in layouts:
            obj_id = lay['TableEnumOrId'][:-3]
            obj_name = ''
            # this is the ID prefix for objects
            if '01I' in obj_id and obj_id in obj_dict.keys():
                obj_name = obj_dict[obj_id]
            else:
                obj_name = lay['TableEnumOrId']
                
            name = obj_name + '-' + lay['NamespacePrefix'] + '__' + lay['Name']
            names.append(name)
                
        return names