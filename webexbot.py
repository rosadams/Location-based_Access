import sys
import requests
import json

def check_webhook(WEBEX_URL, headers, webhook_vars):

    webhook_name = webhook_vars['webhook_name']
    resources = webhook_vars['resources']
    event = webhook_vars['event']
    bot_route = webhook_vars['bot_route']
    #webhook_vars = {'webhook_name' : webhook_name, 'resources' : resources, 'event' : event, 'bot_route' : bot_route }



    url = WEBEX_URL + '/webhooks'

    ngrok_url = requests.get(
        "http://127.0.0.1:4040/api/tunnels", headers={"Content-Type": "application/json"}).json()

    for urls in ngrok_url["tunnels"]:
        if "https://" in urls['public_url']:
            target_url = urls['public_url']
            address = urls['config']['addr']
            print('Ngrok target_url is:', target_url)
            print('Ngrok address is:', address)

    webhook_js = send_spark_get(url, headers,js=True)
    print('webhook_js initial check is: ', webhook_js)

    items = webhook_js['items']

    if len(items) > 0 :
        #print(items)
        for webhook in range(len(items)) :
            if ((items[webhook]['name'] == webhook_name) and (items[webhook]['resource'] in resources)):
                #print('Webhook name =', items[webhook]['name'])
                #print('resource =', items[webhook]['resource'] )
                send_spark_delete(url + '/' + items[webhook]['id'], headers)


    for webhook in resources :
        payload = {'name': webhook_name, 'targetUrl': target_url + bot_route, 'resource' : webhook, 'event' : event}
        webhook_js = send_spark_post(url, headers, data=payload, js=True)
        print(webhook_js)

    return


def send_spark_get(url, headers, payload=None, js=True):

    if payload == None:
        request = requests.get(url, headers=headers)
    else:
        request = requests.get(url, headers=headers, params=payload)
    if js == True:
        request= request.json()
    return request


def send_spark_delete(url, headers, js=False):

  request = requests.delete(url, headers=headers)
  if js != False:
    request = request.json()
  return request



def send_spark_post(url, headers, data, js=True):

  request = requests.post(url, json.dumps(data), headers=headers)
  if js:
    request = request.json()
  return request


def check_bot(WEBEX_URL, headers):

    url = WEBEX_URL + '/people/me'

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

