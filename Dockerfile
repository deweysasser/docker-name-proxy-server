#
# Nginx Dockerfile
#
# https://github.com/dockerfile/nginx
#

# Pull base image.
FROM ubuntu:14.04

RUN apt-get update && apt-get -y install curl python
RUN curl https://get.docker.com | bash

RUN apt-get -y install python-pip
RUN pip install docker-py

ADD events.sh /root/watch
ADD build-proxy-config.py /root/
CMD ["/root/watch"]
ENV DOMAIN=example.com
VOLUME /etc/nginx/conf.d

