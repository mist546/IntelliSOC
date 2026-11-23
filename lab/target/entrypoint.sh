#!/bin/sh
set -e

mkdir -p /var/log/lab /run/sshd
touch /var/log/lab/auth.log /var/log/lab/nginx_access.log
rm -f /run/rsyslogd.pid

rsyslogd
# Not "sshd -D -e": -e would send sshd's log to stderr instead of syslog.
/usr/sbin/sshd

# Wazuh mode (docker-compose.wazuh.yml): ship the logs to the Wazuh manager
# instead of the host. Started in the background once the manager's
# enrollment port answers, so nginx comes up either way.
if [ -n "$WAZUH_MANAGER" ]; then
    sed -i "s|MANAGER_ADDRESS|$WAZUH_MANAGER|" /var/ossec/etc/ossec.conf
    (
        until bash -c "exec 3<>/dev/tcp/$WAZUH_MANAGER/1515" 2>/dev/null; do sleep 3; done
        /var/ossec/bin/wazuh-control start >/dev/null
        echo "[lab-target] wazuh-agent started, reporting to $WAZUH_MANAGER"
    ) &
fi

echo "[lab-target] sshd on :22, nginx on :80, logs in /var/log/lab"
exec nginx -g 'daemon off;'
