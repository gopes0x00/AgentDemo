#!/bin/bash

# Update the package index
sudo yum update -y

# Install wget if not already present
if ! command -v wget &> /dev/null; then
    echo "wget not found, installing..."
    sudo yum install -y wget
fi

# Install Go if not already present
if ! command -v go &> /dev/null; then
    echo "Go not found, installing..."
    sudo yum install -y golang
fi

# Download and install go-audit
GO_AUDIT_VERSION="v1.2.0"
DOWNLOAD_URL="https://github.com/slackhq/go-audit/releases/download/${GO_AUDIT_VERSION}/go-audit-linux-amd64.tar.gz"

mkdir -p /opt/go-audit
wget $DOWNLOAD_URL -O /tmp/go-audit.tar.gz && sudo tar -xzf /tmp/go-audit.tar.gz -C /opt/go-audit


# Create a basic go-audit configuration file
cat <<EOF | sudo tee /opt/go-audit/go-audit.yml
# /etc/go-audit.yaml

canary: true

output:
  file:
    enabled: true
    attempts: 2
    path: /var/log/go-audit/go-audit.log
    mode: 0600
    user: root
    group: root

# log an event when we believe a message has been lost
message_tracking:
  enabled: true
  log_out_of_order: false
  max_out_of_order: 500

rules:
  - -b 1024
  # required if you set canary: true
  - -w /proc/net/netlink -p war -k netlink-file
  # watch interesting network events
  - -a exit,always -S connect
  - -a exit,always -S listen
  # watch execve for everything that has an auid set (ignores things like cron)
  - -a exit,always -F arch=b64 -F auid!=-1 -S execve -k user_commands
  - -a exit,always -F arch=b32 -F auid!=-1 -S execve -k user_commands
  # failure to access file because of perms
  - -a always,exit -F arch=b32 -S open -S openat -F exit=-EACCES -k access
  - -a always,exit -F arch=b64 -S open -S openat -F exit=-EACCES -k access
  - -a always,exit -F arch=b32 -S open -S openat -F exit=-EPERM -k access
  - -a always,exit -F arch=b64 -S open -S openat -F exit=-EPERM -k access

filters:
  # reduce the number of connect syscall events being logged
  - syscall: 42
    message_type: 1306
    # 0200....7F - ipv4 on any port to 127.x.x.x
    # 01 - local/unix domain sockets
    regex: saddr=(0200....7F|01)
EOF

cat <<EOF | sudo tee /etc/systemd/system/go-audit.service
# /etc/systemd/system/go-audit.service
[Unit]
Description = go-audit
After=network.target auditd.service
Conflicts = auditd.service

[Service]
Type = simple
ExecStart = /opt/go-audit/go-audit -config /opt/go-audit/go-audit.yml

[Install]
WantedBy = multi-user.target
EOF

# Setup go-audit and run
sudo mkdir -p /var/log/go-audit
sudo systemctl enable go-audit && sudo systemctl start go-audit

# Secure SSH configuration to only allow key-based authentication
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

# prevent double logging for audit
sudo systemctl mask systemd-journald-audit.socket

# Restart SSH service to apply changes
sudo systemctl restart sshd

echo "Go and go-audit installed, and SSH configured for key-based authentication only."
