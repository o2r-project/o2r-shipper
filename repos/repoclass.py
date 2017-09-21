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


# shipper's generic parent class for repository api wrappers
class Repo:
    def __init__(self):
        pass
