import logging
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
from Location_Policy import Location_Policy
from ISE_API import *
from CMX_API import *

ise_server = {
    "host": "Satlab-dna-ise.cisco.com",
    "port": "9060",
    "user": "3sbananas",
    "pass": "C1scodna",
    "server_name": "Satlab-dna-ise"
    }

cmx_server = {
    "host": "10.88.66.116",
    "server_name": "",
    "port": "",
    "user": "admin",
    "pass": "C1scodna!"
    }

# Setup Logging




bkup_file = "localpolicy.bak"


# Instantiate Location Policy
policy = Location_Policy(bkup_file, cmx_server)


def blacklist(mac_address):
    # if mac address has not already been blacklisted in the local policy:
    # 1. blacklist it in local policy,
    # 2. blacklist in ISE
    # 3. issue CoA.
    if policy.in_blacklist(mac_address) is None:
        print(ise_get_endpoint_info(ise_server, mac_address))
        policy.blacklist(ise_get_endpoint_info(ise_server, mac_address))
        ise_blacklist_mac(ise_server, mac_address)
        #ise_CoA(ise_server, mac_address)
        print("blacklisting ", mac_address)


def unblacklist(mac_address):
    # if mac address is in the blacklist
    # 1. unblacklist it in local policy,
    # 2. unblacklist in ISE
    # 3. issue CoA.
    if policy.in_blacklist(mac_address) is not None:
        print("mac_address is currently blacklisted in local policy. Unblacklisting.")
        ise_unblacklist_mac(ise_server, policy.in_blacklist(mac_address))
        #ise_CoA(ise_server, mac_address)
        policy.unblacklist(mac_address)
        print("unblaCklisted ", mac_address)


def mac_action(mac_address, username, zone, in_out):
    print(mac_address, username, zone, in_out)
    user_groups = ise_get_userinfo(ise_server, username).get("usergroup_names")

    if in_out == "IN":
        if policy.zone_exists(zone) is False:
            zone_policy = policy.get_default()
            allow_deny = zone_policy.get("allow_deny")
            allow_deny_all = policy.match_default_groups(["ALL_ACCOUNTS (default)"])
            group_match = policy.match_default_groups(user_groups)
            # *** CMX call to get all zones & update policy
            print("zone ", zone, "does not exist in policy")
        else:
            zone_policy = policy.get_for_zone(zone)
            allow_deny = zone_policy.get("allow_deny")
            allow_deny_all = policy.match_zone_groups(zone, ["ALL_ACCOUNTS (default)"])
            group_match = policy.match_zone_groups(zone, user_groups)
        if allow_deny == "allow" and allow_deny_all == "ALL":
            print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy - Allow ALL")
            print(mac_address, "UnBlacklisted")
            unblacklist(mac_address)
        elif allow_deny == "deny" and allow_deny_all == "ALL":
            print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy - Deny ALL")
            print(mac_address, "Blacklisted")
            blacklist(mac_address)
        else:
            if (allow_deny == "allow" and group_match == "NONE") or (allow_deny == "deny" and group_match == "ALL"):
                print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy - Deny ALL")
                print(mac_address, "Blacklisted")
                blacklist(mac_address)
            else:
                print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy", allow_deny)
                print(mac_address, "UnBlacklisted")
                unblacklist(mac_address)
    else:
        print("default policy applied")
        zone_policy = policy.get_default()
        allow_deny = zone_policy.get("allow_deny")
        allow_deny_all = policy.match_default_groups(["ALL_ACCOUNTS (default)"])
        group_match = policy.match_default_groups(user_groups)
        if allow_deny == "allow" and allow_deny_all == "ALL":
            print(mac_address, "in user group/s: ", user_groups, " matches", zone, "Default Policy - Allow ALL")
            print(mac_address, "UnBlacklisted")
            unblacklist(mac_address)
        elif allow_deny == "deny" and allow_deny_all == "ALL":
            print(mac_address, "in user group/s: ", user_groups, " matches", zone, "Default Policy - Deny ALL")
            print(mac_address, "Blacklisted")
            blacklist(mac_address)
        else:
            if (allow_deny == "allow" and group_match == "NONE") or (allow_deny == "deny" and group_match == "ALL"):
                print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy - Deny ALL")
                print(mac_address, "Blacklisted")
                # blacklist(mac_address)
            else:
                print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy", allow_deny)
                print(mac_address, "UnBlacklisted")
                unblacklist(mac_address)



def zone_action(changed_zones):
    for n in changed_zones:
        if n["zone_name"] != "default_policy":
            for mac_addr in cmx_get_zonedevices(cmx_server, n["zone_name"]):
                mac_action(mac_addr, n["zone_name"], "In")
        else:
            for mac_addr in cmx_get_nonzonedevices(cmx_server):
                mac_action(mac_addr, n["zone_name"], "Out")
    return


def render_policy(saved_policy, ise_groups, policy_options, zone):
    # setup default browser display options
    allow_policy = {}
    for policy in policy_options:
        allow_policy[policy] = ''

    policy_groups = {}
    for group in ise_groups:
        policy_groups[group] = ''

    # now add the policy selections to display in browser
    for key, value in allow_policy.items():
        if key.lower() == saved_policy['allow_deny']:
            allow_policy[key] = 'selected'
    #print('render_policy:allow_policy:', allow_policy)


    for key, value in policy_groups.items():
        if key in saved_policy['group_list']:
            policy_groups[key] = 'selected'
    #print('render_policy:policy_groups: ', policy_groups)

    rendered_policy = {'policy': allow_policy, 'groups': policy_groups}

    return  rendered_policy


app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('config_update'))



@app.route('/cmxreceiver', methods =['POST'])
def cmxreceiver():
    if request.method == 'POST':
        area_json = request.get_json()
        zone = area_json.get("notifications")[0].get("locationMapHierarchy")
        mac_address = area_json.get("notifications")[0].get("deviceId")
        username = area_json.get("notifications")[0].get("username")
        in_out = area_json.get("notifications")[0].get("boundary").replace("SIDE", "")
        mac_action(mac_address, username, zone, in_out)
        return "OK"


@app.route('/config_update', methods =['GET', 'POST'])
def config_update():
    global policy
    if request.method == 'GET':
        saved_policy = policy.get()
        ise_groups = ise_get_usergroups(ise_server)
        policy_options = ['Allow', 'Deny']

        default_policy = render_policy(saved_policy['default_policy'], ise_groups, policy_options, 'default_policy')

        zones = {}
        list_value = 0
        for zone in saved_policy['zone_policies']:
            submit_policy = saved_policy['zone_policies'][list_value]['zone_policy']
            zones[zone['zone_name']] = render_policy(submit_policy, ise_groups, policy_options, zone['zone_name'])
            list_value = list_value + 1

        return render_template("form_submit.html", zones=zones, default_policy=default_policy)

    else:
        changed_zones = []
        zone_numbers = []

        for key, value in request.form.items():
            if 'zone' in key:
                zone_numbers.append(key.strip('zone'))

        for element in zone_numbers:
            zone_name = request.form.get('zone' + element)
            policy_option = request.form.get('policy' + element)
            group_list = request.form.getlist('group' + element)
            changed_zones.append({'zone_name': zone_name, 'allow_deny': policy_option, 'group_list': group_list})

        policy.update(changed_zones)
        zone_action(changed_zones)

        return render_template('changed_policy.html', changed_zones=changed_zones)



if __name__ == "__main__" :

    flask_port = 5050

    print('\n********   Starting up Flask Web...    ********\n\n')

    app.run(host='0.0.0.0', port=flask_port, threaded=True, debug=True)
