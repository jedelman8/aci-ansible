#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: aci_fabric_inventory
short_description: Get fabric topology data on Cisco ACI fabrics
description:
- Get fabric topology data on Cisco ACI fabrics.
author:
- Swetha Chunduri (@schunduri)
- Dag Wieers (@dagwieers)
- Jacob McGill (@jmcgill298)
version_added: '2.4'
requirements:
    - ACI Fabric 1.0(3f)+
options:
    action:
        description:
            - post or get
    node_id:
        description:
            - ID of the node whose details are being fetched
        required: true
    command:
        description:
            - Type of information to retrieve
        default: all
        choices: ['fantray','interfaces','power-supplies','firmware','supervisor-module','linecard-module','all']
    level:
        description:
            - MO query or subtree query
        default: brief
        choices: ['brief','detail']
    filename:
        description:
           - Name of the output file[.txt] to store the response
    host:
        description:
            - IP Address or hostname of APIC resolvable by Ansible control host
        required: true
    username:
        description:
            - Username used to login to the switch
        required: true
        default: 'admin'
    password:
        description:
            - Password used to login to the switch
        required: true
    protocol:
        description:
            - Dictates connection protocol to use
        default: https
        choices: ['http', 'https']
'''

EXAMPLES = r'''
- aci_fabric_inventory:
    node_id : "{{ node_id }}"
    level: "{{ level }}"
    command: "{{ command }}"
    filename: "{{ filename }}"
    host: "{{ host }}"
    username: "{{ user }}"
    password: "{{ pass }}"
    protocol: "{{ protocol }}"
'''
import socket
import json
import requests

from ansible.module_utils.basic import AnsibleModule


mo_class_value = {
    'fantray': 'eqptFt',
    'power-supplies': 'eqptPsu',
    'supervisor-module': 'eqptSupC',
    'linecard-module': 'eqptLC',
    'interfaces': 'ethpmPhysIf',
    'firmware': 'firmwareRunning'
}
cntrlr_mo_class_value = {
    'interfaces': 'cnwPhysIf',
    'firmware': 'ethpmPhysIf'
}


def request_get(level, mo_class, node_id):
    if level == 'detail':
        get_uri = 'api/node/class/topology/pod-1/node-' + node_id + '/' + mo_class + '.json?query-target=children'
    else:
        get_uri = 'api/node/class/topology/pod-1/node-' + node_id + '/' + mo_class + '.json'
    return get_uri


def get_mo_class(command, node_id):
    if (command == 'interfaces' or command == 'firmware') and len(node_id) == 1:
        mo_class = cntrlr_mo_class_value.get(command)
    else:
        mo_class = mo_class_value.get(command)
    return mo_class


def write2file(data, filename):
    if filename != "None":
        with open(filename + '.txt', 'w') as output_file:
            output_file.write(json.dumps(data, sort_keys=True, indent=4))
    else:
        filename = 'Output filename not mentioned.'


def main():
    ''' Ansible module to take all the parameter values from the playbook '''

    module = AnsibleModule(
        argument_spec=dict(
            node_id=dict(type='int'),
            command=dict(choices=['fantray', 'interfaces', 'power-supplies', 'firmware', 'supervisor-module', 'linecard-module', 'nodes', 'all'],
                         default='all'),
            level=dict(choices=['brief', 'detail'], default='brief'),
            filename=dict(type='str', required=False),
            host=dict(required=True),
            username=dict(type='str', default='admin'),
            password=dict(type='str'),
            protocol=dict(choices=['http', 'https'], default='https'),
        ),
        supports_check_mode=False,
    )

    host = socket.gethostbyname(module.params['host'])
    username = module.params['username']
    password = module.params['password']
    protocol = module.params['protocol']

    level = module.params['level']
    filename = module.params['filename']
    node_id = module.params['node_id']
    node_id = str(node_id)
    command = module.params['command']
    response = []
    mo_class = get_mo_class(command, node_id)

    apic = '{0}://{1}/'.format(protocol, host)
    auth = dict(aaaUser=dict(attributes=dict(name=username,
                pwd=password)))
    url = apic + 'api/aaaLogin.json'

    authenticate = requests.post(url, data=json.dumps(auth), timeout=2,
                                 verify=False)

    if authenticate.status_code != 200:
        module.fail_json(msg='could not authenticate to apic',
                         status=authenticate.status_code,
                         response=authenticate.text)

    if command == 'nodes':
        get_uri = 'api/node/class/topSystem.json'
    elif command == 'all':
        for key in mo_class_value:
            command = key
            mo_class = get_mo_class(key, node_id)
            mo_class = str(mo_class)
            get_uri = request_get(level, mo_class, node_id)
            get_url = apic + get_uri
            req = requests.get(get_url, cookies=authenticate.cookies, verify=False)
            resp = req.text
            status = req.status_code
            response.append(json.loads(resp))
    else:
        get_uri = request_get(level, mo_class, node_id)
        get_url = apic + get_uri
        req = requests.get(get_url, cookies=authenticate.cookies, verify=False)
        resp = req.text
        status = req.status_code
        response = json.loads(resp)

    write2file(response, filename)
    changed = False
    if req.status_code == 200:
        changed = True
    else:
        changed = False
        module.fail_json(msg='error issuing api request',
                         response=response, status=status)

    results = {}
    results['status'] = status
    results['response'] = response
    results['changed'] = changed

    module.exit_json(**results)


if __name__ == '__main__':
    main()
