
import json
import logging
import sys
import os
import random
import string
import time
import urllib
import json

with open('sites.json') as f:
    data = json.load(f)

unifi_site_list = 'a'
live_mode = True
log = logging.getLogger(__name__)
PYTHON_VERSION = sys.version_info[0]


def pw_gen(size=16, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
  return ''.join(random.choice(chars) for _ in range(size))


try:
    # Ugly hack to force SSLv3 and avoid
    # urllib2.URLError: <urlopen error [Errno 1] _ssl.c:504:
    # error:14077438:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error>
    import _ssl
    _ssl.PROTOCOL_SSLv23 = _ssl.PROTOCOL_TLSv1
except:
    pass

try:
    # Updated for python certificate validation
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

import sys
PYTHON_VERSION = sys.version_info[0]

if PYTHON_VERSION == 2:
    import cookielib
    import urllib2
elif PYTHON_VERSION == 3:
    import http.cookiejar as cookielib
    import urllib3
    import ast

import json
import logging
import urllib

class Controller:

    """Interact with a UniFi controller.

    Uses the JSON interface on port 8443 (HTTPS) to communicate with a UniFi
    controller. Operations will raise unifi.controller.APIError on obvious
    problems (such as login failure), but many errors (such as disconnecting a
    nonexistant client) will go unreported.

    >>> from unifi.controller import Controller
    >>> c = Controller('192.168.1.99', 'admin', 'p4ssw0rd')
    >>> for ap in c.get_aps():
    ...     print 'AP named %s with MAC %s' % (ap['name'], ap['mac'])
    ...
    AP named Study with MAC dc:9f:db:1a:59:07
    AP named Living Room with MAC dc:9f:db:1a:59:08
    AP named Garage with MAC dc:9f:db:1a:59:0b

    """

    def __init__(self, host, username, password, port=8443, version='v4', site_id='default'):
        """Create a Controller object.

        Arguments:
            host     -- the address of the controller host; IP or name
            username -- the username to log in with
            password -- the password to log in with
            port     -- the port of the controller host
            version  -- the base version of the controller API [v2|v3|v4]
            site_id  -- the site ID to connect to (UniFi >= 3.x)

        """

        self.host = host
        self.port = port
        self.version = version
        self.username = username
        self.password = password
        self.site_id = site_id
        self.url = 'https://' + host + ':' + str(port) + '/'
        self.api_url = self.url + self._construct_api_path(version)



        cj = cookielib.CookieJar()
        if PYTHON_VERSION == 2:
            self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        elif PYTHON_VERSION == 3:
            self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        self._login(version)

    def __del__(self):
        if self.opener != None:
            self._logout()

    def _jsondec(self, data):
        if PYTHON_VERSION == 3:
            data = data.decode()
        obj = json.loads(data)
        if 'meta' in obj:
            if obj['meta']['rc'] != 'ok':
                raise APIError(obj['meta']['msg'])
        if 'data' in obj:
            return obj['data']
        return obj

    def _read(self, url, params=None):
        if PYTHON_VERSION == 3:
            if params is not None:
                params = ast.literal_eval(params)
                #print (params)
                params = urllib.parse.urlencode(params)
                params = params.encode('utf-8')
                res = self.opener.open(url, params)
            else:
                res = self.opener.open(url)
        elif PYTHON_VERSION == 2:
            res = self.opener.open(url, params)
        return self._jsondec(res.read())

    def _construct_api_path(self, version):
        """Returns valid base API path based on version given

           The base API path for the URL is different depending on UniFi server version.
           Default returns correct path for latest known stable working versions.

        """

        V2_PATH = 'api/'
        V3_PATH = 'api/s/' + self.site_id + '/'

        if(version == 'v2'):
            return V2_PATH
        if(version == 'v3'):
            return V3_PATH
        if(version == 'v4'):
            return V3_PATH
        else:
            return V2_PATH

    def _login(self, version):


        params = {'username': self.username, 'password': self.password}
        login_url = self.url

        if version == 'v4':
            login_url += 'api/login'
            params = json.dumps(params)
        else:
            login_url += 'login'
            params.update({'login': 'login'})
            if PYTHON_VERSION is 2:
                params = urllib.urlencode(params)
            elif PYTHON_VERSION is 3:
                params = urllib.parse.urlencode(params)

        if PYTHON_VERSION is 3:
            params = params.encode("UTF-8")
        time_check = 0
        while time_check < 10:
            time_check += 1
            try:
              self.opener.open(login_url, params).read()
            except Exception as e:
              print e
              print login_url
              print "trying to log in again"
              time.sleep(1)

    def _logout(self):

        try:
          self.opener.open(self.url + 'logout').read()
        except:
          print "couldnt log out... oh well"

    def get_alerts(self):
        """Return a list of all Alerts."""

        return self._read(self.api_url + 'list/alarm')

    def get_alerts_unarchived(self):
        """Return a list of Alerts unarchived."""

        js = json.dumps({'_sort': '-time', 'archived': False})
        params = urllib.urlencode({'json': js})
        return self._read(self.api_url + 'list/alarm', params)

    def get_statistics_last_24h(self):
        """Returns statistical data of the last 24h"""

        return self.get_statistics_24h(time())

    def get_statistics_24h(self, endtime):
        """Return statistical data last 24h from time"""

        js = json.dumps(
            {'attrs': ["bytes", "num_sta", "time"], 'start': int(endtime - 86400) * 1000, 'end': int(endtime - 3600) * 1000})
        params = urllib.urlencode({'json': js})
        return self._read(self.api_url + 'stat/report/hourly.system', params)

    def get_events(self):
        """Return a list of all Events."""

        return self._read(self.api_url + 'stat/event')

    def get_aps(self):
        """Return a list of all AP:s, with significant information about each."""

        #Set test to 0 instead of NULL
        params = json.dumps({'_depth': 2, 'test': 0})
        return self._read(self.api_url + 'stat/device', params)

    def get_clients(self):
        """Return a list of all active clients, with significant information about each."""

        return self._read(self.api_url + 'stat/sta')

    def get_users(self):
        """Return a list of all known clients, with significant information about each."""

        return self._read(self.api_url + 'list/user')

    def get_user_groups(self):
        """Return a list of user groups with its rate limiting settings."""

        return self._read(self.api_url + 'list/usergroup')

    def get_wlan_conf(self):
        """Return a list of configured WLANs with their configuration parameters."""

        return self._read(self.api_url + 'list/wlanconf')

    def _run_command(self, command, params={}, mgr='sitemgr'):

        params.update({'cmd': command})
        if PYTHON_VERSION == 2:
            return self._read(self.api_url + 'cmd/' + mgr, urllib.urlencode({'json': json.dumps(params)}))
        elif PYTHON_VERSION == 3:
            return self._read(self.api_url + 'cmd/' + mgr, urllib.parse.urlencode({'json': json.dumps(params)}))

    def _mac_cmd(self, target_mac, command, mgr='stamgr'):

        params = {'mac': target_mac}
        self._run_command(command, params, mgr)

    def block_client(self, mac):
        """Add a client to the block list.

        Arguments:
            mac -- the MAC address of the client to block.

        """

        self._mac_cmd(mac, 'block-sta')

    def unblock_client(self, mac):
        """Remove a client from the block list.

        Arguments:
            mac -- the MAC address of the client to unblock.

        """

        self._mac_cmd(mac, 'unblock-sta')

    def disconnect_client(self, mac):
        """Disconnect a client.

        Disconnects a client, forcing them to reassociate. Useful when the
        connection is of bad quality to force a rescan.

        Arguments:
            mac -- the MAC address of the client to disconnect.

        """

        self._mac_cmd(mac, 'kick-sta')

    def restart_ap(self, mac):
        """Restart an access point (by MAC).

        Arguments:
            mac -- the MAC address of the AP to restart.

        """

        self._mac_cmd(mac, 'restart', 'devmgr')

    def delete_site(self, site_id):
        cmd = 'delete-site'
        js = {"site": site_id}
        r = self._run_command(cmd, params=js)

    def get_sites(self):
        res = self.opener.open(self.url + '/api/self/sites')
        return self._jsondec(res.read())

c = Controller('unifi.net', 'user', 'pass')
for row in data["data"]:
    if row["desc"] == "bad-site":
        print row
        c.delete_site(row["_id"])
