import subprocess
import os
import sys
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


def check_webhook():

    url = WEBEX_URL + '/webhooks'

    ngrok_url = requests.get(
        "http://127.0.0.1:4040/api/tunnels", headers={"Content-Type": "application/json"}).json()

    for urls in ngrok_url["tunnels"]:
        if "https://" in urls['public_url']:
            target_url = urls['public_url']
            address = urls['config']['addr']
            print('Ngrok target_url is:', target_url)
            print('Ngrok address is:', address)

    webhook_js = send_spark_get(url, js=True)
    print('webhook_js initial check is: ', webhook_js)

    items = webhook_js['items']

    if len(items) > 0 :
        #print(items)
        for webhook in range(len(items)) :
            if ((items[webhook]['name'] == webhook_name) and (items[webhook]['resource'] in resources)):
                #print('Webhook name =', items[webhook]['name'])
                #print('resource =', items[webhook]['resource'] )
                send_spark_delete(url + '/' + items[webhook]['id'])


    for webhook in resources :
        payload = {'name': webhook_name, 'targetUrl': target_url + bot_route, 'resource' : webhook, 'event' : event}
        webhook_js = send_spark_post(url, data=payload, js=True)
        print(webhook_js)

    return


def send_spark_get(url, payload=None, js=True):

    if payload == None:
        request = requests.get(url, headers=headers)
    else:
        request = requests.get(url, headers=headers, params=payload)
    if js == True:
        request= request.json()
    return request

def send_spark_delete(url, js=False):

  request = requests.delete(url, headers=headers)
  if js != False:
    request = request.json()
  return request


def send_spark_post(url, data, js=True):

  request = requests.post(url, json.dumps(data), headers=headers)
  if js:
    request = request.json()
  return request


def check_bot():

    url = WEBEX_URL + '/people/me'

    '''
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Bearer " + WEBEX_BOT_TOKEN
    }
    '''

    print('Connecting to Webex Teams Cloud Service...')
    try:
        resp = requests.get(url, headers=headers, timeout=25, verify=False)
        resp.raise_for_status()
    except requests.exceptions.Timeout as err:
        print('\n', err)
        print('Webex Teams appears to be unreachable!!')
        sys.exit(1)
    except requests.exceptions.HTTPError as err:
        print('\n', err)
        if resp.status_code == 401:
            print("Looks like your provided Webex Teams Bot access token is not correct. \n"
                  "Please review it and make sure it belongs to your bot account.\n"
                  "Do not worry if you have lost the access token. "
                  "You can always go to https://developer.webex.com/my-apps "
                  "URL and generate a new access token.")
        else:
            print('HTTPError: Check error code', resp.status_code)
        sys.exit(1)
    except requests.exceptions.RequestException as err:
        print('\n', err)
        print('RequestException')
        sys.exit(1)

    if resp.status_code == 200:
        response_json = resp.json()
        bot_name = response_json['displayName']
        bot_email = response_json['emails'][0]
        print('Status code={}.\nResponse={}\n'.format(resp.status_code, response_json))

        return bot_name, bot_email


def help():
    return "Sure! I can help. Below are the commands that I understand:<br/>" \
            "`Help` - I will display what I can do.<br/>" \
            "`Hello` - I will display my greeting message<br/>" \
            "`Zones` - I will display all the zones in the policy database <br/>" \
            "`Groups` - I will displace all the ISE groups that can be used in a Zone policy <br/>" \
            "`Display [Zone Name]` - I will display the policy for [Zone Name] <br/>" \
            "`Change [Zone Name] policy=[policy] groups=group1, group2, group3` <br/>" \
            "`[ ]` represent variables. <br/>"



def hello():
    return "Hi my name is %s bot.<br/>" \
           "Type `Help` to see what I can do.<br/>" % bot_name


def get_zones(saved_policy):

    message = '**The following Zones are defined:**<br/>'
    for zone in saved_policy['zone_policies']:
        message += (zone['zone_name'] + '<br/>')

    return message


def get_groups(groups):

    message = '**The following ISE groups can be used in a zone policy:**<br/>'
    for group in groups:
        message += (group + '<br/>')

    return message

def display_zone_policy(saved_policy, search_zone):

    message = '**Policy for zone**: {}<br/>'.format(search_zone)
    for zone in saved_policy['zone_policies']:
        if zone['zone_name'] == search_zone.strip():
            message += ('**Policy**: ' + zone['zone_policy']['allow_deny'] + '<br/>')
            groups = ', '.join(zone['zone_policy']['policies_list'])
            message += ('**Groups**: ' + groups + '<br/>')
    return message

def change_zone_policy(policy, error):

    if error!='':
        return error

    zone = policy.split('policy', maxsplit=1)
    policy = 'policy' + zone[1].strip()
    split_policy=policy.split(' ', maxsplit=1)
    policy=split_policy[0]
    groups=split_policy[1]
    policy_msg = policy.split('=')[1]
    groups_msg = groups.split('=')[1]
    message = '**Policy was changed for zone**: {}<br/>'.format(zone[0])
    message += ('**Policy**: ' + policy_msg + '<br/>')
    message += ('**Groups**: ' + groups_msg + '<br/>')

    groups_msg = groups_msg.split(',')
    for group_index in range(len(groups_msg)):
        groups_msg[group_index]=groups_msg[group_index].strip()

    changed_zones = {'zone_name' : zone[0], 'zone_policy' : {'allow_deny' : policy_msg, 'policies_list' : groups_msg}}

    print(json.dumps(changed_zones, indent=4))

    ross_object_function_to_update_policy(changed_zones)

    return message


app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('config_update'))



@app.route('/cmxreceiver', methods =['POST'])
def cmxreceiver():
    if request.method == 'POST' :
        print("Previously done")
        return "OK"


@app.route('/bot', methods =['GET', 'POST'])
def bot():

    if request.method == 'GET' :
        print('Hello bot get request')
        return '<br/><br/>Location Policy Bot is up and running. @mention {0} from Teams <strong>@{0} help</strong> to start!'.format(bot_name)


    elif request.method == 'POST':

        with open('location_policy.json') as json_file:
            saved_policy = json.load(json_file)
            #print(json.dumps(saved_policy, indent=4))

        ise_groups = ['loc-testing', 'Nurses', 'Doctors', 'Employees', 'Test', ]

        webhook = request.get_json()
        print(webhook)

        resource = webhook['resource']
        senders_email = webhook['data']['personEmail']
        room_id = webhook['data']['roomId']

        if resource == "memberships" and senders_email == bot_email:
            print('webhook is: ', webhook)
            send_spark_post("https://api.ciscospark.com/v1/messages",
                            {
                                "roomId": room_id,
                                "markdown": (hello() +
                                             "**Note: This is a group space and you have to call "
                                             "me specifically with `@%s` for me to respond.**" % bot_name)
                            }
                            )

        if ("@webex.bot" not in webhook['data']['personEmail']):
            print('Requester email= ', webhook['data']['personEmail'])
            print('msgID= ', webhook['data']['id'])
            result = send_spark_get(
                'https://api.ciscospark.com/v1/messages/{}'.format(webhook['data']['id']))
            print('Raw request=', result['text'])
            message = result['text']
            message = message.replace(bot_name, '').strip()
            message = message.split()
            message[0] = message[0].lower()
            message = ' '.join(message)
            print('Parsed request=', message)
            if message.startswith('help'):
                msg = help()
            elif message.startswith('hello'):
                msg = hello()
            elif message.startswith('zones'):
                msg = get_zones(saved_policy)
            elif message.startswith('groups'):
                msg = get_groups(ise_groups)
            elif message.startswith('display'):
                zone = message.replace('display', '')
                msg = display_zone_policy(saved_policy, zone)
            elif message.startswith('change'):
                policy = message.replace('change', '')
                error = ''
                if not ' policy' in policy:
                    error = 'Confirm Change policy request is using the correct syntax:<br/>'
                    error += ('change [zone_name] policy=[policy] groups=([groups])')
                elif not ' groups' in policy:
                    error = 'Confirm Change policy request is using the correct syntax:<br/>'
                    error += ('change [zone_name] policy=[policy] groups=([groups])')
                msg = change_zone_policy(policy, error)
            else:
                msg = "Sorry, but I did not understand your request. Type `Help` to see what I can do"

            if msg != None:
                send_spark_post("https://api.ciscospark.com/v1/messages",
                                {"roomId": webhook['data']['roomId'], "markdown": msg})

    return "true"



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
            #changed_zones.append({'zone_name' : zone_name,'policy': policy, 'group': group_list})
            changed_zones.append({'zone_name' : zone_name,'zone_policy': {'allow_deny': policy, 'policies_list': group_list}})

        for zone in changed_zones:
            print(json.dumps(zone, indent=4))

        ross_object_function_to_update_policy(changed_zones)

        return render_template('changed_policy.html', changed_zones=changed_zones)

if __name__ == "__main__" :


    if 'WEBEX_BOT_TOKEN' in os.environ:
        WEBEX_BOT_TOKEN = os.environ.get('WEBEX_BOT_TOKEN')

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Bearer " + WEBEX_BOT_TOKEN
    }

    WEBEX_URL = "https://api.ciscospark.com/v1"

    bot_name, bot_email = check_bot()

    webhook_name = 'location_query'
    resources = ['messages', 'memberships']
    event = 'created'
    bot_route = '/bot'

    print(WEBEX_BOT_TOKEN)
    print(bot_name)
    print(bot_email)

    check_webhook()


    flask_port = 5050

    print('\n********   Starting up Flask Web...    ********\n\n')

    app.run(host='0.0.0.0', port=flask_port)

