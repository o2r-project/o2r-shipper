
import argparse
import ast
# import base64
import hashlib
# import hmac
import json
import logging
# import os
# import re
# import time
import traceback
import urllib.parse
import uuid

import bagit
import requests
from bottle import *
from pymongo import MongoClient, errors


# File interaction
def files_scan_path(filepath):
    # scan dir to determine if bagit bag, zipfile, etc.
    try:
        if not os.path.isdir(filepath):
            return 0
        if os.path.isfile(os.path.join(filepath, 'bagit.txt')):
            # is a bagit bag
            return 1
        else:
            # needs to become a bagit bag
            return 2
        #scan for zip files
        #for fname in os.listdir('.'):
        #   if fname.endswith('.zip'):
        #   return 3
    except:
        print('error while scanning path')
        raise


def files_recursive_gen(start_path, gen_paths):
    for entry in os.scandir(start_path):
        if entry.is_dir(follow_symlinks=False):
            yield from files_recursive_gen(entry.path, gen_paths)
        else:
            if gen_paths:
                yield os.path.relpath(entry.path)
            else:
                yield os.stat(entry.path).st_size / 1024 ** 2


def files_dir_size(my_path):
    return sum(f for f in files_recursive_gen(my_path, False))


def status_note(msgtxt):
    if type(msgtxt) not in [list, str, dict]:
        msgtxt = str(msgtxt)
    if type(msgtxt) is list:
        msgtxt = ''.join(msgtxt)
    print(''.join(('[shipper] ', msgtxt)))


def xstr(s):
    return '' if s is None else str(s)


def strtobool(s):
    if s is None:
        return False
    if type(s) is str:
        if s.lower() in ['true', 't', 'yes', 'y', '1', 'on']:
            return True
        else:
            return False
    else:
        return False