#
# Nginx Dockerfile
#
# https://github.com/dockerfile/nginx
#

# Pull base image.
FROM debian:jessie

RUN apt-get update && \
    apt-get -y install curl python && \
    curl https://get.docker.com | bash && \
    apt-get -y install python-pip && \
    pip install boto3 && \
    pip install docker-py

ADD events.sh /root/watch
ADD build-proxy-config.py /root/
RUN mkdir -p /etc/proxy
ENTRYPOINT ["/root/watch"]
ENV DOMAIN= MAX_UPLOAD_SIZE=100m
VOLUME /etc/nginx/conf.d
VOLUME /usr/share/nginx/html


