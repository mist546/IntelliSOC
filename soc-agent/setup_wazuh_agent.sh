#!/usr/bin/env bash
# Installs a Wazuh agent on this Ubuntu/Debian VM and connects it to the
# Wazuh manager VM (set up first with setup_wazuh_bridge.sh).
#
#   sudo bash setup_wazuh_agent.sh --manager <manager-VM-IP> [--name <agent-name>]
#
# Options:
#   --enable-ssh-password-auth   install the SSH server and allow password
#                                logins (lab use only), so this VM can be the
#                                target of SSH brute-force demos
#
# Safe to re-run.
set -euo pipefail

MANAGER=""
AGENT_NAME="$(hostname)"
SSH_PASSWORD_AUTH=0
OSSEC_CONF=/var/ossec/etc/ossec.conf
OSSEC_LOG=/var/ossec/logs/ossec.log

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manager) MANAGER="${2:-}"; shift 2 ;;
    --name) AGENT_NAME="${2:-}"; shift 2 ;;
    --enable-ssh-password-auth) SSH_PASSWORD_AUTH=1; shift ;;
    *) usage ;;
  esac
done
[[ -n "$MANAGER" ]] || usage
[[ $EUID -eq 0 ]] || { echo "Please run with sudo."; exit 1; }
command -v apt-get >/dev/null || { echo "Only Ubuntu/Debian are supported."; exit 1; }

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

step "Checking the Wazuh manager at $MANAGER"
for port in 1515 1514; do
  timeout 5 bash -c "exec 3<>/dev/tcp/$MANAGER/$port" 2>/dev/null || fail "Cannot reach $MANAGER:$port.
  - Is the manager VM running, and did setup_wazuh_bridge.sh finish there?
  - Are both VMs on the same VMware network (e.g. both NAT)? Check with: ping $MANAGER"
done
echo "Manager reachable on 1515 (enrollment) and 1514 (events)."

step "Updating package lists"
if ! apt-get update -qq; then
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${VERSION_CODENAME:-}" == "buster" ]] || fail "apt-get update failed - fix the package sources and re-run."
  # Debian 10 is end-of-life; its packages now live on archive.debian.org.
  echo "Debian 10 detected: switching apt to archive.debian.org (backup: /etc/apt/sources.list.intellisoc.bak)."
  [[ -f /etc/apt/sources.list.intellisoc.bak ]] || cp /etc/apt/sources.list /etc/apt/sources.list.intellisoc.bak
  cat > /etc/apt/sources.list <<'EOF'
deb http://archive.debian.org/debian buster main contrib non-free
deb http://archive.debian.org/debian-security buster/updates main contrib non-free
EOF
  apt-get -o Acquire::Check-Valid-Until=false update -qq
fi
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl gnupg apt-transport-https rsyslog >/dev/null

step "Installing the Wazuh agent"
if [[ ! -f /usr/share/keyrings/wazuh.gpg ]]; then
  curl -fsS https://packages.wazuh.com/key/GPG-KEY-WAZUH \
    | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
  chmod 644 /usr/share/keyrings/wazuh.gpg
fi
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
  > /etc/apt/sources.list.d/wazuh.list
apt-get update -qq
WAZUH_MANAGER="$MANAGER" WAZUH_AGENT_NAME="$AGENT_NAME" DEBIAN_FRONTEND=noninteractive \
  apt-get install -y -qq wazuh-agent >/dev/null
# The agent must never be newer than the manager.
apt-mark hold wazuh-agent >/dev/null
# The install-time variables only apply on first install; keep a re-run's --manager too.
sed -i "s#<address>[^<]*</address>#<address>$MANAGER</address>#" "$OSSEC_CONF"
echo "Installed $(dpkg-query -W -f='wazuh-agent ${Version}' wazuh-agent)."

step "Making the agent send this VM's SSH/auth log"
has_authlog=0; has_journald=0
grep -q '<location>/var/log/auth.log</location>' "$OSSEC_CONF" && has_authlog=1
grep -q '<location>journald</location>' "$OSSEC_CONF" && has_journald=1
if [[ $has_authlog -eq 0 && $has_journald -eq 0 ]]; then
  cat >> "$OSSEC_CONF" <<'EOF'

<!-- Added by IntelliSOC setup_wazuh_agent.sh -->
<ossec_config>
  <localfile>
    <log_format>syslog</log_format>
    <location>/var/log/auth.log</location>
  </localfile>
</ossec_config>
EOF
  echo "Added /var/log/auth.log."
elif [[ $has_authlog -eq 1 && $has_journald -eq 1 ]]; then
  echo "WARNING: $OSSEC_CONF reads both /var/log/auth.log and journald. If every SSH"
  echo "failure shows up twice on IntelliSOC's Logs page, remove one of the two <localfile> blocks."
else
  echo "Already configured."
fi

if [[ $SSH_PASSWORD_AUTH -eq 1 ]]; then
  step "Installing the SSH server and allowing password logins (lab only)"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server >/dev/null
  mkdir -p /etc/ssh/sshd_config.d
  # sshd keeps the first value it reads; 00- sorts before e.g. 50-cloud-init.conf.
  echo "PasswordAuthentication yes" > /etc/ssh/sshd_config.d/00-intellisoc-lab.conf
  if ! grep -qE '^\s*Include\s+/etc/ssh/sshd_config.d' /etc/ssh/sshd_config; then
    # Older releases (e.g. Debian 10) don't include sshd_config.d.
    sed -i 's/^\s*PasswordAuthentication\s.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
    grep -qE '^PasswordAuthentication yes' /etc/ssh/sshd_config || echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
  fi
  systemctl restart ssh 2>/dev/null || systemctl restart sshd
fi

step "Starting the agent"
log_lines=$(wc -l < "$OSSEC_LOG" 2>/dev/null || echo 0)
systemctl daemon-reload
systemctl enable wazuh-agent >/dev/null 2>&1
systemctl restart wazuh-agent
connected=0
for _ in $(seq 1 30); do
  if tail -n +"$((log_lines + 1))" "$OSSEC_LOG" 2>/dev/null | grep -q "Connected to the server"; then
    connected=1; break
  fi
  sleep 1
done

step "Status"
printf 'wazuh-agent:  %s\n' "$(systemctl is-active wazuh-agent)"
printf 'agent name:   %s\n' "$AGENT_NAME"
printf "this VM's IP: %s\n" "$(hostname -I | awk '{print $1}')"
if [[ $connected -eq 1 ]]; then
  echo "Connected to the manager at $MANAGER."
else
  echo "WARNING: no connection confirmed yet - check: tail -n 30 $OSSEC_LOG"
fi
cat <<EOF

On the manager VM, 'sudo /var/ossec/bin/agent_control -l' should list "$AGENT_NAME" as Active.

Test: from the PC, run  ssh wronguser@$(hostname -I | awk '{print $1}')  and type a wrong
password 10+ times - an "SSH Brute Force" alert with host "$AGENT_NAME" appears on the
IntelliSOC dashboard.
EOF
