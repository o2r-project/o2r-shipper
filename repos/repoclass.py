import hashlib
import hmac
import json
import logging
import os
import re
import time
import traceback
import urllib.parse
import uuid
import zipfile
from datetime import datetime
from io import BytesIO

import bagit
import requests
import zipstream


# shipper's generic parent class for repository api wrappers
class Repo:

    @staticmethod
    def get_host(HOST):
        return str(HOST)

    @staticmethod
    def get_label(LABEL):
        return str(LABEL)

    @staticmethod
    def get_id(ID):
        return str(ID)
