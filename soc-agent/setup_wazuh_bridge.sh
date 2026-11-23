#!/usr/bin/env bash
# Sets up this Ubuntu/Debian VM as IntelliSOC's Wazuh manager + bridge.
#
# Copy the whole soc-agent/ folder to the VM, then from inside it run:
#   sudo bash setup_wazuh_bridge.sh --backend http://<PC-IP>:8000 --agent-id <id> --agent-key <api_key>
#
# Options:
#   --enable-ssh-password-auth   allow SSH password logins on this VM (lab use
#                                only) so SSH brute-force demos produce events
#
# Safe to re-run: it updates the bridge and its settings in place.
set -euo pipefail

BACKEND=""
AGENT_ID=""
AGENT_KEY=""
SSH_PASSWORD_AUTH=0
INSTALL_DIR=/opt/intellisoc-bridge
ENV_FILE=/etc/intellisoc-bridge.env
UNIT_FILE=/etc/systemd/system/intellisoc-bridge.service
OSSEC_CONF=/var/ossec/etc/ossec.conf
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend) BACKEND="${2:-}"; shift 2 ;;
    --agent-id) AGENT_ID="${2:-}"; shift 2 ;;
    --agent-key) AGENT_KEY="${2:-}"; shift 2 ;;
    --enable-ssh-password-auth) SSH_PASSWORD_AUTH=1; shift ;;
    *) usage ;;
  esac
done
[[ -n "$BACKEND" && -n "$AGENT_ID" && -n "$AGENT_KEY" ]] || usage
[[ $EUID -eq 0 ]] || { echo "Please run with sudo."; exit 1; }
command -v apt-get >/dev/null || { echo "Only Ubuntu/Debian are supported."; exit 1; }
BACKEND="${BACKEND%/}"

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

step "Installing base packages"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl gnupg apt-transport-https python3-venv rsyslog >/dev/null

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || fail "Python 3.10+ is required (this VM has $(python3 --version 2>&1)). Use Ubuntu 22.04 or newer."

step "Checking IntelliSOC at $BACKEND"
curl -fsS -m 5 "$BACKEND/api/health" >/dev/null || fail "Cannot reach $BACKEND/api/health from this VM.
  - Is the backend running on the PC (.\\scripts\\start_backend.ps1)?
  - Is the Windows Firewall rule for TCP 8000 in place?
  - With VMware NAT, the PC is the 'VMware Network Adapter VMnet8' address (ipconfig), e.g. http://192.168.86.1:8000"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 5 -X POST \
  -H "X-Agent-Id: $AGENT_ID" -H "X-Agent-Key: $AGENT_KEY" "$BACKEND/api/agents/heartbeat" || true)
[[ "$code" == "200" ]] || fail "IntelliSOC rejected the agent credentials (HTTP $code). Register a new agent on the Agents page and use its id/api_key."
echo "IntelliSOC reachable, agent credentials accepted."

step "Installing the Wazuh manager"
if [[ ! -f /usr/share/keyrings/wazuh.gpg ]]; then
  curl -fsS https://packages.wazuh.com/key/GPG-KEY-WAZUH \
    | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
  chmod 644 /usr/share/keyrings/wazuh.gpg
fi
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
  > /etc/apt/sources.list.d/wazuh.list
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq wazuh-manager >/dev/null
# Agents must never be newer than the manager; don't let routine upgrades move it.
apt-mark hold wazuh-manager >/dev/null
echo "Installed $(dpkg-query -W -f='wazuh-manager ${Version}' wazuh-manager)."

step "Making the manager watch this VM's own SSH/auth log"
has_authlog=0; has_journald=0
grep -q '<location>/var/log/auth.log</location>' "$OSSEC_CONF" && has_authlog=1
grep -q '<location>journald</location>' "$OSSEC_CONF" && has_journald=1
if [[ $has_authlog -eq 0 && $has_journald -eq 0 ]]; then
  cat >> "$OSSEC_CONF" <<'EOF'

<!-- Added by IntelliSOC setup_wazuh_bridge.sh -->
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
systemctl daemon-reload
systemctl enable wazuh-manager >/dev/null 2>&1
systemctl restart wazuh-manager

# Wazuh agents on other VMs enroll on 1515 and send events on 1514.
if command -v ufw >/dev/null && ufw status 2>/dev/null | grep -q '^Status: active'; then
  ufw allow 1514/tcp >/dev/null && ufw allow 1515/tcp >/dev/null
  echo "Opened ports 1514/1515 in ufw for Wazuh agents."
fi

step "Installing the IntelliSOC bridge in $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
if [[ "$SRC_DIR" != "$INSTALL_DIR" ]]; then
  # Keep the bridge's saved read position (state*.json) across re-runs.
  tar -C "$SRC_DIR" --exclude=.venv --exclude=__pycache__ --exclude='state*.json' \
    --exclude='windows_state.json' -cf - . | tar -C "$INSTALL_DIR" -xf -
fi
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -q --disable-pip-version-check -r "$INSTALL_DIR/requirements.txt"
sed -i "s#^backend_url:.*#backend_url: \"$BACKEND\"#" "$INSTALL_DIR/config.wazuh.yaml"

( umask 077; printf 'MINISOC_AGENT_ID=%s\nMINISOC_AGENT_KEY=%s\n' "$AGENT_ID" "$AGENT_KEY" > "$ENV_FILE" )

cat > "$UNIT_FILE" <<EOF
[Unit]
Description=IntelliSOC Wazuh bridge (forwards Wazuh alerts to IntelliSOC)
After=network-online.target wazuh-manager.service
Wants=network-online.target

[Service]
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_DIR/.venv/bin/python -u agent.py --config config.wazuh.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable intellisoc-bridge >/dev/null 2>&1
systemctl restart intellisoc-bridge

if [[ $SSH_PASSWORD_AUTH -eq 1 ]]; then
  step "Allowing SSH password logins (lab only)"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server >/dev/null
  mkdir -p /etc/ssh/sshd_config.d
  # sshd keeps the first value it reads; 00- sorts before e.g. 50-cloud-init.conf.
  echo "PasswordAuthentication yes" > /etc/ssh/sshd_config.d/00-intellisoc-lab.conf
  systemctl restart ssh 2>/dev/null || systemctl restart sshd
fi

step "Status"
sleep 3
printf 'wazuh-manager:     %s\n' "$(systemctl is-active wazuh-manager)"
printf 'intellisoc-bridge: %s\n' "$(systemctl is-active intellisoc-bridge)"
printf 'This VM'"'"'s IP:      %s\n' "$(hostname -I | awk '{print $1}')"
cat <<EOF

Done. The bridge should show ONLINE on IntelliSOC's Agents page within a few seconds.
  Bridge log:      journalctl -u intellisoc-bridge -f
  Wazuh alerts:    tail -f /var/ossec/logs/alerts/alerts.json
  Connected agents: /var/ossec/bin/agent_control -l

Test: from the PC, run  ssh wronguser@$(hostname -I | awk '{print $1}')  and type a wrong
password 10+ times - an "SSH Brute Force" alert appears on the IntelliSOC dashboard.
EOF
