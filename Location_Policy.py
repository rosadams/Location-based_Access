import json
from CMX_API import *


class Location_Policy:
    def __init__(self, filename, cmx_server):
        self.filename = filename
        self.cmx_server = cmx_server
        try:
            with open(filename) as backup_file:
                self.data = json.load(backup_file)
        except:
            with open(filename, "w") as self.backup_file:
                self.data = {"blacklisted": [], "zone_policies": [],
                             "default_policy": {"allow_deny": "allow", "group_list": ["ALL_ACCOUNTS (default)"], "acl_list": []}}

                # get list of zones from CMX to populate zone policy data structure
                self.zone_list = cmx_get_zones(cmx_server)
                for zone in self.zone_list:
                    self.data.get("zone_policies").append(
                        {"zone_name": zone.get("hierarchy"), "zone_policy": {"allow_deny": "allow", "group_list": ["ALL_ACCOUNTS (default)"], "acl_list": []}})
                # Register zones via CMX API
                cmx_register_zone(self.cmx_server, self.zone_list)
                # backup to file
                json.dump(self.data, self.backup_file, indent=4)



    def sync_CMX_zones(self):
        # pull zone list from CMX.  Add any newly configured zones to the location policy data structure (data) with default (allow ALL) policy.
        self.cmx_zones = cmx_get_zones(self.cmx_server)
        self.cmx_zone_names = set([n.get("hierarchy") for n in self.cmx_zones])
        self.policy_zones = {n.get("zone_name") for n in self.data.get("zone_policies")}

        if self.policy_zones ^ self.cmx_zone_names != set():
            self.added_zones = self.cmx_zone_names - self.policy_zones
            if self.added_zones != set():
                # Zone/s have been added to CMX.  Add them to the policy object
                #print("adding zones to policy object", self.added_zones)
                for n in self.added_zones:
                    self.data.get("zone_policies").append(
                        {"zone_name": n, "zone_policy": {"allow_deny": "allow", "group_list": ["ALL_ACCOUNTS (default)"], "acl_list": []}})

            else:
                self.deleted_zones = self.policy_zones - self.cmx_zone_names
                # Zone/s have been deleted from CMX.  Delete them from the policy object
                #print("deleting zones from policy DB", self.added_zones)
                for n in self.data.get("zone_policies")[:]:
                    if n.get("zone_name") in self.deleted_zones:
                        self.data.get("zone_policies").remove(n)
            # Register zones in CMX
            #cmx_register_zone(self.cmx_server, self.cmx_zones)
            # backup updated policy
            self.backup()
        else:
            pass
            #print("policy and CMX zones are already sync'd")
        return


    def get(self):
        self.sync_CMX_zones()
        return self.data


    def update(self, policy_updates):
        # Apply updates to policy object and create list of zones to check
        self.zones_to_check = []
        for updt in policy_updates:
            self.zones_to_check.append(updt["zone_name"])
            if updt["zone_name"] == "default_policy":
                self.data["default_policy"]["allow_deny"] = updt["allow_deny"]
                self.data["default_policy"]["group_list"] = updt["group_list"]
            else:
                for pol in self.data["zone_policies"]:
                    if pol["zone_name"] == updt["zone_name"]:
                        pol["zone_policy"]["allow_deny"] = updt["allow_deny"]
                        pol["zone_policy"]["group_list"] = updt["group_list"]
        self.backup()
        return self.zones_to_check



    def get_for_zone(self, zone):
        for n in self.data.get("zone_policies"):
            if n.get("zone_name") == zone:
                return n.get("zone_policy")
        return


    def match_zone_groups(self, zone, grouplist):
        # Returns True if any groups in grouplist match any groups in location_policy grouplist for given zone.  False
        # if no matches.
        groupset = set(grouplist)
        for n in self.data.get("zone_policies"):
            if n.get("zone_name") == zone:
                policyset = set(n.get("zone_policy").get("group_list"))
        if groupset.intersection(policyset) == set():
            return False
        else:
            return True


    def match_default_groups(self, grouplist):
        # Returns True if any groups in grouplist match any groups in location_policy grouplist for for the default policy.  False
        # if no matches.
        groupset = set(grouplist)
        policyset = set(self.data.get("default_policy").get("group_list"))
        if groupset.intersection(policyset) == set():
            return False
        else:
            return True


    def zone_exists(self, zone):
        # Returns True if zone exists in loc_policy zone list
        for n in self.data.get("zone_policies"):
            if n.get("zone_name") == zone:
                return True
        return False


    def zone_allow(self, zone):
        # Returns True is zone policy = allow, and False if zone policy = False
        for n in self.data.get("zone_policies"):
            if n.get("zone_name") == zone:
                if (n.get("zone_policy").get("allow_deny")) == "allow":
                    return True
                else:
                    return False


    def in_blacklist(self, mac_address):
        # Returns mac_info for given mac_address if mac_address has been blacklisted.  Returns None is mac_address
        # is not in blacklist.
        for n in self.data.get("blacklisted"):
            if n.get("mac_address") == mac_address:
                return n

        return


    def unblacklist(self, mac_address):
        for n in self.data.get("blacklisted")[:]:
            print("unblacklisting from loc policy")
            if n.get("mac_address") == mac_address:
                self.data.get("blacklisted").remove(n)
        self.backup()
        return


    def blacklist(self, mac_info):
        self.data.get("blacklisted").append(mac_info)
        self.backup()
        return


    def backup(self):
        with open(self.filename, "w") as self.backup_file:
            json.dump(self.data, self.backup_file, indent=4)
        return

    def get_default(self):
        return self.data.get("default_policy")