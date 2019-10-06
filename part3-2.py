import argparse
import os
import time
import requests
from pprint import pprint
import json
from six.moves import input
from __main__ import *

#credentials, project = google.auth.default()
#service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
compute = service
#
# Stub code - just lists all instances
#
# [START list_instances]
def list_instances(compute, project, zone):
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items'] if 'items' in result else None
# [END list_instances]

# [START create_instance]
def create_instance(compute, project, zone, name):
    # Get the latest Debian Jessie image.
    image_response = compute.images().getFromFamily(
        project='ubuntu-os-cloud', family='ubuntu-1804-lts').execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/n1-standard-1" % zone
    startup_script1 = open(
        os.path.join(
            os.path.dirname(__file__), 'startup-script1.sh'), 'r').read()

    config = {
        'name': name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],
        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': startup_script1
            }]
        }
    }
    return service.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()
# [END create_instance]


# [START create_firewall]
def create_firewall(project):
    st = 'projects/green-entity-251200/global/firewalls/allow-5000'
    st1 = 'projects/green-entity-251200/global/networks/default'
    firewall_body ={
                    # "kind": "compute#firewall",
                    "name": "allow-5000",
                    # "selfLink": st,
                    # "network": st1,
                    "direction": "INGRESS",
                    "priority": 1000,
                    "targetTags": [
                                    "allow-5000"
                                  ],
                     "allowed": [
                                {
                                    "IPProtocol": "tcp",
                                    "ports": [
                                                "5000"
                                             ]
                                }
                                ],
                    "sourceRanges": [
                                        "0.0.0.0/0"
                                    ]
                    }

    request = service.firewalls().insert(project=project, body=firewall_body)
    return request.execute()
# [END create_firewall]


# [START get_info]
def get_info(project, zone, instance):
    request = service.instances().get(project=project, zone=zone,
                                      instance=instance)
    response = request.execute()
    return response
# [END get_info]


# [START set_tags]
def set_tags(project, zone, instance, fingerprint):
    tags_body = {
                    "items": [
                                "allow-5000"
                             ],
                    "fingerprint": fingerprint
                }
    request = service.instances().setTags(project=project, zone=zone,
                                          instance=instance, body=tags_body)
    return request.execute()
# [END set_tags]


# [START delete_instance]
def delete_instance(compute, project, zone, name):
    return compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()
# [END delete_instance]


# [START wait_for_operation]
def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)
# [END wait_for_operation]


# [START run]
def main(project, zone, instance_name, wait=True):
    # compute = googleapiclient.discovery.build('compute', 'v1')
    #compute= service
    print('Creating instance.')
    operation = create_instance(compute, project, zone, instance_name)
    wait_for_operation(compute, project, zone, operation['name'])
    flag = 1
    request = service.firewalls().list(project=project)
    while request is not None:
        response = request.execute()
        for firewall in response['items']:
        # TODO: Change code below to process each `firewall` resource:
            if firewall["name"] == "allow-5000" :
                print(firewall["name"])
                flag = 0
                break

        request = service.firewalls().list_next(previous_request=request, previous_response=response)
    if flag == 1 :
        operation= create_firewall(project) 
        wait_for_operation(compute, project, zone, operation['name'])

    instances = list_instances(compute, project, zone)

    print('Instances in project %s and zone %s:' % (project, zone))
    response = get_info(project, zone, instance_name)
    fingerprint = response["tags"]["fingerprint"]
    print(fingerprint)
    publicIP = response["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
    print(publicIP)
    operation= set_tags(project, zone, instance_name, fingerprint)
    wait_for_operation(compute, project, zone, operation['name'])
    for instance in instances:
        print(' - ' + instance['name'])
    # if wait:
    #    input()

    # print('Deleting instance.')

    # operation = delete_instance(compute, project, zone, instance_name)
    # wait_for_operation(compute, project, zone, operation['name'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project_id', help='Your Google Cloud project ID.')
    parser.add_argument(
        '--zone',
        default='us-west1-b',
        help='Compute Engine zone to deploy to.')
    parser.add_argument(
        '--name', default='demo-instance2', help='New instance name.')

    args = parser.parse_args()

    main(args.project_id, args.zone, args.name)
# [END run]