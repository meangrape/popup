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
Handles the actual creation and logging of popup AMIs
"""

import base64
import os
import sys
import time

from datetime import datetime


class PopupServer():
    def __init__(self, conn, args):
        """We use 2 different AMIs based on instance size.
        Both images are 64-bit ubuntu 12.10 in us-east-1
        """
        self.args = args
        self.conn = conn
        self.connection_string = None
        self.date = str(datetime.date(datetime.now())).replace('-','')
        self.home = os.path.expanduser('~')
        self.instance = None
        self.kp = None
        self.sg = None
        self.unique_tag = base64.urlsafe_b64encode(os.urandom(6))
        self.name_tag = "popup-%s-%s" % (args.iam, self.unique_tag)
        self.size = self.args.size
        if self.size == "micro":
            self.size = "t1.micro"
            self.ami = "ami-7539b41c"
        if self.size == "small":
            self.size = "m1.small"
            self.ami = "ami-9b3db0f2"
        sys.exit()
        self.image = self.conn.get_all_images(self.ami)
        self.start()

    def _create_key_pair(self):
        self.kp = self.conn.create_key_pair(self.name_tag)
        with open('$s/.popup/keys/%s.pem' % (self.home, self.kp.name), 'wb') as f:
            f.write(self.kp.material)
            os.chmod(f.name, 0600)
        
    def _create_security_group(self):
        self.sg = self.conn.create_security_group(self.name_tag, "Popup OpenVPN for %s (%s)" % (self.args.iam, self.date))
        # SSH, OpenVPN, Mosh, Tor, HTTP/S
        # XXX Configure this in the playbooks (or next to the playbooks)
        for triple in [('tcp', 22, 22), ('tcp', 1194, 1194), ('udp', 1194, 1194), ('udp', 60000, 61000), ('tcp', 80, 80),
            ('tcp', 443, 443), ('tcp', 9001, 9001), ('tcp', 9030, 9030)]:
            self.sg.authorize(triple[0], triple[1], triple[2], '0.0.0.0/0')


    def start(self):
        self._create_key_pair()
        self._create_security_group()
        self.reservation = self.image[0].run(1, 1, key_name=self.kp.name, security_groups=[self.sg.name], instance_type=self.size)
        self.instance = self.reservation.instances[0]
        self._update_state()
        print("...pending")
        while self.state == u'pending':
            sys.stdout.write('.')
            self._update_state()
            time.sleep(30)
        self.public_dns = self.instance.public_dns_name
        self.instance.add_tag('popup_id', self.unique_tag)
        self.instance.add_tag('start_date', self.date)
        self.instance.add_tag('owner', self.args.iam)
        if self.args.client:
            self.instance.add_tag('client', self.args.client)

        # Manifest files serve as a poor inventory system
        # and a backup location for the server's SSH key
        with open('%s/.popup/manifests/%s-%s-%s' % (self.home, self.date, self.public_dns, self.unique_tag), 'w') as f:
            f.write(self.kp.material)
            os.chmod(f.name, 0600)

        self.connection_string = "ssh -i %s/.popup/keys/%s.pem ubuntu@%s" % (self.home, self.kp.name, self.public_dns)
        return self

    def _update_state(self):
        self.instance.update()
        self.state = self.instance.state

