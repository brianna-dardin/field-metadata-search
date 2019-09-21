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
    req_url = ''
    
    def __init__(self, api_version, response):
        self.api_version = api_version
        self.session_id = response['access_token']
        
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
        
        # turns into just under 10 minutes; should be adjusted for bigger orgs
        max_requests = 10
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
            env += '<met:queries><type>CustomObject</type></met:queries>'
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
        pkg = '<types>'
        
        # the * operator doesn't work for standard objects, so query all object names
        objects = self._get_object_names()
        for obj in objects:
            pkg += '<members>' + obj + '</members>'
            
        pkg += '<name>CustomObject</name></types>'
        
        # including everything in one package to reduce API calls, which is fine
        # for smaller orgs. This probably needs to be split up for bigger orgs
        # due to the 10k file limit for each retrieve call
        metadata_types = ['Workflow','ApexClass','ApexTrigger','ApexPage',
                          'ApprovalProcess','EmailTemplate','ApexComponent',
                          'AutoResponseRules','DuplicateRule','AssignmentRules',
                          'Layout','MatchingRule','SharingRules','Flow',
                          'AuraDefinitionBundle','EscalationRules']
        
        for mt in metadata_types:
            pkg += '<types>'
            pkg += '<members>*</members>'
            pkg += '<name>' + mt + '</name>'
            pkg += '</types>'
            
        pkg += '<version>' + self.api_version + '</version>'
        return pkg
    
    def _get_object_names(self):
        action = 'listMetadata'
        env = self._create_envelope({'type' : action})
        headers = {'Content-type': 'text/xml', 'SOAPAction': action}
        
        list_req = requests.post(self.req_url, headers=headers, data=env)
        list_req.raise_for_status()
        
        list_env = BeautifulSoup(list_req.text, "xml")
        list_results = list_env.find_all('result')
        
        obj_names = []
        for res in list_results:
            name = res.find('fullName').text
            obj_names.append(name)
        
        return obj_names