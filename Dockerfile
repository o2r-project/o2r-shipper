FROM python:3.6-alpine
MAINTAINER <https://github.com/o2r-project>

RUN apk add --no-cache wget git \
    && git clone --depth 1 -b master https://github.com/o2r-project/o2r-shipper /shipper \
    && wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 \
    && chmod +x /usr/local/bin/dumb-init \
    && apk del wget git

WORKDIR /shipper
RUN pip install -r requirements.txt

ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD ["python", "shipper.py"]

# docker build -t o2r-shipper .