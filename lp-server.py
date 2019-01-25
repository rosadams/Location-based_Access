from flask import Flask, flash, redirect, render_template, request, session, abort, url_for

from Location_Policy import Location_Policy
from ISE_API import *

ise_server = {
    "host": "Satlab-dna-ise.cisco.com",
    "port": "9060",
    "user": "3sbananas",
    "pass": "C1scodna",
    "server_name": "Satlab-dna-ise"
    }

cmx_server = {
    "host": "10.88.66.124",
    "server_name": "",
    "port": "",
    "user": "admin",
    "pass": "C1scodna!"
    }


bkup_file = "localpolicy.bak"


# Instantiate Location Policy
policy = Location_Policy(bkup_file, cmx_server)



def blacklist(mac_address):
    if policy.in_blacklist(mac_address) == None:
        policy.blacklist(ise_get_endpoint_info(ise_server, mac_address))
        ise_blacklist_mac(ise_server, mac_address)
        ise_CoA(ise_server, mac_address)



def unblacklist(mac_address):
    if policy.in_blacklist(mac_address) != None:
        ise_unblacklist_mac(ise_server, policy.in_blacklist(mac_address))
        policy.unblacklist(mac_address)
        ise_CoA(ise_server, mac_address)



def mac_action(mac_address, zone, in_out):
    print(mac_address, zone, in_out)
    user_groups = ise_get_device_usergroup(ise_server, mac_address)
    user_groups.append("ALL")


    if in_out == "In":

        if policy.zone_exists(zone) == False:
            zone_policy = policy.get_default()
            allow_deny = zone_policy.get("allow_deny")
            group_match = policy.match_default_groups(user_groups)
            #*** CMX call to get all zones & update policy
            print("zone does not exist")
        else:
            zone_policy = policy.get_for_zone(zone)
            allow_deny = zone_policy.get("allow_deny")
            group_match = policy.match_zone_groups(zone, user_groups)
        print("allow_deny = ", allow_deny)
        print("group_match = ", group_match)



        if allow_deny == "allow" and  group_match == False:
            print("blacklist:" + mac_address)
        elif allow_deny == "deny" and  group_match == True:
            print("blacklist")
        else:
            print("unblacklist1: ")

    else:
        print("default policy applied")
        zone_policy = policy.get_default()
        allow_deny = zone_policy.get("allow_deny")
        group_match = policy.match_default_groups(user_groups)

        if allow_deny == "allow" and  group_match == False:
            print("default blacklist1:")
        elif allow_deny == "deny" and  group_match == True:
            print("default blacklist2")
        else:
            print("defauklt unblacklist1: ")



app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('areaA'))



@app.route('/cmxreceiver', methods =['POST'])
def cmxreceiver():
    if request.method == 'POST' :
        #query = request.form['query'] #this is an example how you'd get a variable -query- directly out of the form
        area_json = request.get_json()
        zone = area_json.get("notifications")[0].get("locationMapHierarchy")
        mac_address = area_json.get("notifications")[0].get("deviceId")
        in_out = area_json.get("notifications")[0].get("subscriptionName").split()[-1]

        mac_action(mac_address, zone, in_out)
        return "OK"


@app.route('/config_update', methods =['POST'])
def config_update():
    if request.method == 'POST' :
        #query = request.form['query'] #this is an example how you'd get a variable -query- directly out of the form
        area_json = request.get_json()
        print('Output from URL route point:\nArea B json is =', area_json)
        run_update('areaB', area_json)
        return "OK"


if __name__ == "__main__" :

    flask_port = 5050

    print('\n********   Starting up Flask Web...    ********\n\n')

    app.run(host='0.0.0.0', port=flask_port)