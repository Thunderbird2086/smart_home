import email.utils
from logging import getLogger, DEBUG
import socket
import uuid

import const

logger = getLogger('devel')


class upnp_device(object):
    host_ip = None

    @staticmethod
    def local_ip():
        if not upnp_device.host_ip:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                temp_socket.connect(('8.8.8.8', 53))
                upnp_device.host_ip = temp_socket.getsockname()[0]
            except socket.error:
                upnp_device.host_ip = '127.0.0.1'

            del(temp_socket)
            logger.info("got local address of %s" % upnp_device.host_ip)

        return upnp_device.host_ip

    @staticmethod
    def make_uuid(name):
        return ''.join(["%x" % sum([ord(c) for c in name])] +
                       ["%x" % ord(c) for c in "%sXevious!" % name])[:14]

    def __init__(self, listener, poller, port, server_version,
                 persistent_uuid, other_headers=None, ip_address=None):
        self._listener = listener
        self._poller = poller
        self.port = port
        self._server_version = server_version
        self._persistent_uuid = persistent_uuid
        self._uuid = uuid.uuid4()
        self._other_headers = other_headers

        if ip_address:
            self.ip_address = ip_address
        else:
            self.ip_address = upnp_device.local_ip()

        ''' TCP server socket
        '''
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.ip_address, self.port))
        self._socket.listen(5)
        if self.port == 0:
            self.port = self._socket.getsockname()[1]

        self._poller.add(self)
        self._client_sockets = {}
        self._listener.add_device(self)

    def fileno(self):
        return self._socket.fileno()

    def read(self, fileno):
        if fileno == self._socket.fileno():
            ''' server socket
            '''
            (client_socket, client_address) = self._socket.accept()
            self._poller.add(self, client_socket.fileno())
            self._client_sockets[client_socket.fileno()] = client_socket
            return

        data, _ = self._client_sockets[fileno].recvfrom(4096)
        if not data:
            self._poller.remove(self, fileno)
            del(self._client_sockets[fileno])
            return

        if logger.isEnabledFor(DEBUG):
            logger.debug('----- Start ----')
        self.handle_req(data, self._client_sockets[fileno])
        if logger.isEnabledFor(DEBUG):
            logger.debug('---- End ----')

    def handle_req(self, data, socket):
        pass

    @property
    def name(self):
        if self._name:
            return self._name
        
        return 'Unknown'

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def extra_headers(self):
        headers = ''
        for header in self._other_headers:
            headers += "%s\r\n" % header
        
        return headers

    def notify(self, broadcast_socket, headers):
        date_str = email.utils.formatdate(
            timeval=None, localtime=False, usegmt=True)

        location_url = const.URL_DES_XML % {
            'ip_address': self.ip_address, 'port': self.port}

        for nt, usn in headers:
            msg = ("NOTIFY * HTTP/1.1\r\n"
                   "HOST: 239.255.255.250:1900\r\n"
                   "CACHE-CONTROL: max-age=86400\r\n"
                   "LOCATION: %(loc)s\r\n"
                   "NT: %(nt)s\r\n"
                   "NTS: ssdp:alive\r\n"
                   "SERVER: %(server)s\r\n"
                   "USN: %(usn)s\r\n"
                   "\r\n"
                   % { 'loc':location_url, 'nt':nt,
                       'server':self._server_version,
                       'usn':usn })

            if logger.isEnabledFor(DEBUG):
                logger.debug(msg)
           
            broadcast_socket.sendto(msg, ('239.255.255.250', 1900))
            broadcast_socket.sendto(msg, ('239.255.255.250', 1900))

        if logger.isEnabledFor(DEBUG):
            logger.debug('---- End ----')

        pass

    def respond_to_search(self, dest, search_target):
        if logger.isEnabledFor(DEBUG):
            logger.debug('----- Start ----')
            logger.debug("Responding to search for %s" % self.name)

        date_str = email.utils.formatdate(
            timeval=None, localtime=False, usegmt=True)

        location_url = const.URL_SETUP_XML % {
            'ip_address': self.ip_address, 'port': self.port}

        message = ("HTTP/1.1 200 OK\r\n"
                   "CACHE-CONTROL: max-age=86400\r\n"
                   "DATE: %s\r\n"
                   "LOCATION: %s\r\n"
                   "OPT: \"http://schemas.upnp.org/upnp/1/0/\"; ns=01\r\n"
                   "01-NLS: %s\r\n"
                   "SERVER: %s\r\n"
                   "ST: %s\r\n"
                   "USN: uuid:%s::%s\r\n" % (
                    date_str, location_url, self._uuid, self._server_version,
                    search_target, self._persistent_uuid, search_target))

        message += self.extra_headers
        message += "\r\n"

        if logger.isEnabledFor(DEBUG):
            logger.debug(message)
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.sendto(message, dest)
        if logger.isEnabledFor(DEBUG):
            logger.debug('---- End ----')
