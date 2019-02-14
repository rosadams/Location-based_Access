from flask import Flask, flash, redirect, render_template, request, session, abort, url_for

from Location_Policy import Location_Policy
from ISE_API import *
from CMX_API import *
from locationbot import get_zones, get_groups, display_zone_policy, change_zone_policy, help, hello
from webexbot import send_spark_get, send_spark_post, send_spark_delete, check_bot, check_webhook

bot_name = ''

if 'WEBEX_BOT_TOKEN' in os.environ:
    WEBEX_BOT_TOKEN = os.environ.get('WEBEX_BOT_TOKEN')

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

    print(WEBEX_BOT_TOKEN)
    print(bot_name)
    print(bot_email)

    check_webhook(WEBEX_URL, headers, webhook_vars)

else:
    WEBEX_BOT_TOKEN = 'None'




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
    # if mac address has not already been blacklisted in the local policy:
    # 1. blacklist it in local policy,
    # 2. blacklist in ISE
    # 3. issue CoA.
    if policy.in_blacklist(mac_address) is None:
        print(ise_get_endpoint_info(ise_server, mac_address))
        policy.blacklist(ise_get_endpoint_info(ise_server, mac_address))
        ise_blacklist_mac(ise_server, mac_address)
        ise_CoA(ise_server, mac_address)
        print("blacklisting ", mac_address)


def unblacklist(mac_address):
    print("mac address: ", mac_address, "policy is already in policy blacklist ->", policy.in_blacklist(mac_address))
    if policy.in_blacklist(mac_address) is not None:
        print("mac_address is already blacklisted in local policy")
        ise_unblacklist_mac(ise_server, policy.in_blacklist(mac_address))
        ise_CoA(ise_server, mac_address)
        policy.unblacklist(mac_address)
        print("unblasklisted ", mac_address)


def mac_action(mac_address, zone, in_out):
    user_groups = ise_get_device_usergroup(ise_server, mac_address)
    user_groups.append("ALL_ACCOUNTS (default)")


    if in_out == "In":
        if policy.zone_exists(zone) is False:
            zone_policy = policy.get_default()
            allow_deny = zone_policy.get("allow_deny")
            group_match = policy.match_default_groups(user_groups)
            #*** CMX call to get all zones & update policy
            print("zone ", zone, "does not exist")
        else:
            zone_policy = policy.get_for_zone(zone)
            allow_deny = zone_policy.get("allow_deny")
            group_match = policy.match_zone_groups(zone, user_groups)
        if group_match:
            print(mac_address, "in user group/s ___", ", matched zone policy: ", allow_deny, user_groups)
        else:
            print(mac_address, "in user group/s ___", ", did not match zone policy: ", allow_deny, user_groups)


        if allow_deny == "allow" and  group_match is False:
            print("blacklist:" + mac_address)
        elif allow_deny == "deny" and  group_match is True:
            print("blacklist")
            blacklist(mac_address)
        else:
            print("unblacklist1: ")
            unblacklist(mac_address)
    else:
        print("default policy applied")
        zone_policy = policy.get_default()
        allow_deny = zone_policy.get("allow_deny")
        group_match = policy.match_default_groups(user_groups)

        if allow_deny == "allow" and  group_match == False:
            print("default blacklist1:")
        elif allow_deny == "deny" and  group_match == True:
            print("default blacklist2")
            blacklist(mac_address)
        else:
            print("default unblacklist1: ")
            unblacklist(mac_address)



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
        in_out = area_json.get("notifications")[0].get("subscriptionName").split()[-1]
        print(mac_address, zone, in_out)
        mac_action(mac_address, zone, in_out)
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

        for n in changed_zones:
            if n["zone_name"] != "default_policy":
                for mac_addr in cmx_get_zonedevices(cmx_server, n["zone_name"]):
                    mac_action(mac_addr, n["zone_name"], "In")
            else:
                for mac_addr in cmx_get_nonzonedevices(cmx_server):
                    mac_action(mac_addr, n["zone_name"], "Out")

        return render_template('changed_policy.html', changed_zones=changed_zones)


@app.route('/bot', methods =['GET', 'POST'])
def bot():

    if request.method == 'GET' :
        print('Hello bot get request')
        message = 'The Location Bot is not running!'

        if bot_name != '':
            message = '<br/><br/>Location Policy Bot is up and running. @mention {0} from Teams <strong>@{0} help</strong> to start!'.format(bot_name)

        return message


    elif request.method == 'POST':

        with open('location_policy.json') as json_file:
            saved_policy = json.load(json_file)
            #print(json.dumps(saved_policy, indent=4))

        ise_groups = ['loc-testing', 'Nurses', 'Doctors', 'Employees', 'ALL_ACCOUNTS (default)', 'GuestType_SocialLogin (default)', 'Accounting', 'HR']

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
                'https://api.ciscospark.com/v1/messages/{}'.format(webhook['data']['id']), headers)
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
                msg = hello(bot_name)
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
                msg, changed_zones = change_zone_policy(policy, error)

                print(json.dumps(changed_zones, indent=4))
                ross_object_function_to_update_policy(changed_zones)

            else:
                msg = "Sorry, but I did not understand your request. Type `Help` to see what I can do"

            if msg != None:
                send_spark_post("https://api.ciscospark.com/v1/messages", headers,
                                {"roomId": webhook['data']['roomId'], "markdown": msg})

    return "true"



if __name__ == "__main__" :

    flask_port = 5050

    print('\n********   Starting up Flask Web...    ********\n\n')

    app.run(host='0.0.0.0', port=flask_port, debug=True)