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


# shipper's generic parent class for repository api wrappers and provider for imported libs
class Repo:

    @staticmethod
    def is_parent():
        return True
