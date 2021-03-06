import os
import json
import requests
import base64
import configparser
import logging
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
from Location_Policy import Location_Policy
from ISE_API import *
from CMX_API import *
from locationbot import get_zones, get_groups, display_zone_policy, change_zone_policy, help, hello, indexed_mapping
from webexbot import send_spark_get, send_spark_post, send_spark_delete, check_bot, check_webhook

flasklog = logging.getLogger('werkzeug')
flasklog.disabled = True

bot_name = ''
WEBEX_BOT_TOKEN = 'None'
config = configparser.ConfigParser()
config_file_path = './startup.ini'
bkup_file = "localpolicy.bak"


if 'WEBEX_BOT_TOKEN' in os.environ:
    WEBEX_BOT_TOKEN = os.environ.get('WEBEX_BOT_TOKEN')
    print('Found bot token in environment')

try:
    config.read(config_file_path)
    if config.has_option('BOT', 'token') and config['BOT']['token']!='':
        WEBEX_BOT_TOKEN = config['BOT']['token']
        print('Found bot token in {}'.format(config_file_path))

except:
    pass

if WEBEX_BOT_TOKEN != 'None':
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Bearer " + WEBEX_BOT_TOKEN
    }

    WEBEX_URL = "https://api.ciscospark.com/v1"

    bot_name, bot_email = check_bot(WEBEX_URL, headers)

    webhook_name = 'location_query'
    resources = ['messages', 'memberships']
    event = 'created'
    bot_route = '/bot'
    webhook_vars = {'webhook_name': webhook_name, 'resources': resources, 'event': event, 'bot_route': bot_route}

    print(bot_name)
    print(bot_email)

    check_webhook(WEBEX_URL, headers, webhook_vars)
else:
    print('Webex Bot is not configured. Pass bot token via environment or launch bootstrap route on webserver to configure and restart')


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


try:
    config.read(config_file_path)
    if config['GENERAL'].getboolean('configured_state'):
        ise_server = dict(config.items('ISE'))
        cmx_server = dict(config.items('CMX'))
        #print(ise_server)
        #print(cmx_server)
        print('Run Ross policy = Location_Policy(bkup_file, cmx_server)')
    else:
        print('Server not configured. Launch bootstrap route on webserver to configure and restart')

except:
        print('Server not configured. Launch bootstrap route on webserver to configure and restart')


# Instantiate Location Policy
policy = Location_Policy(bkup_file, cmx_server)


def blacklist(mac_address):
    # if mac address has not already been blacklisted in the local policy:
    # 1. blacklist it in local policy,
    # 2. blacklist in ISE
    # 3. issue CoA.
    print("trying to blacklist ", mac_address)
    if policy.in_blacklist(mac_address) is None:
        #print(ise_get_endpoint_info(ise_server, mac_address))
        policy.blacklist(ise_get_endpoint_info(ise_server, mac_address))
        print(ise_blacklist_mac(ise_server, mac_address))
        ise_CoA(ise_server, mac_address)
    else:
        print(mac_address, " is already in blacklist.  No action taken.")


def unblacklist(mac_address):
    print("trying to unblacklist ", mac_address)
    if policy.in_blacklist(mac_address) is not None:
        ise_unblacklist_mac(ise_server, policy.in_blacklist(mac_address))
        ise_CoA(ise_server, mac_address)
        policy.unblacklist(mac_address)
        print("unblacklisted ", mac_address)
    else:
        print(mac_address, " is not in blacklist.  No action taken.")


def mac_action(mac_address, username, zone, in_out):
    print("\n\n******", mac_address, username, zone, in_out)
    user_groups = ise_get_userinfo(ise_server, username).get("usergroup_names")

    if in_out.upper() == "IN":
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
            print("zone policy allow_deny = ", allow_deny )
            print("allow_deny_all =", allow_deny_all )
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

        print("allow_deny = ", allow_deny)
        print("allow_deny all = ", allow_deny_all)

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
                blacklist(mac_address)
            else:
                print(mac_address, "in user group/s: ", user_groups, " matches", zone, "policy", allow_deny)
                print(mac_address, "UnBlacklisted")
                unblacklist(mac_address)



def zone_action(changed_zones):
    print("Applying New zone policy: ", changed_zones)

    for n in changed_zones:
        if n["zone_name"] != "default_policy":
            print(cmx_get_zonedevices(cmx_server, n["zone_name"]))
            for dev in cmx_get_zonedevices(cmx_server, n["zone_name"]):
                mac_action(dev.get("mac_address"), dev.get("username"), n["zone_name"], "In")
        else:
            for dev in cmx_get_nonzonedevices(cmx_server):
                mac_action(dev.get("mac_address"), dev.get("username"), n["zone_name"], "Out")
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


@app.route('/', methods = ['GET'])
def index():

        return render_template("index.html")

@app.route('/test', methods =['GET', 'POST'])
def test():

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

        return render_template("form_submitv2.html", zones=zones, default_policy=default_policy)

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

@app.route('/bootstrap', methods =['GET', 'POST'])
def bootstrap():

    if request.method == 'GET':

        if not os.path.isfile(config_file_path):
            config['GENERAL'] = {'configured_state': 'false'}
            config['ISE'] = {
                "host": "",
                "port": "9060",
                "user": "",
                "pass": "",
                "server_name": ""
            }
            config['CMX'] = {
                "host": "",
                "server_name": "",
                "port": "",
                "user": "",
                "pass": ""
            }
            config['BOT'] = {'token': ""}


            with open(config_file_path, 'w') as config_file:
                config.write(config_file)

        config.read(config_file_path)

        ise_server = dict(config.items('ISE'))
        cmx_server = dict(config.items('CMX'))
        bot_var = dict(config.items('BOT'))
        bootstrap_vars = {'ise_server': ise_server, 'cmx_server': cmx_server, 'bot': bot_var}

        if 'WEBEX_BOT_TOKEN' in os.environ:
            display_token='no'
        else:
            display_token='yes'

        return render_template("bootstrap.html", token=display_token, vars=bootstrap_vars)

    elif request.method == 'POST':
        config.read(config_file_path)
        config.set('ISE', 'host', request.form.get('ise_host'))
        config.set('ISE', 'port', request.form.get('ise_port'))
        config.set('ISE', 'user', request.form.get('ise_user'))
        config.set('ISE', 'pass', request.form.get('ise_password'))
        config.set('ISE', 'server_name', request.form.get('ise_server_name'))
        config.set('CMX', 'host', request.form.get('cmx_host'))
        config.set('CMX', 'port', request.form.get('cmx_port'))
        config.set('CMX', 'user', request.form.get('cmx_user'))
        config.set('CMX', 'pass', request.form.get('cmx_password'))
        if 'bot_token' in request.form:
            config.set('BOT', 'token', request.form.get('bot_token'))
        config['GENERAL'] = {'configured_state': 'true'}

        with open(config_file_path, 'w') as config_file:
            config.write(config_file)

        return '<br/><br/>Application configured. Look at <strong>startup.ini</strong> file for configuration options entered. Restart server.'


@app.route('/bot', methods =['GET', 'POST'])
def bot():

    if request.method == 'GET' :
        print('Hello bot get request')
        message = 'The Location Bot is not running!'

        if bot_name != '':
            message = '<br/><br/>Location Policy Bot is up and running. @mention {0} from Teams <strong>@{0} help</strong> to start!'.format(bot_name)

        return message


    elif request.method == 'POST':

        saved_policy = policy.get()
        ise_groups = ise_get_usergroups(ise_server)
        webhook = request.get_json()
        resource = webhook['resource']
        senders_email = webhook['data']['personEmail']
        room_id = webhook['data']['roomId']

        if resource == "memberships" and senders_email == bot_email:
            #print('webhook is: ', webhook)
            send_spark_post("https://api.ciscospark.com/v1/messages",
                            {
                                "roomId": room_id,
                                "markdown": (hello() +
                                             "**Note: This is a group space and you have to call "
                                             "me specifically with `@%s` for me to respond.**" % bot_name)
                            }
                            )

        if ("@webex.bot" not in webhook['data']['personEmail']):
            #print('Requester email= ', webhook['data']['personEmail'])
            #print('msgID= ', webhook['data']['id'])
            result = send_spark_get(
                'https://api.ciscospark.com/v1/messages/{}'.format(webhook['data']['id']), headers)
            #print('Raw request=', result['text'])
            message = result['text']
            message = message.replace(bot_name, '').strip()
            message = message.split()
            print(message)
            message[0] = message[0].lower()
            message = ' '.join(message)
            #print('Parsed request=', message)
            if message.startswith('help'):
                msg = help()
            elif message.startswith('hello'):
                msg = hello(bot_name)
            elif message.startswith('zones'):
                msg = get_zones(saved_policy)
            elif message.startswith('groups'):
                msg = get_groups(ise_groups)
            elif message.startswith('display'):
                zone = message.replace('display', '')
                msg = display_zone_policy(saved_policy, zone)
            elif message.startswith('change'):
                zone_policy = message.replace('change', '')
                error = ''
                if not ' policy' in zone_policy:
                    error = 'Confirm Change policy request is using the correct syntax:<br/>'
                    error += ('change [zone_name] policy=[policy] groups=([groups])')
                elif not ' groups' in zone_policy:
                    error = 'Confirm Change policy request is using the correct syntax:<br/>'
                    error += ('change [zone_name] policy=[policy] groups=([groups])')

                if zone_policy == '':
                    sorted_zone_dict, sorted_group_dict = indexed_mapping(saved_policy, ise_groups)

                    msg = '**_Select Zone number from list below:_**<br/>'
                    zone_length = 0
                    for index, value in sorted_zone_dict.items():
                        msg += index + '.  ' + value + '<br/>'
                        zone_length = zone_length + 1
                    #msg += str(zone_length + 1) + '.  Default Zone'

                    msg += '<br/>'
                    msg += '**_Select Groups (comma separated) from list below:_**<br/>'

                    for index, value in sorted_group_dict.items():
                        msg += index + '.  ' + value + '<br/>'

                    msg += '<br/>'
                    msg += 'Syntax: **change [zone_number] policy=[allow | deny ] groups=[group_1, group_2, group_n]**<br/>'

                    send_spark_post("https://api.ciscospark.com/v1/messages", headers,
                                    {"roomId": webhook['data']['roomId'], "markdown": msg})

                    return "true"

                msg, changed_zones = change_zone_policy(zone_policy, error)

                if len(changed_zones) > 0:
                    if changed_zones[0]['zone_name'].isdigit():
                        sorted_zone_dict, sorted_group_dict = indexed_mapping(saved_policy, ise_groups)
                        groups_list = changed_zones[0]['group_list']
                        temp_list = []
                        for group_index, group in enumerate(groups_list):
                            temp_list.append(sorted_group_dict[group].strip())

                        groups_msg = ', '.join(temp_list)
                        zone_policy = sorted_zone_dict[changed_zones[0]['zone_name']] + ' policy='
                        zone_policy = zone_policy +  changed_zones[0]['allow_deny']
                        zone_policy = zone_policy + ' groups=' + groups_msg
                        msg, changed_zones = change_zone_policy(zone_policy, error)

                    else:
                        pass

                print(json.dumps(changed_zones, indent=4))

                if changed_zones[0]['zone_name'] == 'Default Zone':
                    changed_zones[0]['zone_name'] = 'default_policy'
                policy.update(changed_zones)
                zone_action(changed_zones)

            else:
                msg = "Sorry, but I did not understand your request. Type `Help` to see what I can do"
            print("Message: ", msg)
            if msg != None:
                send_spark_post("https://api.ciscospark.com/v1/messages", headers,
                                {"roomId": webhook['data']['roomId'], "markdown": msg})

    return "true"


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

        return render_template("form_submitv2.html", zones=zones, default_policy=default_policy)

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


@app.route('/server_status/<server>', methods =['GET', 'POST'])
def servers_status(server):

    if request.method == 'GET':
        try:
            config.read(config_file_path)
        except:
            print('Configure servers before you can start testing connectivity')

        if server == 'ise':
            print('Run test routing for ISE')

            url = 'https://' + config.get('ISE', 'host') + ':' + config.get('ISE', 'port') + '/ers/config/endpointcert/versioninfo'

            userPass = config.get('ISE', 'user') + ':' + config.get('ISE', 'pass')
            base64Val = base64.b64encode(userPass.encode())
            print(url)
            print(userPass)
            print(base64Val)
            test_token = 'Basic ' + base64Val.decode()
            print(test_token)

            print('Trying connection to ISE server : {} ...'.format(config.get('ISE', 'host')))

        elif server == 'cmx':
            print('Run test routing for CMX')

            url = 'https://' + config.get('CMX', 'host') + '/api/location/v2/clients'

            userPass = config.get('CMX', 'user') + ':' + config.get('CMX', 'pass')
            base64Val = base64.b64encode(userPass.encode())
            print(url)
            print(userPass)
            print(base64Val)
            test_token = 'Basic ' + base64Val.decode()
            print(test_token)

            print('Trying connection to CMX server : {} ...'.format(config.get('CMX', 'host')))


        elif server == 'bot':
            print('Run test routing for Bot')

            url = 'https://api.ciscospark.com/v1/people/me'

            if 'WEBEX_BOT_TOKEN' in os.environ:
                test_token = os.environ.get('WEBEX_BOT_TOKEN')

            elif config.has_option('BOT', 'token') and config['BOT']['token'] != '':
                test_token = config['BOT']['token']

            else:
                return 'Bot is not configured yet'

            test_token = 'Bearer ' + test_token
            print(test_token)

            print('Trying connection to Webex bot endpoint: https://api.ciscospark.com/v1/people/me ...')

        headers = {
            "authorization" : test_token,
            "accept" : "application/json"
        }
        print(headers)

        extended_error = ''

        open('error.txt', 'w').close()
        try:
            resp = requests.get(url, headers=headers, timeout=25, verify=False)
            resp.raise_for_status()
        except requests.exceptions.Timeout as err:
            print('\n', err)
            extended_error = '{} server appears to be unreachable!!'.format(server.upper())
            print(extended_error)
            f = open('error.txt', 'w')
            f.write(str(err))
            f.close()
        except requests.exceptions.HTTPError as err:
            print('\n', err)
            if resp.status_code == 401:
                extended_error ="Looks like your token is invalid. \n"
                extended_error = extended_error + "Ensure you used the correct username and password.\n\n"
                print(extended_error)
                f = open('error.txt', 'w')
                f.write(str(err))
                f.close()
            else:
                extended_error = 'HTTPError: Check error code ' + str(resp.status_code)
                print(extended_error)

        except requests.exceptions.RequestException as err:
            print('\n', err)
            extended_error = 'RequestException'
            print(extended_error)
            f = open('error.txt', 'w')
            f.write(str(err))
            f.close()

        try:
            message = 'Test %s server response: %s<br/>' % (server, resp.status_code)

        except:

            message = 'Test %s server response: %s<br/>' % (server, 'Some other error')

        message += '<br/>'

        extended_error = extended_error.replace('\n', '<br/>')
        message += extended_error

        if os.path.isfile('error.txt'):
            with open('error.txt') as file:
                for line in file:
                    message +=  line + '<br/>'

        print(message)

        return message

    else:
        return 'This is a roadmap item!'



if __name__ == "__main__" :

    flask_port = 5050

    print('\n********   Starting up Flask Web...    ********\n\n')

    app.run(host='0.0.0.0', port=flask_port, debug=False)