# (C) Copyright 2016 The o2r project. https://o2r.info
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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