#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Copyright (c) 2012-2013, Meangrape Incorporated
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Command-line tool for managing popup servers
"""

import argparse
import os
import os.path
import sys
import time

import boto
import boto.ec2

from datetime import datetime

from boto.ec2.connection import EC2Connection

import PopupServer


def _gather_instances(conn, args):
    """Try and locate popup EC2 instances. The three options are by: userid, "client" (which is really an arbitrary string),
    tag (which is a short random string associated with a specific popup

    Returns a list of EC2 instance ids, unique tags, and (if applicable) the manifest files
    """
    reservations = conn.get_all_instances()
    instances = [ i for r in reservations for i in r.instances ]
    stop_these = []
    unique_tags = []
    manifests = []
    for instance in instances:
        try:
            if instance.tags['owner'] == args.iam:
                if args.all:
                    stop_these.append(instance.id)
                    unique_tags.append(instance.tags['popup_id'])
                    manifests.append("%s-%s-%s" % (instance.tags['start_date'], instance.public_dns_name, instance.tags['popup_id']))
                    continue
                if args.client:
                    try:
                        if instance.tags['client'] == args.client:
                            stop_these.append(instance.id)
                            unique_tags.append(instance.tags['popup_id'])
                            continue
                    except KeyError:
                        continue
                if args.tag:
                    if instance.tags['popup_id'] == args.tag:
                        stop_these.append(instance.id)
                        unique_tags.append(instance.tags['popup_id'])
        except KeyError:
            continue
    return (stop_these, unique_tags, manifests)


def create_popup(conn, args):
    print("Creating EC2 instance...")
    server = PopupServer.PopupServer(conn, args)
    print(server.connection_string)


def destroy_popup(conn, args):
    """Terminate EC2 popup instance(s) plus associated resources (keypair, security group).
    Also remove local manifest files and ssh keys.
    """
    HOME = os.path.expanduser('~')
    instance_ids, unique_tags, manifests = _gather_instances(conn, args)
    print("Terminating %s" % instance_ids)
    for id in instance_ids:
        conn.terminate_instances(instance_ids=[id])
        wait_for_state(conn, id, u'terminated')
    for tag in unique_tags:
        name = "popup-%s-%s" % (args.iam, tag)
        print("...delete security group")
        conn.delete_security_group(name)
        print("...delete keypair")
        conn.delete_key_pair(name)
        print("...cleanup local manifest and key")
        os.remove("%s/.popup/keys/%s" % (HOME, name))
    for manifest in manifests:
        os.remove("%s/.popup/manifests/%s" % (HOME, manifest))
    #XXX Remove .popup/configs/ssh_configs


def inventory(conn, args):
    """Queries EC2 for running instances created by this program
    It should really xref against the manifests directory
    """
    reservations = conn.get_all_instances()
    instances = [ i for r in reservations for i in r.instances ]
    for instance in instances:
        if instance.state != u'terminated':
            try:
                if instance.tags['owner'] == args.iam:
                    if args.detailed:
                        print "instance id: %s" % instance.id
                        print "public DNS: %s" % instance.public_dns_name
                        print "state: %s" % instance.state
                        print "launch time: %s" % instance.launch_time
                    for tag in ['start_date', 'client', 'owner', 'popup_id']:
                        try:
                            print "%s: %s" % (tag, instance.tags[tag])
                        except KeyError:
                            continue
            except KeyError:
                continue


def stop_popup(conn, args):
    instance_ids, unique_tags, _ = _gather_instances(conn, args)
    print("Stopping %s" % instance_ids)
    conn.stop_instances(instance_ids=instance_ids, force=args.force)


def wait_for_state(conn, id, desired):
    """ If we don't wait for the instance to terminate, we can't delete the security group
    It's ugly.
    """
    reservations = conn.get_all_instances(filters={'instance-id': id})
    instance = reservations[0].instances[0]
    state = instance.state
    print("...waiting for instance %s to terminate" % id)
    while True:
        if state == desired:
            return True
        else:
            sys.stdout.write('.')
            time.sleep(10)
            instance.update()


def get_parser():
    _ROOT = os.path.abspath(os.path.dirname(__file__))
    IAM_ID = os.environ.get('IAM_ID') or os.environ['USER']

    parser = argparse.ArgumentParser(prog='popup', description='Manage EC2 popup instances', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--iam', type=str, metavar='IAMID', 
        help='Your IAM id. We attempt to read an IAM_ID environemnt variable and fallback to your username. This is the primary key used to identify AWS resources belonging to you',
        default=IAM_ID)
    parser.add_argument('-v', '--version', action='store_true')
    subparsers = parser.add_subparsers()
    parser_create = subparsers.add_parser('create', help='Create a popup group (instance, keypair, security group)')
    parser_create.add_argument('-s', '--size', type=str, help='Instance size (micro or small)', default='micro')
    parser_create.add_argument('-c', '--client', type=str, help="Tag instance with this client's name (an arbitrary string)")
    parser_create.add_argument('-l', '--lifetime', type=int, help='Will stop in this many hours', default=12)

    playbook_dir = os.path.join(_ROOT, 'playbooks')
    playbooks = [name for name in os.listdir(playbook_dir) if os.path.isdir("%s/%s" % (name, playbook_dir))]
    parser_create.add_argument('-p', '--playbooks', nargs='*', choices=playbooks, help='Setup the selected features', default=['mosh', 'openvpn', 'tmux'])
    parser_create.set_defaults(func=create_popup)

    parser_destroy = subparsers.add_parser('destroy', help='Destroy a popup group and associated resources')
    destroy_group = parser_destroy.add_mutually_exclusive_group(required=True)
    destroy_group.add_argument('-a', '--all', action='store_true', help='Delete all of your popups and resources')
    destroy_group.add_argument('-c', '--client', type=str, help='Delete all of your instances with this client name')
    destroy_group.add_argument('-t', '--tag', type=str, help='Unique resource tag to be deleted')
    parser_destroy.set_defaults(func=destroy_popup)
    
    parser_inventory = subparsers.add_parser('inventory', help='List popups you have running in AWS')
    parser_inventory.add_argument('-d', '--detailed', action='store_true', help='Provide additional EC2 specific information')
    parser_inventory.set_defaults(func=inventory)
    
    parser_stop = subparsers.add_parser('stop', help='Stop running instances')
    parser_stop.add_argument('-f', '--force', action='store_true', help='Force shutdown', default=False)
    stop_group = parser_stop.add_mutually_exclusive_group(required=True)
    stop_group.add_argument('-a', '--all', action='store_true', help='Stop (not terminate) all of your instances')
    stop_group.add_argument('-c', '--client', type=str, help='Stop (not terminate) all instances for this client')
    stop_group.add_argument('-t', '--tag', type=str, help='Unique resource tag to be stopped')
    parser_stop.set_defaults(func=stop_popup)
    return parser

def main():
    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    conn = EC2Connection()
    parser = get_parser() 
    args = parser.parse_args()
    if args.version:
        print """
popup version 0.1.0
Copyright (c) 2012-13, Meangrape Incorporated
All rights reserved.

License: Simplified BSD <http://github.com/jayed/popup/LICENSE>


"""
    args.func(conn, args)


if __name__ == "__main__":
    main()
