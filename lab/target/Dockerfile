FROM ubuntu:24.04

# Must not be newer than the manager in docker-compose.wazuh.yml.
ARG WAZUH_VERSION=4.14.10

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        openssh-server rsyslog nginx curl gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Wazuh agent: installed always, but only started in Wazuh mode
# (start_lab.ps1 -Wazuh sets WAZUH_MANAGER; see entrypoint.sh).
RUN curl -fsSL https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor -o /usr/share/keyrings/wazuh.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
        > /etc/apt/sources.list.d/wazuh.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "wazuh-agent=${WAZUH_VERSION}-1" \
    && rm -rf /var/lib/apt/lists/*

# "admin" has a weak password on purpose, so a brute force can succeed and
# trigger FAILED_THEN_SUCCESS. "deploy" has a strong one.
RUN useradd -m -s /bin/bash admin && echo 'admin:password123' | chpasswd \
    && useradd -m -s /bin/bash deploy && echo 'deploy:Xk9#mQ2v!Lp7wR' | chpasswd

COPY sshd_lab.conf /etc/ssh/sshd_config.d/lab.conf
COPY rsyslog.conf /etc/rsyslog.conf
COPY site.conf /etc/nginx/sites-available/default
COPY www/ /var/www/html/
COPY wazuh-agent.conf /var/ossec/etc/ossec.conf
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh /etc/rsyslog.conf /etc/ssh/sshd_config.d/lab.conf /var/ossec/etc/ossec.conf \
    && chown root:wazuh /var/ossec/etc/ossec.conf && chmod 660 /var/ossec/etc/ossec.conf \
    && chmod +x /entrypoint.sh

EXPOSE 22 80
ENTRYPOINT ["/entrypoint.sh"]
