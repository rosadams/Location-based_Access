import requests
import json
import xmltodict
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json

# suppress security warning messages due to having verify=false in requests
requests.packages.urllib3.disable_warnings()


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
    except Exception as x:
        print('It failed :(', x.__class__.__name__)
    #else:
    #    print('It eventually worked', response.status_code)
    finally:
        t1 = time.time()
        #print('Took', t1 - t0, 'seconds')

    if str(response) == "<Response [200]>":
        data = xmltodict.parse(response.text)
        att_list = data["sessionParameters"]['other_attr_string'].split(":!:")
        return [n.split(":")[-1] for n in att_list if "Name=User Identity Groups:" in n]
    elif str(response) == "<Response [500]>":
        return []


def ise_get_userinfo(server, user_name):
    #returns a dictionary with information for a given username. Schema:
    # {
    #     "user_name": "",
    #     "id": "",
    #     "usergroup_ids": [],
    #     "usergroup_names": []
    # }

    #get user_id
    call = "/ers/config/internaluser?filter=name.eq." + user_name
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    user_id = response.json().get("SearchResult").get("resources")[0].get("id")
    # Get usergroup_ids
    uri = response.json().get("SearchResult").get("resources")[0].get("link").get("href")
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    usergroup_ids = response.json().get("InternalUser").get("identityGroups").split(",")
    #Get usergroup_names
    usergroup_names = []
    for n in usergroup_ids:
        call = "/ers/config/identitygroup/" + n
        uri = ("https://" + server["host"] + ":" + server["port"] + call)
        response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
        usergroup_names.append(response.json().get("IdentityGroup").get("name"))
    user_info = {"user_name": user_name, "id": user_id, "usergroup_ids": usergroup_ids, "usergroup_names": usergroup_names}
    return user_info


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
    call = "/ers/config/endpoint/name/" + mac_address
    uri = ("https://" + server["host"] + ":" + server["port"] + call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    endpoint_info = {"mac_address": response.json().get("ERSEndPoint").get("mac").lower(),
                     "id": response.json().get("ERSEndPoint").get("id"),
                     "staticGroupAssignment": response.json().get("ERSEndPoint").get("staticGroupAssignment"),
                     "groupId": response.json().get("ERSEndPoint").get("groupId"),
                     }
    return endpoint_info


def ise_get_device_usergroup(server, mac_address):
    # returns a a list of the user groups associated with a device session.
    call = "/admin/API/mnt/Session/MACAddress/" + mac_address
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    if str(response) == "<Response [200]>":
        data = xmltodict.parse(response.text)
        #print(data["sessionParameters"]["Name"])

        #print(data["sessionParameters"])
        #print(data["sessionParameters"]["passed"])
        #print(data["sessionParameters"]["failed"])
        att_list = data["sessionParameters"]['other_attr_string'].split(":!:")
        for n in att_list:
            print(n)

       # return data["sessionParameters"]["selected_azn_profiles"].split(",")
        return
    else:
        return []


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
    response = requests.put(uri, auth=(server["user"], server["pass"]), headers=headers, data=body, verify=False)
    return response


def ise_unblacklist_mac(server, mac_info):
    """ unblacklists mac_address and resets staticGroupAssignment and groupId to their original values
        (stored in mac_info dictionary).
    """
    call = "/ers/config/endpoint/" + mac_info.get("id")
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
    response = requests.put(uri, auth=(server["user"], server["pass"]), headers=headers, data=body, verify=False)
    return response


def ise_CoA(server, mac_address):
    # Issues a CoA for the given mac_address
    print("Issuing CoA for ", mac_address)
    call = "/admin/API/mnt/CoA/Reauth/" + server.get("server_name") + "/" + mac_address.upper() + "/0"
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    print(response)
    print(response.content)


def main():
    ise_server = {
        "host": "Satlab-dna-ise.cisco.com",
        "server_name": "satlab-dna-ise",
        "port": "9060",
        "user": "3sbananas",
        "pass": "C1scodna"
    }

    # Output Examples
    #print (ise_get_groupID_from_mac(ise_server, "00:0C:29:1F:2B:C0"))
    #print(ise_blacklist_mac(ise_server, " 00:0C:29:00:00:01"))
    #print(ise_unblacklist_mac(ise_server, " 00:0C:29:00:00:01"))
    #print(ise_get_endpoint_info(ise_server, " 00:0C:29:00:00:01"))
    #print(ise_get_usergroupid(ise_server, "Blacklist"))
    #print(ise_get_usergroups(ise_server))
    #print(ise_get_device_usergroup(ise_server, "00:0C:29:1F:2B:C0"))

    print(ise_get_device_usergroup(ise_server, "D0:2B:20:CA:AB:77"))
    #print(ise_get_endpoint_info(ise_server, "D0:2B:20:CA:AB:77"))


"""
#Test Blacklist and Unblacklist
    mac_info = ise_get_endpoint_info(ise_server, "00:0C:29:1F:2B:C0")
    print(mac_info)
    print("\n\n\n*****Blacklisting server**** \n ")
    ise_blacklist_mac(ise_server, "00:0C:29:1F:2B:C0")
    print(ise_get_endpoint_info(ise_server, "00:0C:29:1F:2B:C0"))
    print("\n\n\n*****UN-Blacklisting server**** \n ")
    ise_unblacklist_mac(ise_server, mac_info)
    print(ise_get_endpoint_info(ise_server, "00:0C:29:1F:2B:C0"))
    
"""

if __name__ == "__main__":
    main()