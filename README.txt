Popup an EC2 instance running OpenVPN.

Package installation and configuration is handled buy ansible, an SSH-based systems configuration system similar to Puppet or Chef that doesn't use a central server. http://ansible.cc

popup
├── PopupServer
├── manifests.............inventory of EC2 instances created
├── keys..................EC2 instance private keys
├── playbooks.............ansible playbooks
└── config................ssh and ansible configs and environment settings
    ├── ssh_control...........SSH multiplexed connections
    └── ssh_config............per instance SSH config files

