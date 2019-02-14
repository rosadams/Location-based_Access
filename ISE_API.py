import requests
import xmltodict
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# suppress security warning messages due to having verify=false in requests
requests.packages.urllib3.disable_warnings()


def requests_retry_session(
    # Retry for REST requests that return error codes.   Needed to address lag in ISE session database after Issuing a CoA.
    # Code borrowed from https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    retries=5,
    backoff_factor=10,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def ise_get_usergroups(server):
    # returns a sorted list of all usergroups configured in ISE
    call = "/ers/config/identitygroup"
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    grouplist = []
    for n in (response.json().get("SearchResult").get("resources")):
        grouplist.append(n.get("name"))
    return (sorted(grouplist))


def ise_get_device_usergroup(server, mac_address):
    # returns a a list of the user groups associated with a device session.
    call = "/admin/API/mnt/Session/MACAddress/" + mac_address.upper()
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    #response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    t0 = time.time()
    try:
        response = requests_retry_session().get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
        print(response)
    except Exception as x:
        print('It failed :(', x.__class__.__name__)
    else:
        print('It eventually worked', response.status_code)
    finally:
        t1 = time.time()
        print('Took', t1 - t0, 'seconds')

    print(response)
    if str(response) == "<Response [200]>":
        data = xmltodict.parse(response.text)
        att_list = data["sessionParameters"]['other_attr_string'].split(":!:")
        print(att_list)
        return [n.split(":")[-1] for n in att_list if "Name=User Identity Groups:" in n]
    elif str(response) == "<Response [500]>":
        return []


def ise_get_usergroupid(server, groupname):
    #returns the groupID for a given group name

    call = "/ers/config/endpointgroup?filter=name.EQ." + groupname
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    return response.json().get("SearchResult").get("resources")[0].get("id")


def ise_get_endpoint_info(server, mac_address):
    """returns a dictionary containing the mac, staticGroupAssignment, and groupId of the endpoint, given mac address/name
       (str) of that device.
    """
    call = "/ers/config/endpoint/name/" + mac_address.upper()
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    endpoint_info = {"mac_address": response.json().get("ERSEndPoint").get("mac").lower(),
                     "id": response.json().get("ERSEndPoint").get("id"),
                     "staticGroupAssignment": response.json().get("ERSEndPoint").get("staticGroupAssignment"),
                     "groupId": response.json().get("ERSEndPoint").get("groupId"),
                     }
    return endpoint_info

"""
def ise_get_device_usergroup(server, mac_address):
    # returns a a list of the user groups associated with a device session.
    call = "/admin/API/mnt/Session/MACAddress/" + mac_address.upper()
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    print(response)
    if str(response) == "<Response [200]>":
        data = xmltodict.parse(response.text)
        att_list = data["sessionParameters"]['other_attr_string'].split(":!:")
        print(att_list)
        return [n.split(":")[-1] for n in att_list if "Name=User Identity Groups:" in n]
    else:
        return []
"""

def ise_get_device_user_info(server, mac_address):
    # returns a dictionary with username and the user groups associated with a device session.
    call = "/admin/API/mnt/Session/MACAddress/" + mac_address.upper()
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    if str(response) == "<Response [200]>":
        dev_usr_info = {}
        data = xmltodict.parse(response.text)
        dev_usr_info["user_name"] = data["sessionParameters"]["user_name"]
        att_list = data["sessionParameters"]['other_attr_string'].split(":!:")
        dev_usr_info["user_groups"] = [n.split(":")[-1] for n in att_list if "Name=User Identity Groups:" in n]
        return(dev_usr_info)

    else:
        return {"user_name": "not in ISE", "user_groups":[]}


def ise_blacklist_mac(server, mac_address):
    """ blacklists mac_address
    """
    endpoint_id = ise_get_endpoint_info(server, mac_address).get("id")
    blacklist = ise_get_usergroupid(server, "loc_blacklist")

    call = "/ers/config/endpoint/" + endpoint_id
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = """
        {
            "ERSEndPoint": {
                "groupId": \"""" + blacklist + """\",
                "staticGroupAssignment": "true",
                "link": {
                }
            }
        }
    """
    return requests.put(uri, auth=(server["user"], server["pass"]), headers=headers, data=body, verify=False)


def ise_unblacklist_mac(server, mac_info):
    """ unblacklists mac_address and resets staticGroupAssignment and groupId to their original values
        (stored in mac_info dictionary).
    """
    call = "/ers/config/endpoint/" + mac_info.get("id").upper()
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    body = """
            {
                "ERSEndPoint": {
                    "groupId": \"""" + mac_info.get("groupId") + """\",
                    "staticGroupAssignment": """ + str(mac_info.get("staticGroupAssignment")).lower() + """,
                    "link": {
                    }
                }
            }
        """
    return requests.put(uri, auth=(server["user"], server["pass"]), headers=headers, data=body, verify=False)


def ise_CoA(server, mac_address):
    # Issues a CoA for the given mac_address
    #call = "/admin/API/mnt/CoA/Reauth/" + server.get("server_name") + "/" + mac_address.upper() + "/1"
    call = "/admin/API/mnt/CoA/Disconnect/" + server.get("server_name") + "/" + mac_address.upper() + "/1"
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    print(response.text)
    return response
