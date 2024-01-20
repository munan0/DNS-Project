
# Requests is an HTTP library, written in Python, for human beings. Basic GET usage:
# The csv module implements classes to read and write tabular data in CSV format.
import requests, csv

# Supplies the datetime module exports the following constants:
#       .MINYEAR  .MAXYEAR  .UTC
from datetime import date

# Attaches HTTP Basic Authentication to the given Request object.
from requests.auth import HTTPBasicAuth

# DISABLE WARNINGS FOR SSL VERIFICATION
requests.packages.urllib3.disable_warnings()

# api_base_url inputs the necessary api url needed for the task
api_base_url = 'https://yoururl.com'

# heasders - if no token call is made, the
headers = {}

# function for login credentials
# setup however you need them
def get_login() -> list:
    print('Please enter your username:')
    username=str(input())
    print('Please enter your password:')
    password=str(input())   
    return [username, password]

# function for get request to api: provides login string and parameter dictionary
# The .Response <Response> object, which contains a server's response to an HTTP request.
# Pay attention to the available parameters
def cisco_request_get(type:str, login : list, params:dict={}) -> requests.Response:
    return requests.get(
        f'{api_base_url}{type}',
        params=params,
        headers=headers,
        verify=False
    )

# function for post request to api for tokens
# The .Response <Response> object, which contains a server's response to an HTTP request.
# Token for login might be different for your location, change as needed
def cisco_request_post(type:str, login : list, params:dict={}) -> requests.Response:
    return requests.post(
        f'https://yoursite/tokensfor authorization',
        params=params,
        auth = HTTPBasicAuth(login[0],login[1]),
        verify=False
    )

# function for creating a dictionary from the devices that are being searched
# the meat of the request. your dictionaries and how they are setup in the metadata
# will make the difference as to what you recieve
def get_devices(login : list) -> dict:
    devices : dict = {}
    devices_params : dict = {'expanded' : 'true', 'limit' : '100'}
    devices_request : requests.Response = cisco_request_get(
        type="", 
        login=login, 
        params=devices_params)
    if devices_request.ok:
        devices_json = devices_request.json()
        for device in devices_json['items']:
            #print(f"Grabbing device <{device['id']}>")
            
            ip = device['hostName']
            name = device['name']
            type = device['model']
            devices[device['id']] = {'name' : name, 'ip' : ip, 'type' : type}
    return devices

# function for creating a dictionary from the interfaces that are on the devices searched
def getInterfaces(login : list, devices:dict) -> dict:
    for k,v in devices.items():
        devices_params : dict = {'expanded' : 'true', 'limit' : '100'}
        devices_request : requests.Response = cisco_request_get(
            type=f"/{k}/physicalinterfaces", 
            login=login, 
            params=devices_params)
        if devices_request.ok:
            theJson = devices_request.json()
            i = []
            for inter in theJson['items']:
                if 'ipv4' in inter:
                    if 'address' in inter['ipv4']['static']:
                        i.append(
                            {
                                'interface': inter['name'],
                                'logicalName': inter['ifname'],
                                'ipv4': inter['ipv4']['static']['address'],
                                'netmask':cidr_to_subnet(inter['ipv4']['static']['netmask'])
                            }
                        )
            devices[k]['interfaces']=i 
    return devices

# function for creating a dictionary from the subinterfaces that are on the interfaces searched
def getSubInterfaces(login : list, devices:dict) -> dict:
    for k,v in devices.items():
        devices_params : dict = {'expanded' : 'true', 'limit' : '100'}
        devices_request : requests.Response = cisco_request_get(
            type=f"/{k}/subinterfaces", 
            login=login, 
            params=devices_params)
        if devices_request.ok:
            theJson = devices_request.json()
            i: list = devices[k]['interfaces']
            if 'items' in theJson:
                for inter in theJson['items']:
                    if 'ipv4' in inter:
                        if 'address' in inter['ipv4']['static']:
                            i.append(
                                {
                                    'interface': f"{inter['name']}.{inter['vlanId']}",
                                    'logicalName': inter['ifname'],
                                    'ipv4': inter['ipv4']['static']['address'],
                                    'netmask':cidr_to_subnet(inter['ipv4']['static']['netmask'])
                                }
                            )
                devices[k]['interfaces']=i 
    return devices

# function to convert CIDR notation to subnet mask if cidr is provided only
def cidr_to_subnet(subnet):
    if len(subnet) > 2:
        return subnet
    subnet_mask = '255.255.255.255'
    prefix_length = int(subnet)
    if prefix_length >= 0 and prefix_length <= 32:
        subnet_mask_parts = [0,0,0,0]
        subnet_mask_binary = ''
        for i in range(prefix_length):
            subnet_mask_parts[i//8] += 1 << (7 - i % 8)
        subnet_mask =  '.'.join(str(part) for part in subnet_mask_parts)
    return subnet_mask
 
# head_row_csv for header of the csv being created
# this is how your csv will be headed. the function below this will
# have to match in order for the information to line up correctly.
head_row_csv:list = ['DEVICE NAME','DEVICE TYPE','DEVICE IPV4','INTERFACE','LOGICAL NAME','INTERFACE IPV4','NETMASK']

# function to generate the csv report from the data compiled
def generate_report(headers:list, devices:dict):
    # This will give you the date of the report along with the 
    # name of the report.
    filename = f"{date.today()}_NameOfReport.csv"
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for devId, devInfo in devices.items():
            try:
                for inter in devInfo['interfaces']:
                    row : list = []
                    row.append(devInfo['name'])
                    row.append(devInfo['type'])
                    row.append(devInfo['ip'])
                    row.append(inter['interface'])
                    row.append(inter['logicalName'])
                    row.append(inter['ipv4'])
                    row.append(inter['netmask'])
                    writer.writerow(row)
            except:
                continue

# function calls
login = get_login()
tokens : requests.Response = cisco_request_post(
    type = '', login=login
)
# token parameters might be different for your sight.
headers['token-authorization-parameter']=tokens.headers['token-authorization-parameter']
# refresh parameters might or might not be required. 
headers['token-authorization-refresh-parameter']=tokens.headers['token-authorization-refresh-parameter']
devices = get_devices(login)
devices = getInterfaces(login, devices)
devices = getSubInterfaces(login, devices)
print(devices)
generate_report(head_row_csv, devices)