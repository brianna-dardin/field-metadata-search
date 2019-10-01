from retrieval import Retrieval
from objectclass import Object
import requests
import os

def main():
    CLIENT_ID = input('What is the client ID? ')
    CLIENT_SECRET = input('What is the client secret? ')
    USERNAME = input('What is your username? ')
    PASSWORD = input('What is your password? ')
    SECURITY_TOKEN = input('What is your security token? ')
    
    sandbox = ''
    while True:
        sandbox = input('Are you logging into a sandbox? Type yes or no only. ')
        sandbox = sandbox.lower()
        if 'yes' in sandbox or 'no' in sandbox:
            break
        else:
            print('Invalid input. Please answer yes or no only.')
    
    auth_url = 'https://{}.salesforce.com/services/oauth2/token'
    if 'y' in sandbox:
        auth_url = auth_url.format('test')
    else:
        auth_url = auth_url.format('login')
    
    params = {'grant_type' : 'password',
              'client_id' : CLIENT_ID,
              'client_secret' : CLIENT_SECRET,
              'username' : USERNAME,
              'password' : PASSWORD + SECURITY_TOKEN}
    
    r = requests.post(auth_url, data = params)
    r.raise_for_status()
    print('Login successful')
    
    data = r.json()
    token = data['access_token']
    instance = data['instance_url']
    
    api_version = ''
    while True:
        api_version = input('What API version do you want to use? ')
        try:
            #converts string into float in case it's not entered as an integer
            #then converts to integer since API versions aren't numbered "46.1" etc
            api_version = int(float(api_version))
            #converts to float again so that the string is in the format of "46.0"
            api_version = str(float(api_version))
            break
        except:
            print('Invalid input. Please enter a numeric API version.')
        
    if os.path.isdir(os.path.join(os.getcwd(),'src')):
        while True:
            re_retrieve = input('Would you like to retrieve the metadata again? Type yes or no only. ')
            re_retrieve = re_retrieve.lower()
            if 'yes' in re_retrieve or 'no' in re_retrieve:
                break
            else:
                print('Invalid input. Please answer yes or no only.')
                
        if 'y' in re_retrieve:
            soap = Retrieval(api_version,data)
            soap.retrieve()
    else:
        soap = Retrieval(api_version,data)
        soap.retrieve()
        
    obj = None
    while True:
        obj_name = input('What is the API name of the sObject you would like to analyze? ')
        obj = Object(obj_name)
        obj.get_fields(token, instance, api_version)
        
        if len(obj.fields) > 0:
            break
        else:
            print('No fields found. Please double check the API name and try again.')
    
    search_perm = ''
    while True:
        search_perm = input('Analyzing permission sets and profiles takes much longer than other metadata.'\
                            +' Do you still want to analyze them? Type yes or no only. ')
        if 'yes' in search_perm or 'no' in search_perm:
            break
        else:
            print('Invalid input. Please answer yes or no only.')
            
    perm = False
    if 'y' in search_perm:
        perm = True
    
    obj.search_fields(perm)
    
if __name__ == '__main__':
    main()