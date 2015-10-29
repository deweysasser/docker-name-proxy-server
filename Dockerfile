#
# Nginx Dockerfile
#
# https://github.com/dockerfile/nginx
#

# Pull base image.
FROM ubuntu:14.04

RUN apt-get update && \
   apt-get -y install curl && \
   apt-get -y install software-properties-common

# Install Nginx.
RUN \
  add-apt-repository -y ppa:nginx/development && \
  apt-get update && \
  apt-get install -y nginx && \
  rm -rf /var/lib/apt/lists/* && \
  echo "\ndaemon off;" >> /etc/nginx/nginx.conf && \
  chown -R www-data:www-data /var/lib/nginx

# Define working directory.
WORKDIR /etc/nginx

# Define default command.
CMD ["nginx"]

# Expose ports.
EXPOSE 80
EXPOSE 443


RUN rm sites-enabled/default
ADD wrapper /root/
ADD build-proxy-config /root/

ENTRYPOINT ["/root/wrapper"]