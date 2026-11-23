FROM kalilinux/kali-rolling

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        hydra nmap nikto sqlmap curl openssh-client sshpass iputils-ping ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY wordlists/ /root/wordlists/
COPY cheatsheet.txt /root/cheatsheet.txt
RUN sed -i 's/\r$//' /root/wordlists/* /root/cheatsheet.txt \
    && echo 'cat /root/cheatsheet.txt' >> /root/.bashrc

WORKDIR /root
