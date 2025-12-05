FROM alpine:3.20

RUN apk add --no-cache bash curl bind-tools ca-certificates tzdata

COPY public_ip_detector.sh /usr/local/bin/public_ip_detector.sh
RUN chmod +x /usr/local/bin/public_ip_detector.sh

ENV PUBLIC_IP_TEXT_PATH=/shared/public_ip.txt \
    PUBLIC_IP_JSON_PATH=/shared/public_ip.json \
    PUBLIC_IP_REFRESH_SECONDS=60 \
    PUBLIC_IP_PORT=27015

ENTRYPOINT ["/usr/local/bin/public_ip_detector.sh"]
