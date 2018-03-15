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
import logging
from logging import config
from logging import getLogger
import sys
import time

import const
import devices
from upnp_handler import poller, upnp_broadcaster

logging.config.fileConfig('logging.conf')
logger = getLogger()

if __name__ == '__main__':
    #logging.config.fileConfig('logging.conf')
    
    # Set up our singleton listener for UPnP broadcasts
    u = upnp_broadcaster()
    if not u.init_socket():
        logger.error("failed to initialize broad caster")
        exit(-1)
    
    # Set up our singleton for polling the sockets for data ready
    p = poller()
    
    # Add the UPnP broadcast listener to the poller so we can respond
    # when a broadcast is received.
    p.add(u)
    
    # Create our virtual switch(socket) devices
    devices.load(u, p)
    logger.info("Entering main loop\n")
    
    while True:
        try:
            # Allow time for a ctrl-c to stop the process
            p.poll(100)
            time.sleep(0.1)
        except Exception as e:
            logging.error(e)
            break
