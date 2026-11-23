# Wazuh manager for the IntelliSOC lab: the official image, minus Filebeat
# (it ships alerts to a Wazuh indexer, which this lab does not run -
# IntelliSOC is the dashboard), plus the lab's ossec.conf. The image's
# startup copies /wazuh-config-mount over /var/ossec on every start.
# Keep the version in step with WAZUH_VERSION in ../target/Dockerfile.
FROM wazuh/wazuh-manager:4.14.10

RUN rm -rf /etc/services.d/filebeat /etc/cont-init.d/1-config-filebeat

COPY ossec.conf /wazuh-config-mount/etc/ossec.conf
RUN sed -i 's/\r$//' /wazuh-config-mount/etc/ossec.conf
