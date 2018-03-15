#!/usr/bin/env python

"""
The MIT License (MIT)

Copyright (c) 2015 Maker Musings

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

# For a complete discussion, see http://www.makermusings.com

from logging import getLogger, DEBUG
import select
import socket
import struct
import time

from const import ALEXA
from const import FILTER

logger = getLogger('devel')


class poller:
    # A simple utility class to wait for incoming data to be
    # ready on a socket.
    def __init__(self):
        self._poller = None

        if 'poll' in dir(select):
            self._poller = select.poll()

        self._devices = {}

    def add(self, device, file_no=None):
        if not file_no:
            file_no = device.fileno()

        if self._poller:
            self._poller.register(file_no, select.POLLIN)

        self._devices[file_no] = device

    def remove(self, device, file_no=None):
        if not file_no:
            file_no = device.fileno()

        if self._poller:
            self._poller.unregister(file_no)

        del(self._devices[file_no])

    def poll(self, timeout=0):
        ready = []
        if self._poller:
            ready = self._poller.poll(timeout)
        elif len(self._devices) > 0:
            (rsocks, wsocks, esocks) = select.select(self._devices.keys(),
                                                  [], [], timeout)
            ready = [(s, None) for s in rsocks]

        for file_no in ready:
            device = self._devices.get(file_no[0], None)
            if device:
                device.read(file_no[0])


class upnp_broadcaster(object):
    # Since we have a single process managing several virtual UPnP devices,
    # we only need a single listener for UPnP broadcasts. When a matching
    # search is received, it causes each device instance to respond.
    TIMEOUT = 0

    def __init__(self):
        self.devices = []
        self.inprogress = False

    def init_socket(self):
        ok = True
        self.ip = '239.255.255.250'
        self.port = 1900
        try:
            # This is needed to join a multicast group
            self.mreq = struct.pack(
                "4sl", socket.inet_aton(self.ip), socket.INADDR_ANY)

            # Set up server socket
            self.ssock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.ssock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                self.ssock.bind(('', self.port))
            except Exception as e:
                logger.warning("WARNING: Failed to bind %s:%d: %s",
                             (self.ip, self.port, e))
                ok = False

            try:
                self.ssock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.mreq)
            except Exception as e:
                logger.warning('WARNING: Failed to join multicast group:{0}'.
                             format(e))
                ok = False

        except Exception as e:
            logger.error("Failed to initialize UPnP sockets:{0}".format(e))
            return False

        if ok:
            logger.info("Listening for UPnP broadcasts")

        return ok

    def fileno(self):
        return self.ssock.fileno()

    def read(self, fileno):
        data, sender = self.recvfrom(1024)
        if logger.isEnabledFor(DEBUG):
            logger.debug('sender: {0} - data : {1}'.format(sender, data))

        if sender[0] in FILTER:
            return

        if sender[0] in ALEXA:
            logger.info(ALEXA[sender[0]])

        if data:
            if data.find('M-SEARCH') == 0 and not self.inprogress:
                if data.find('upnp:rootdevice') != -1:
                    for device in self.devices:
                        time.sleep(0.1)
                        device.respond_to_search(sender, 'urn:rootdevice')
                        self.inprogress = True
            else:
                pass
        else:
            pass

    # Receive network data
    def recvfrom(self, size):
        if self.TIMEOUT:
            self.ssock.setblocking(0)
            ready = select.select([self.ssock], [], [], self.TIMEOUT)[0]
        else:
            self.ssock.setblocking(1)
            ready = True

        try:
            if ready:
                return self.ssock.recvfrom(size)
            else:
                return False, False
        except Exception as e:
            logger.error(e)
            return False, False

    def add_device(self, device):
        self.devices.append(device)
        logger.info("UPnP broadcast listener: new device registered")
