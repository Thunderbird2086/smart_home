# This XML is the minimum needed to define one of our virtual switches
# to the Amazon Echo
# working with Alexa Amazon Echo (2nd generation)
URL_SETUP_XML = "http://%(ip_address)s:%(port)s/setup.xml"
URL_DES_XML = "http://%(ip_address)s:%(port)s/setup.xml"

POST_UPNP = 'POST /upnp/control/basicevent1 HTTP/1.1'
GET_EVENT_SRV_XML = 'GET /eventservice.xml HTTP/1.1'
GET_SETUP_XML = 'GET /setup.xml HTTP/1.1'

ALEXA = {'192.168.3.9'  : 'Echo Plus',
         '192.168.3.20' : 'Echo Dot'
        }

FILTER = [ '192.168.3.254', '192.168.3.253', '192.168.3.252', '192.168.3.251',
           '192.168.3.1', '192.168.3.12', '192.168.3.2' ]

UPNP_ROOT_DEVICE = 'upnp:rootdevice'
USN_UPNP_ROOT_DEVICE = 'uuid:%s::upnp:rootdevice'
