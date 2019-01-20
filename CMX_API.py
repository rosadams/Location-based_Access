import requests
import json
import xmltodict
from requests.auth import HTTPBasicAuth

# suppress security warning messages due to having verify=false in requests
requests.packages.urllib3.disable_warnings()


def cmx_get_zones(server):
    #
    call = "/api/config/v1/heterarchy/allUserLevels?filterElements=false"
    uri = ("https://" + server["host"]+ call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    zonelist = []
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    superzones = response.json().get("userLevels")
    for n in superzones:
        if n.get("originalName") == "Zone":
            for m in n.get("children"):
                zonelist.append(m.get("name"))
    return zonelist


def cmx_get_zonedevices(server, zone):
    #
    call = "/api/location/v2/clients?mapHierarchy=System Campus>Cisco San Antonio>2nd Floor>"
    uri = ("https://" + server["host"]+ call + zone)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    zonelist = []
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    for n in response.json():
        if n.get("dot11Status") == "ASSOCIATED":
            print(n.get("macAddress"), n.get("mapInfo").get("mapHierarchyString"))


def main():
    cmx_server = {
        "host": "10.88.66.124",
        "server_name": "",
        "port": "",
        "user": "admin",
        "pass": "C1scodna!"
    }

    print(cmx_get_zones(cmx_server))

    cmx_get_zonedevices(cmx_server, "Zone A")


if __name__ == "__main__":
    main()