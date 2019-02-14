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
                zonelist.append({"name":m.get("name"),
                                 "id": m.get("id"),
                                 "hierarchy": '>'.join(str(x) for x in m.get("ancestors")) + ">" + m.get("name")})
    return zonelist


def cmx_register_zone(server, zonelist):
    # Register Zone as one that will keep client counts
    call = "/api/config/v1/zoneCountParams/1"
    uri = ("https://" + server["host"]+ call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    zone_hierarchy = []
    zone_details = []
    zone_count = 0
    for n in zonelist:
        zone_hierarchy.append(n.get("hierarchy"))
        zone_details.append({"id": n.get("id"),
                             "hierarchy": n.get("hierarchy"), "name": n.get("name"), "active": "true"})
        zone_count += 1
    body = json.dumps(
           {
            "name": "ZoneCountParams",
            "zoneHierarchy": zone_hierarchy,
            "zoneIds": [],
            "zoneDetails": zone_details,
            "totalZones": zone_count,
            "debug": "true"
            }
            , indent=4)

    return requests.put(uri, auth=(server["user"], server["pass"]), headers=headers, data=body, verify=False)


def cmx_get_zonedevices(server, zone):
    # returns a list of mac_addresses for  all associated devices in a given zone
    call = "/api/location/v2/clients?mapHierarchy=" + (zone.rsplit("/", 1)[0])
    uri = ("https://" + server["host"]+ call + zone)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)

    assoc_dev = [n.get("macAddress")
                 for n in response.json()
                 if n.get("mapInfo").get("mapHierarchyString") == zone
                 and n.get("dot11Status") == "ASSOCIATED"
                ]
    return assoc_dev


def cmx_get_nonzonedevices(server):
    # returns a list of mac_addresses for  all associated devices in a given zone
    call = "/api/location/v2/clients?mapHierarchy="
    uri = ("https://" + server["host"]+ call)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.get(uri, auth=(server["user"], server["pass"]), headers=headers, verify=False)
    zones = [n.get("hierarchy") for n in cmx_get_zones(server)]
    assoc_dev = [n.get("macAddress")
                 for n in response.json()
                 if n.get("mapInfo").get("mapHierarchyString") not in zones
                 and n.get("dot11Status") == "ASSOCIATED"
                ]
    return assoc_dev
