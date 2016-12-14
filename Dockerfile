FROM python:3.5-alpine
MAINTAINER <https://github.com/o2r-project>

RUN apk add --no-cache wget \
    && wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 \
    && chmod +x /usr/local/bin/dumb-init \
    && apk del wget

WORKDIR /shipper
COPY shipper.py shipper.py
COPY config.json config.json
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "shipper.py"]

# docker build -t shipper .