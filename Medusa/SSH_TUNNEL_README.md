# Tunnel creation to access EC2 instance using SSH via HPE proxy

Remote connections to the EC2 instance via SSH from the Linux jumphost will timeout due to the proxy configuration by default.
We need to setup a tunnel for SSH connection to route via HTTP proxy in order to access the AWS EC2 instances. In order to do that, we need to Install the following dependencies before getting started with the tunnel creation.

## Dependencies
- Development tools
	- For Debian-based distributions (Ubuntu, ElementaryOS, ...)
	```sudo apt install build-essential```

	- For Red-Hat-based distributions (CentOS, Fedora, ...)
	```sudo yum groups mark install 'Development Tools'```
	```sudo yum groups mark convert 'Development Tools'```
	```sudo yum groupinstall 'Development tools'```

- Corkscrew repository - https://github.com/bryanpkc/corkscrew


## Installation

Clone the corkscrew repository and execute following commands in the same order from the same directory.

`autoreconf --install`
`./configure`
`make`
`sudo make install`


## Update SSH configuration to use tunnel'
Add the following line to `~/.ssh/config` file.

`ProxyCommand /usr/local/bin/corkscrew proxy.am.hpecore.net 443 %h %p`

Restart the sshd service for the changes to become active.

`systemctl restart sshd`

After making these changes you can use linux jumphost to connect to EC2 instances using public IP/DNS name via SSH.
