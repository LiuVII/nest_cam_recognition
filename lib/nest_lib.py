import json
import urllib
import urllib2

import settings

nest_auth_url = settings.nest_auth_url
nest_access_token_url = settings.nest_access_token_url
nest_api_root_url = settings.nest_api_root_url
nest_tokens_path = settings.nest_tokens_path
nest_api_url = settings.nest_api_url

product_id = settings.product_id
product_secret = settings.product_secret

# Custom implementation
def get_camera_url(url=nest_api_url):
    return "{0}/devices/cameras/".format(url)

def get_snapshot_url(device_id, url=nest_api_url):
    return "{0}/devices/cameras/{1}/snapshot_url".format(url, device_id)

def get_action_url(device_id, url=nest_api_url):
    return "{0}/devices/cameras/{1}/last_event".format(url, device_id)

def get_camera_id(token):
    try:
        cameras = list(get_data(token, get_camera_url())["results"].keys())
        return cameras[0]
    except:
        print('No cameras were found')
        return ""

def get_action_time(token, device_id):
    return get_data(token, get_action_url(device_id))["results"]["start_time"]

# Nest provided implementation

def get_url():
    return authorization_url()


def get_device(token, device_type, device_id):
    api_path = "{0}/devices/{1}/{2}".format(nest_api_url, device_type, device_id)
    data = get_data(token, api_path)
    device = data.get("results") if data else None
    return device


def get_data(token, api_endpoint=nest_api_url):
    headers = {
        'Authorization': "Bearer {0}".format(token),
    }
    req = urllib2.Request(api_endpoint, None, headers)
    try:
        response = urllib2.urlopen(req)

    except urllib2.HTTPError as err:
        # send error message to client
        json_err = err.read()
        print "get_data error occurred: ", json_err
        raise apierr_from_json(err.code, json_err)

    except Exception as ex:
        # send error message to client
        print "Error: ", ex
        raise apierr_from_msg(500, "An error occurred connecting to the Nest API.")

    data = json.loads(response.read())

    return {"results": data}


def get_access(authorization_code):
    return get_access_token(authorization_code)
    #token = get_access_token(authorization_code)
    #store_token(token)


def remove_access(auth_revoked=False):
    """ Product has correctly implemented deauth API when disconnecting or logging out.

     When the user requests to log out, deauthorize their token using the Nest
     deauthorization API then destroy their local session and cookies.
     See https://goo.gl/f2kfmv for more information.
    """
    token = fetch_token()
    if token:
        if not auth_revoked:
            # delete user token using the Nest API, if not already revoked
            try:
                delete_access_token(token)
            except Exception as ex:
                print "Error deleting access token: ", ex

        # delete token and user data from persistent storage and cache
        delete_cached_token()

    else:
        print 'Not signed in.'


def get_token():
    return fetch_token()


def fetch_token():
    if session is not None and "token" in session:
        return session["token"]
    return None


def store_token(token):
    session["token"] = token


def delete_cached_token():
    session["token"] = None


def get_access_token(authorization_code):
    data = urllib.urlencode({
        'client_id': product_id,
        'client_secret': product_secret,
        'code': authorization_code,
        'grant_type': 'authorization_code'
    })
    req = urllib2.Request(nest_access_token_url, data)
    response = urllib2.urlopen(req)
    data = json.loads(response.read())
    return data['access_token']


def delete_access_token(token):
    path = nest_tokens_path + token
    req = urllib2.Request(nest_api_root_url + path, None)
    req.get_method = lambda: "DELETE"
    response = urllib2.urlopen(req)
    resp_code = response.getcode()
    print "deleted token, response code: ", resp_code
    return resp_code


def authorization_url():
    query = urllib.urlencode({
        'client_id': product_id,
        'state': 'STATE'
    })
    return "{0}?{1}".format(nest_auth_url, query)