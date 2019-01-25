import subprocess
import os
import platform
import socket
import time
import atexit
#import psutil
import requests
import json
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for



def render_policy(saved_policy, ise_groups, policy_options, zone):

    print('render_policy:', zone)

    # setup default browser display options
    allow_policy = {}
    for policy in policy_options:
        allow_policy[policy] = ''

    policy_groups = {}
    for group in ise_groups:
        policy_groups[group] = ''
    if zone == 'default_policy':
        policy_groups['ALL'] = ''


    # now add the policy selections to display in browser
    for key, value in allow_policy.items():
        if key.lower() == saved_policy['allow_deny']:
            allow_policy[key] = 'selected'
    print('render_policy:allow_policy:', allow_policy)


    for key, value in policy_groups.items():
        if key in saved_policy['policies_list']:
            policy_groups[key] = 'selected'
    print('render_policy:policy_groups: ', policy_groups)

    rendered_policy = {'policy': allow_policy, 'groups': policy_groups}

    return  rendered_policy


def ross_object_function_to_update_policy(changed_zones):
    
    print('function: ross_object_function_to_update_policy. Variable changed_zones need to be transformed for you object function')

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('config_update'))



@app.route('/cmxreceiver', methods =['POST'])
def cmxreceiver():
    if request.method == 'POST' :
        print("Previously done")
        return "OK"



@app.route('/config_update', methods =['GET', 'POST'])
def config_update():

    if request.method == 'GET' :

        with open('location_policy.json') as json_file:
            saved_policy = json.load(json_file)
            print(json.dumps(saved_policy, indent=4))

        ise_groups = ['loc-testing', 'Nurses', 'Doctors', 'Employees', 'Test',]
        ise_groups.append('ALL')
        # move the 'ALL' element to front of list
        ise_groups.insert(0, ise_groups.pop(-1))

        policy_options = ['Allow', 'Deny']

        default_policy = render_policy(saved_policy['default_policy'], ise_groups, policy_options, 'default_policy')
        print('default_policy:', default_policy)

        zones = {}
        list_value = 0
        for zone in saved_policy['zone_policies']:
            submit_policy = saved_policy['zone_policies'][list_value]['zone_policy']
            zones[zone['zone_name']] = render_policy(submit_policy, ise_groups, policy_options, zone['zone_name'])
            list_value = list_value + 1

        print('zones policy:', zones)

        return render_template("form_submit.html", zones=zones, default_policy=default_policy)

    else:

        print(request.form)
        changed_zones = []
        zone_numbers = []

        for key, value in request.form.items():
            if 'zone' in key:
                zone_numbers.append(key.strip('zone'))

        print(zone_numbers)

        for element in zone_numbers:
            zone_name = request.form.get('zone' + element)
            policy = request.form.get('policy' + element)
            group_list = request.form.getlist('group' + element)
            changed_zones.append({'zone_name' : zone_name,'policy': policy, 'group': group_list})

        for zone in changed_zones:
            print(json.dumps(zone, indent=4))

        ross_object_function_to_update_policy(changed_zones)

        return render_template('changed_policy.html', changed_zones=changed_zones)

if __name__ == "__main__" :

    flask_port = 5050

    print('\n********   Starting up Flask Web...    ********\n\n')

    app.run(host='0.0.0.0', port=flask_port)

