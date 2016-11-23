FROM python:3.5-alpine
MAINTAINER <https://github.com/o2r-project>

WORKDIR /shipper
COPY shipper.py shipper.py
COPY test.zip test.zip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "shipper.py"]