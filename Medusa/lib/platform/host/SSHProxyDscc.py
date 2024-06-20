from sshtunnel import SSHTunnelForwarder, address_to_str, BaseSSHTunnelForwarderError, HandlerSSHTunnelForwarderError
import socket
import threading
from binascii import hexlify

import paramiko


class SSHProxyDscc(SSHTunnelForwarder):
    def __init__(
        self,
        ssh_address_or_host,
        ssh_username,
        ssh_private_key,
        remote_bind_addresses: list(),
        local_bind_addresses: list(),
        ssh_proxy,
    ):
        super(SSHProxyDscc, self).__init__(
            ssh_address_or_host=ssh_address_or_host,
            ssh_username=ssh_username,
            ssh_private_key=ssh_private_key,
            remote_bind_addresses=remote_bind_addresses,
            local_bind_addresses=local_bind_addresses,
            ssh_proxy=ssh_proxy,
        )

    def start_ssh_dscc(self):
        """Start the SSH tunnels"""
        if self.is_alive:
            self.logger.warning("Already started!")
            return
        self._create_tunnels_dscc()
        if not self.is_active:
            self._raise(BaseSSHTunnelForwarderError, reason="Could not establish session to SSH gateway")
        for _srv in self._server_list:
            thread = threading.Thread(
                target=self._serve_forever_wrapper, args=(_srv,), name="Srv-{0}".format(address_to_str(_srv.local_port))
            )
            thread.daemon = self.daemon_forward_servers
            thread.start()
            self._check_tunnel(_srv)
        self.is_alive = any(self.tunnel_is_up.values())
        if not self.is_alive:
            self._raise(HandlerSSHTunnelForwarderError, "An error occurred while opening tunnels.")

    def _create_tunnels_dscc(self):
        """
        Create SSH tunnels on top of a transport to the remote gateway
        """
        if not self.is_active:
            try:
                self._connect_to_gateway_dscc()
            except socket.gaierror:  # raised by paramiko.Transport
                msg = "Could not resolve IP address for {0}, aborting!".format(self.ssh_host)
                self.logger.error(msg)
                return
            except (paramiko.SSHException, socket.error) as e:
                template = "Could not connect to gateway {0}:{1} : {2}"
                msg = template.format(self.ssh_host, self.ssh_port, e.args[0])
                self.logger.error(msg)
                return
        for rem, loc in zip(self._remote_binds, self._local_binds):
            try:
                self._make_ssh_forward_server(rem, loc)
            except BaseSSHTunnelForwarderError as e:
                msg = "Problem setting SSH Forwarder up: {0}".format(e.value)
                self.logger.error(msg)

    def _connect_to_gateway_dscc(self):
        """
        Open connection to SSH gateway
         - First try with all keys loaded from an SSH agent (if allowed)
         - Then with those passed directly or read from ~/.ssh/config
         - As last resort, try with a provided password
        """
        for key in self.ssh_pkeys:
            self.logger.debug("Trying to log in with key: {0}".format(hexlify(key.get_fingerprint())))
            try:
                self._transport = self._get_transport_dscc()
                self._transport.connect(hostkey=self.ssh_host_key, username=self.ssh_username, pkey=key)
                if self._transport.is_alive:
                    return
            except paramiko.AuthenticationException as e:
                self.logger.debug(f"Authentication error {e}")
                self._stop_transport()

        if self.ssh_password:  # avoid conflict using both pass and pkey
            self.logger.debug("Trying to log in with password: {0}".format("*" * len(self.ssh_password)))
            try:
                self._transport = self._get_transport_dscc()
                self._transport.connect(
                    hostkey=self.ssh_host_key, username=self.ssh_username, password=self.ssh_password
                )
                if self._transport.is_alive:
                    return
            except paramiko.AuthenticationException:
                self.logger.debug("Authentication error")
                self._stop_transport()

        self.logger.error("Could not open connection to gateway")

    def _get_transport_dscc(self):
        """Return the SSH transport to the remote gateway"""
        if self.ssh_proxy:
            if isinstance(self.ssh_proxy, paramiko.proxy.ProxyCommand):
                proxy_repr = repr(self.ssh_proxy.cmd[1])
            else:
                proxy_repr = repr(self.ssh_proxy)
            self.logger.debug("Connecting via proxy: {0}".format(proxy_repr))
            _socket = self.ssh_proxy
        else:
            _socket = (self.ssh_host, self.ssh_port)
        transport = paramiko.Transport(_socket)
        sock = transport.sock
        if isinstance(sock, socket.socket):
            sock.settimeout(200)
        transport.set_keepalive(self.set_keepalive)
        transport.use_compression(compress=self.compression)
        transport.daemon = self.daemon_transport
        # try to solve https://github.com/paramiko/paramiko/issues/1181
        # transport.banner_timeout = 200
        if isinstance(sock, socket.socket):
            sock_timeout = sock.gettimeout()
            sock_info = repr((sock.family, sock.type, sock.proto))
            self.logger.debug("Transport socket info: {0}, timeout={1}".format(sock_info, sock_timeout))
        return transport
