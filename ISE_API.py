import requests
import json
import xmltodict
from requests.auth import HTTPBasicAuth

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
    endpoint_info = {"mac_address": response.json().get("ERSEndPoint").get("mac"),
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
    blacklist = ise_get_usergroupid(server, "Blacklist")

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
    return requests.put(uri, auth=(server["user"], server["pass"]), headers=headers, data=body, verify=False)



def ise_CoA(server, mac_address):
    # Issues a CoA for the given mac_address

    call = "/admin/API/mnt/CoA/Reauth/" + server.get("server_name") + "/" + mac_address + "/1"
    uri = ("https://" + server["host"] + call)
    headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    return



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