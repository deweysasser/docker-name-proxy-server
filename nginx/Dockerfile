FROM nginx

RUN apt-get -y update && apt-get -y install inotify-tools psmisc
ADD watch-nginx /root/watch-nginx

CMD /root/watch-nginx 


