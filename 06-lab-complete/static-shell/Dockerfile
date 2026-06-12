FROM nginx:alpine

COPY 06-lab-complete/static-shell/nginx.conf /etc/nginx/conf.d/default.conf
COPY 06-lab-complete/static-shell /usr/share/nginx/html

COPY 06-lab-complete/static-shell/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
