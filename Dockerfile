FROM python:3.5-alpine
MAINTAINER <https://github.com/o2r-project>

WORKDIR /shipper
COPY shipper.py shipper.py
COPY config.json config.json
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "shipper.py"]