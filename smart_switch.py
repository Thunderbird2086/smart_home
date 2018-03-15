import email.utils
from logging import getLogger, DEBUG
import socket
from upnp_device import upnp_device

import const

logger = getLogger('devel')

# This subclass does the bulk of the work
# to mimic a WeMo switch on the network.

SETUP_XML = """<?xml version="1.0"?>
<root xmlns="urn:Belkin:service-1-0">
  <device>
    <!-- general info : begin -->
    <friendlyName>%(device_name)s</friendlyName>
    <manufacturer>Belkin International Inc.</manufacturer>
    <modelName>Emulated Light</modelName>
    <modelNumber>3.1415</modelNumber>
    <serialNumber>221517K0101769</serialNumber>
    <UDN>uuid:Light-1_0-%(device_serial)s</UDN>
    <deviceType>urn:Belkin:device:controllee:1</deviceType>
    <!-- general info : end -->
    <binaryState>0</binaryState>
    <!-- service info : begin -->
    <serviceList>
        <service>
            <serviceType>urn:Belkin:service:basicevent:1</serviceType>
            <serviceId>urn:Belkin:serviceId:basicevent1</serviceId>
            <controlURL>/upnp/control/basicevent1</controlURL>
            <eventSubURL>/upnp/event/basicevent1</eventSubURL>
            <SCPDURL>/eventservice.xml</SCPDURL>
        </service>
        <!-- declaration for the other services (if any) go here -->
    </serviceList>
    <!-- service info : end -->
    <!-- deviceList>Description of embedded devices (if any) go here </deviceList -->
  </device>
</root>
"""

eventservice_xml = """<?scpd xmlns="urn:Belkin:service-1-0"?>
<actionList>
  <action>
    <name>SetBinaryState</name>
    <argumentList>
      <argument>
        <retval/>
        <name>BinaryState</name>
        <relatedStateVariable>BinaryState</relatedStateVariable>
        <direction>in</direction>
      </argument>
    </argumentList>
     <serviceStateTable>
      <stateVariable sendEvents="yes">
        <name>BinaryState</name>
        <dataType>Boolean</dataType>
        <defaultValue>0</defaultValue>
      </stateVariable>
      <stateVariable sendEvents="yes">
        <name>level</name>
        <dataType>string</dataType>
        <defaultValue>0</defaultValue>
      </stateVariable>
    </serviceStateTable>
  </action>
</scpd>
"""

GetBinaryState_soap = \
"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:GetBinaryStateResponse xmlns:u="urn:Belkin:service:basicevent:1">
      <BinaryState>%(state_realy)s</BinaryState>
    </u:GetBinaryStateResponse>
  </s:Body>
</s:Envelope>
"""

REQ_GET_BINARY_STATE = 'urn:Belkin:service:basicevent:1#GetBinaryState'
SOAP_SET_BINARY_STATE = \
        'SOAPACTION: "urn:Belkin:service:basicevent:1#SetBinaryState"'

SERVICE ='urn:Belkin:service:basicevent:1'

class smart_switch(upnp_device):
    relayState = 0

    def __init__(self, name, listener, poller, ip_address, port,
                 action_handler=None):
        self._serial = upnp_device.make_uuid(name)
        if logger.isEnabledFor(DEBUG):
            #logger.debug(self.state)
            pass

        persistent_uuid = "Light-1_0-" + self._serial
        other_headers = ['X-User-Agent: Solvalou/3.14']
        upnp_device.__init__(self, listener, poller, port,
                             "OS2/4.50 UPnP/1.0 UPnP-Device-Host/1.0",
                             persistent_uuid, other_headers=other_headers,
                             ip_address=ip_address)
        self.name = name

        if action_handler:
            self.action_handler = action_handler
        else:
            self.action_handler = self

        if logger.isEnabledFor(DEBUG):
            logger.debug("Virtual Switch/Light device '%s' ready on %s:%s" %
                         (self._name, self.ip_address, self.port))

    def _resp_msg(self, msg_body):
        date = email.utils.formatdate(timeval=None, localtime=False,
                                      usegmt=True)
        return ("HTTP/1.1 200 OK\r\n"
                "CONTENT-LENGTH: %d\r\n"
                "CONTENT-TYPE: text/xml charset=\"utf-8\"\r\n"
                "DATE: %s\r\n"
                "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                "%s"
                "CONNECTION: close\r\n"
                "\r\n"
                "%s" % (len(msg_body), date, self.extra_headers, msg_body))

    def _post_upnp(self, data):
        soap = GetBinaryState_soap % {'state_realy': self.state}
        return self._resp_msg(soap)

    def _event_srv(self, data):
        return self._resp_msg(eventservice_xml)

    def _get_setup_xml(self, data):
        if logger.isEnabledFor(DEBUG):
            logger.debug("Responding to setup.xml for %s" % self._name)
        xml = SETUP_XML % {'device_name': self._name,
                           'device_serial': self._serial}
        return self._resp_msg(xml)

    def _soap_set_binary_state(self, data):
        success = True
        if data.find('<BinaryState>1</BinaryState>') != -1:
            # on
            logger.info("Responding to ON for %s" % self._name)
            self.relayState = 1
            success = self.action_handler.on()
        elif data.find('<BinaryState>0</BinaryState>') != -1:
            # off
            logger.info("Responding to OFF for %s" % self._name)
            self.relayState = 0
            success = self.action_handler.off()
        else:
            success = False
            logger.warning("Unknown Binary State request:")
            if logger.isEnabledFor(DEBUG):
                logger.debug(data)

        if not success:
            return None

        # The echo is happy with the 200 status code and doesn't
        # appear to care about the SOAP response body
        soap = ''
        return self._resp_msg(soap)

    def notify(self, broadcast_socket):
        header_nt_usn = []
        header_nt_usn.append(('upnp:rootdevice',
                              const.USN_UPNP_ROOT_DEVICE %
                              self._persistent_uuid))

        header_nt_usn.append((self._persistent_uuid, self._persistent_uuid ))

        header_nt_usn.append((SERVICE,
                              'uuid:{0}::{1}'.format(self._persistent_uuid,
                                                     SERVICE)))

        upnp_device.notify(self, broadcast_socket, header_nt_usn)

    def handle_req(self, data, socket):
        if logger.isEnabledFor(DEBUG):
            logger.debug('----- Start ----')
            logger.debug("data : {0}".format(data))
        msg = None

        if data.find(const.POST_UPNP) == 0 and \
                data.find(REQ_GET_BINARY_STATE) != -1:
            msg  = self._post_upnp(data)
        elif data.find(const.GET_EVENT_SRV_XML) == 0:
            msg = self._event_srv(data)
        elif data.find(const.GET_SETUP_XML) == 0:
            msg = self._get_setup_xml(data)
        elif data.find(SOAP_SET_BINARY_STATE) != -1:
            msg = self._soap_set_binary_state(data)
        else:
            if logger.isEnabledFor(DEBUG):
                logger.debug('Uknown request: {0}'.format(data))
                logger.debug('---- End ----')
            return

        socket.send(msg)
        if logger.isEnabledFor(DEBUG):
            logger.debug(msg)
            logger.debug('---- End ----')

    def on(self):
        logger.info('turned on')
        return True

    def off(self):
        logger.info('turned off')
        return True

    @property
    def state(self):
        return self.relayState


# This is an example handler class. The fauxmo class expects handlers to be
# instances of objects that have on() and off() methods that return True
# on success and False otherwise.
#
# This example class takes two full URLs that should be requested when an on
# and off command are invoked respectively. It ignores any return data.
class action_to_black_bean(object):
    def __init__(self, on_cmd, off_cmd):
        self._on = on_cmd
        self._off = off_cmd

    def on(self):
        logger.info(self._on)
        return True

    def off(self):
        logger.info(self._off)
        return True


DEFINITION = [
    # ['office lights', 'cmd=on&a=office', 'cmd=off&a=office'],
    # ['kitchen lights', 'cmd=on&a=kitchen', 'cmd=off&a=kitchen'],
    # ['bedroom lights', 'cmd=on&a=bedroom', 'cmd=off&a=bedroom'],
    # ['dining room lights', 'cmd=on&a=dining', 'cmd=off&a=dining'],
    # ['home room lights', 'cmd=on&a=homeroom', 'cmd=off&a=homeroom'],
    # ['my room lights', 'cmd=on&a=myroom', 'cmd=off&a=myroom'],
    ['something', 'file name for turn on', 'file name for turn off'],
]


SWITCHES = []

switches = []

def load(listener, poller):
    for name, on, off in DEFINITION:
        device = [name, action_to_black_bean(on, off)]
        SWITCHES.append(device)

    for one in SWITCHES:
        if len(one) == 2:
            # a fixed port wasn't specified, use a dynamic one
            one.append(0)
        switch = smart_switch(one[0], listener, poller, None,
                              one[2], action_handler=one[1])

        switches.append(switch)

def notify(broadcast_socket):
    for switch in switches:
        switch.notify(broadcast_socket)
