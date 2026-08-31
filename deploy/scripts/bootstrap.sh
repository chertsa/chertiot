#!/usr/bin/env bash
# CHERT IoT — VPS bootstrap (M2.2). Run once as root on a fresh Ubuntu 24.04 host:
#   curl -fsSL https://raw.githubusercontent.com/<org>/chertiot/main/deploy/scripts/bootstrap.sh | bash -s -- <deploy-user> <ssh-pubkey-file-or-url>
# Idempotent: safe to rerun. Does: deploy user + SSH hardening, UFW (22/80/443/8883), fail2ban,
# unattended-upgrades, Docker CE + compose plugin, log rotation, sysctl for many connections.
set -euo pipefail
DEPLOY_USER="${1:-chertiot}"
PUBKEY_SRC="${2:-}"
export DEBIAN_FRONTEND=noninteractive

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "packages"
apt-get update -q
apt-get install -y -q ufw fail2ban unattended-upgrades apt-listchanges ca-certificates curl gnupg git jq

step "deploy user ${DEPLOY_USER}"
id -u "$DEPLOY_USER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$DEPLOY_USER"
usermod -aG sudo "$DEPLOY_USER"
echo "${DEPLOY_USER} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${DEPLOY_USER}"; chmod 440 "/etc/sudoers.d/${DEPLOY_USER}"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/${DEPLOY_USER}/.ssh"
if [[ -n "$PUBKEY_SRC" ]]; then
  if [[ "$PUBKEY_SRC" =~ ^https?:// ]]; then curl -fsSL "$PUBKEY_SRC" >> "/home/${DEPLOY_USER}/.ssh/authorized_keys"; else cat "$PUBKEY_SRC" >> "/home/${DEPLOY_USER}/.ssh/authorized_keys"; fi
  sort -u -o "/home/${DEPLOY_USER}/.ssh/authorized_keys" "/home/${DEPLOY_USER}/.ssh/authorized_keys"
  chown "$DEPLOY_USER:$DEPLOY_USER" "/home/${DEPLOY_USER}/.ssh/authorized_keys"; chmod 600 "/home/${DEPLOY_USER}/.ssh/authorized_keys"
fi

step "ssh hardening"
cat > /etc/ssh/sshd_config.d/90-chertiot.conf <<'CONF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
CONF
[[ -s "/home/${DEPLOY_USER}/.ssh/authorized_keys" ]] && systemctl reload ssh || echo "!! no authorized_keys for ${DEPLOY_USER}; NOT reloading sshd (would lock you out)"

step "firewall"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment ssh
ufw allow 80/tcp comment http
ufw allow 443/tcp comment https
ufw allow 443/udp comment http3
ufw allow 8883/tcp comment mqtts
ufw --force enable

step "fail2ban"
cat > /etc/fail2ban/jail.d/chertiot.local <<'CONF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
[sshd]
enabled = true
CONF
systemctl enable --now fail2ban
systemctl restart fail2ban

step "unattended security upgrades"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
CONF
sed -i 's|^//\s*"${distro_id}:${distro_codename}-security";|        "${distro_id}:${distro_codename}-security";|' /etc/apt/apt.conf.d/50unattended-upgrades || true

step "docker"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
usermod -aG docker "$DEPLOY_USER"
cat > /etc/docker/daemon.json <<'CONF'
{ "log-driver": "json-file", "log-opts": { "max-size": "50m", "max-file": "5" }, "live-restore": true }
CONF
systemctl enable --now docker
systemctl restart docker

step "swap (2x RAM up to 8G; JVM burst tolerance on small hosts)"
if ! swapon --show | grep -q /swapfile; then
  MEM_G=$(( ($(free -m | awk 'NR==2{print $2}') + 512) / 1024 ))
  SWAP_G=$(( MEM_G * 2 > 8 ? 8 : MEM_G * 2 ))
  fallocate -l "${SWAP_G}G" /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

step "sysctl (many MQTT connections)"
cat > /etc/sysctl.d/90-chertiot.conf <<'CONF'
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.ip_local_port_range = 10240 65535
fs.file-max = 1048576
vm.swappiness = 10
CONF
sysctl --system >/dev/null

step "done"
echo "Next: as ${DEPLOY_USER}: git clone the repo, copy .env.example → .env (fill secrets), docker compose -f docker-compose.yml --profile core up -d"
