FROM mariadb:11.8

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash gzip coreutils \
    && rm -rf /var/lib/apt/lists/*

COPY backup-loop.sh /usr/local/bin/backup-loop.sh
RUN chmod 0755 /usr/local/bin/backup-loop.sh

ENTRYPOINT ["/usr/local/bin/backup-loop.sh"]
