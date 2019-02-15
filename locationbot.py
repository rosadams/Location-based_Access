
import re


def help():
    return "Sure! I can help. Below are the commands that I understand:<br/>" \
            "`Help` - I will display what I can do.<br/>" \
            "`Hello` - I will display my greeting message<br/>" \
            "`Zones` - I will display all the zones in the policy database <br/>" \
            "`Groups` - I will displace all the ISE groups that can be used in a Zone policy <br/>" \
            "`Display [Zone Name]` - I will display the policy for [Zone Name] <br/>" \
            "`Change [Zone Name] policy=[policy] groups=group1, group2, group3` <br/>" \
            "`[ ]` represent variables. <br/>"



def hello(bot_name):
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
            groups = ', '.join(zone['zone_policy']['group_list'])
            message += ('**Groups**: ' + groups + '<br/>')
    return message

def change_zone_policy(policy, error):

    if error!='':
        return error


    '''
    Review Regex at: https://regex101.com/

    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    1st Capturing Group ([a-zA-Z0-9>\s]*[A-Za-z0-9])
    --> 1st capturing group captures the zone <--
    Match a single character present in the list below [a-zA-Z0-9>\s]*
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    a-z a single character in the range between a and z (case sensitive)
    A-Z a single character in the range between A and Z (case sensitive)
    0-9 a single character in the range between 0 and 9 (case sensitive)
    > matches the character > literally (case sensitive)
    \s matches any whitespace character (equal to [\r\n\t\f\v ])
    Match a single character present in the list below [A-Za-z0-9]
    --> This is included so that our first group ends on a non-whitespace boundary <--
    A-Z a single character in the range between A and Z (case sensitive)
    a-z a single character in the range between a and z (case sensitive)
    0-9 a single character in the range between 0 and 9 (case sensitive)
    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    2nd Capturing Group (policy\s*=\s*[allowdenyAD]*)
    --> 2nd capturing group captures the allow\deny policy <--
    policy matches the characters policy literally (case sensitive)
    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    = matches the character = literally (case sensitive)
    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    Match a single character present in the list below [allowdenyAD]*
    --> This should match allow, deny, Allow, Deny <--
    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    3rd Capturing Group (groups\s*=\s*[a-zA-Z_\s\(\),]*)
    --> 3rd capturing group captures the groups <--
    groups matches the characters groups literally (case sensitive)
    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    * Quantifier — Matches between zero and unlimited times, as many times as possible, giving back as needed (greedy)
    = matches the character = literally (case sensitive)
    \s* matches any whitespace character (equal to [\r\n\t\f\v ])
    Match a single character present in the list below [a-zA-Z_\s\(\),]*
    '''

    regex_alternate = r"\s*([\w>\s]+[\w])\s+(policy\s*=\s*[allowdenyAD]+)\s+(groups\s*=\s*[\w\s\(\),]+)"

    regex = r"\s*([a-zA-Z0-9>\s]*[a-zA-Z0-9])\s*(policy\s*=\s*[allowdenyAD]*)\s*(groups\s*=\s*[a-zA-Z_\s\(\),-]*)"
    print(policy)
    policy_split = re.search(regex, policy)
    zone = policy_split.group(1)
    policy_msg = policy_split.group(2)
    groups_msg = policy_split.group(3)
    print(zone)
    print(policy_msg)
    print(groups_msg)
    policy_msg = policy_msg.split('=')[1].strip()
    groups_msg = groups_msg.split('=')[1]
    message = '**Policy was changed for zone**: {}<br/>'.format(zone)
    message += ('**Policy**: ' + policy_msg + '<br/>')
    message += ('**Groups**: ' + groups_msg + '<br/>')

    groups_msg = groups_msg.split(',')
    for group_index in range(len(groups_msg)):
        groups_msg[group_index]=groups_msg[group_index].strip()

    changed_zones = {'zone_name' : zone, 'zone_policy' : {'allow_deny' : policy_msg, 'group_list' : groups_msg}}

    return message, changed_zones

