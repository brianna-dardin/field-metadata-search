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
        
    if not os.path.isdir(os.path.join(os.getcwd(),'src')):
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
            
    obj.search_fields()
    
if __name__ == '__main__':
    main()