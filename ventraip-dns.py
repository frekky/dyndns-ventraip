#!/usr/bin/python3
"""
Updates a single DNS record on VentraIP, using public IP retrieved from ipify.org

Copyright (C) 2020 frekky - released under the MIT License
"""

import requests as req
import json
import os
import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'ventraip-dns.conf')

URL_BASE='https://vip.ventraip.com.au/api'
COOKIES_DOMAIN='.vip.ventraip.com.au'

DEBUG=False

def load_config():
    conf = None
    try:
        with open(CONFIG_FILE, "r") as f:
            conf = json.loads(f.read())
    except FileNotFoundError:
        print(f"Config file '{CONFIG_FILE}' does not exist, using empty config")

    if not conf:
        # default config
        conf = {
            'login': {
                '?': 'Enter your plaintext VentraIP username/password',
                'email': '',
                'password': '',
            },
            'record': {
                '?': 'Enter hostname/type of an already-configured DNS record to be updated dynamically',
                'dns_type': 'A',
                'hostname': '',
                'ttl': 60,
                'prio': '',
            },
            'status': {
                '?': "Don't change anything in this section, it will be updated automatically",
                'cookies': {
                    'access_token': '',
                    'vipcontrol_session': '',
                },
                'last_ip': None,
                'last_ip_changed': None,
            },
        }
    
    return conf

def debug_req(r):
    if DEBUG:
        print(r.request.method, r.url, r.status_code)
        print(r.request.headers)
        if r.request.body:
            print('request data:', json.dumps(json.loads(r.request.body)))
        print(r.headers)
        if r.text:
            print('response data:', json.dumps(r.json(), indent=4))
        #breakpoint()

def write_config(conf):
    with open(CONFIG_FILE, "w") as f:
        f.write(json.dumps(conf, indent=4))

def get_ip():
    r = req.get('https://api.ipify.org?format=json')
    if r.status_code == 200:
        data = r.json()
        return data.get('ip', None)
    else:
        return None

def vip_check_token(s):
    r = s.get(f'{URL_BASE}/check-token')
    debug_req(r)
    return r.status_code == 200

def vip_login(s, user, password):
    reqdata = {
        "type": "login",
        "attributes": {
            "email": user,
            "password": password
        }
    }
    r = s.post(f'{URL_BASE}/login', json=reqdata)
    debug_req(r)

    if r.status_code != 200:
        return False
    try:
        data = r.json()['data']
        assert data['type'] == 'access-token'
        token = data['attributes']['token']
        s.cookies.set('access_token', token, domain=COOKIES_DOMAIN)
        s.headers.update({'Authorization': f'Bearer {token}'})
    except (KeyError, AssertionError) as e:
        print(e)
        return False
    return True

def vip_find_domain_id(s, hostname):
    """ Returns ID of domain name which is right-side of given hostname, or None if not found or errors """
    r = s.get(f'{URL_BASE}/domain')
    debug_req(r)

    labels = hostname.split('.')
    if r.status_code != 200:
        return None
    try:
        data = r.json()
        if data['meta']['total'] > data['meta']['per_page']:
            print('Warning: more domain names than displayed on first page, may not find it!')

        for d in data['data']:
            if DEBUG:
                print('Domain:', d)
            assert d['type'] == 'domain'
            domain = d['attributes']['domain']
            dlabels = domain.split('.')
            assert len(dlabels) == 2
            assert len(labels) >= len(dlabels)
            if dlabels == labels[-2:]:
                return d['id']
            
    except (KeyError, AssertionError) as e:
        print(e)

def vip_find_dns_record_id(s, domain_id, hostname, dns_type='A'):
    """ returns ID of DNS record matching hostname and record type """
    assert type(domain_id) == int
    r = s.get(f'{URL_BASE}/domain/{domain_id}/dns')
    debug_req(r)
    if r.status_code != 200:
        return None
    try:
        data = r.json()['data']
        assert data['type'] == 'domain-dns'
        for record in data['attributes']['dns_records']:
            assert record['type'] == 'dns-record'
            if record['attributes']['hostname'] == hostname and record['attributes']['dns_type'] == dns_type:
                return record['id']
    except (KeyError, AssertionError) as e:
        print(e)

def vip_update_dns_record(s, domain_id, record_id, hostname, value, ttl=300, dns_type='A', prio=''):
    assert type(record_id) == int and type(domain_id) == int
    req_data = {
        "type": "dns-record",
        "id": record_id,
        "attributes": {
            "type": dns_type,
            "hostname": hostname,
            "prio": prio,
            "ttl": str(ttl),
            "content": value,
            "id": record_id,
        }
    }
    r = s.put(f'{URL_BASE}/domain/{domain_id}/dns/record/{record_id}', json=req_data)
    debug_req(r)
    return r.status_code == 200

def open_session(conf, check_only=False):
    cc = conf['status']['cookies']
    s = req.Session()

    for k, v in cc.items():
        if v:
            s.cookies.set(k, v, domain=COOKIES_DOMAIN)

    auth = cc['access_token']
    if auth:
        s.headers.update({'Authorization': f'Bearer {auth}'})

    if not vip_check_token(s):
        if not check_only:
            print('Invalid session token, attempting login...')
            if vip_login(s, conf['login']['email'], conf['login']['password']) and vip_check_token(s):
                print(f"Login success")
                cc['access_token'] = s.cookies['access_token']
                cc['vipcontrol_session'] = s.cookies['vipcontrol_session']
            else:
                print('Bad login, giving up.')
                sys.exit(1)
        else:
            print('Invalid session token, will login next time.')
    else:
        print('Existing session access token OK')
    return s


def close_session(conf, sess):
    for x in conf['status']['cookies'].keys():
        conf['status']['cookies'][x] = sess.cookies.get(x, '')
    sess.close()


def main():
    global DEBUG, CONFIG_FILE

    parser = argparse.ArgumentParser(description='Update VentraIP DNS record with my public IP address')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--config', nargs=1)
    args = parser.parse_args()

    DEBUG = args.debug
    if args.config:
        CONFIG_FILE = args.config[0]

    conf = load_config()

    if not conf['login']['email']:
        write_config(conf)
        print(f'Generated empty "{CONFIG_FILE}", configure and then run again.')
        sys.exit(0)

    my_ip = get_ip()
    if not my_ip:
        print('Error getting IP')
        sys.exit(1)
    
    print(f'My IP is {my_ip}')
    status = conf['status']
    prev_ip = status['last_ip']
    do_update = (prev_ip != my_ip) or args.force
    if do_update:
        now = datetime.now()
        if prev_ip:
            last_change = datetime.fromisoformat(status['last_ip_changed'])
            age = now - last_change
            print(f'IP changed to {my_ip} from {prev_ip} (age {str(age)})')
        status['last_ip_changed'] = now.isoformat()
        status['last_ip'] = my_ip
    else:
        print(f"IP address unchanged since {status['last_ip_changed']}")

    s = open_session(conf, check_only = not do_update)
    if do_update:
        hostname = conf['record']['hostname']
        dom_id = vip_find_domain_id(s, hostname)
        if not dom_id:
            print(f"Unable to find domain ID for hostname '{hostname}', check {CONFIG_FILE} and your domains on VentraIP")
            # login OK so save the config
            write_config(conf)
            sys.exit(1)
        print(f"Found domain id '{dom_id}'")
        
        #if not status['record_id']:
        dns_id = vip_find_dns_record_id(s, dom_id, hostname)
        if not dns_id:
            print(f"Unable to find existing DNS record for hostname '{hostname}', make sure it has been created already")
        print(f"Found dns record id '{dns_id}'")

        # finally, do the magic
        ret = vip_update_dns_record(s, dom_id, dns_id, hostname, my_ip,
                ttl=conf['record']['ttl'], dns_type=conf['record']['dns_type'], prio=conf['record']['prio'])
        if ret:
            print('DNS update OK')
    close_session(conf, s)

    write_config(conf)

if __name__ == '__main__':
    main()