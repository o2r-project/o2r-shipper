#!/usr/bin/python3
"""
    Copyright (c) 2016 - o2r project

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
#pylint: skip-file

import argparse
import base64
from datetime import datetime
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
import uuid
import zipfile
import traceback

from io import BytesIO

import requests
from bottle import *
from pymongo import MongoClient, errors

from requestlogger import WSGILogger, ApacheFormatter
import logging

# Bottle
app = Bottle()

@app.hook('before_request')  # remove trailing slashes
def strip_path():
    try:
        request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')
    except Exception as exc:
        status_note(''.join(('! error: ', exc.args[0])))


@app.route('/api/v1/shipment/<name>', method='GET')
def shipment_get_one(name):
    data = db['shipments'].find_one({'id': name})
    if data is not None:
        response.status = 200
        response.content_type = 'application/json'
        if '_id' in data:
            data.pop('_id', None)
        return json.dumps(data)
    else:
        status_note(''.join(('user requested non-existing shipment ', name)))
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'not found'})


@app.route('/api/v1/shipment', method='GET')
def shipment_get_all():
    try:
        sid = request.query.id
        cid = request.query.compendium_id
        answer_list = []
        for key in db['shipments'].find():
            answer_list.append(key['id'])
        response.status = 200
        response.content_type = 'application/json'
        if cid:
            # TODO shipment?compendium_id=XXX must return a list of all shipments for the compendium
            answer_list = []
            for key in db['shipments'].find({'compendium_id': cid}):
                answer_list.append(key['id'])
        return json.dumps(answer_list)
    except:
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'bad request'})


@app.route('/api/v1/shipment', method='POST')
def shipment_post_new():
    try:
        global env_compendium_files
        # First check if user level is high enough:
        cookie = request.get_cookie(env_cookie_name)
        if cookie is None:
            status_note(''.join(('cookie "', env_cookie_name, '" cannot be found!')))
            response.status = 400
            response.content_type = 'application/json'
            return json.dumps({'error': 'bad request: authentication cookie is missing'})

        cookie = urllib.parse.unquote(cookie)
        ###cookie = request.forms.get('cookie')  # for testing only
        #action = request.forms.get('action') # todo
        user_entitled = session_user_entitled(cookie, env_user_level_min)
        status_note(''.join(('validating session with cookie "', cookie, '" and minimum level ', str(env_user_level_min), '. found user "', str(user_entitled), '"')))

        if user_entitled:
            # get shipment id
            new_id = request.forms.get('_id')
            if new_id is None:
                # create new shipment id, as post did not include one
                new_id = uuid.uuid4()
            data = {}
            data['id'] = str(new_id)
            data['compendium_id'] = request.forms.get('compendium_id')
            data['deposition_id'] = request.forms.get('deposition_id')
            data['deposition_url'] = request.forms.get('deposition_url')
            data['recipient'] = request.forms.get('recipient')
            data['last_modified'] = str(datetime.now())
            data['user'] = user_entitled
            data['status'] = 'new'
            db['shipments'].save(data)
            # submit to zenodo:
            if data['recipient'] == 'zenodo':
                status = 200
                # todo:
                # check if action = d and jump to delete depot
                if not data['deposition_id']:
                    # no depot yet, go create one
                    current_compendium = db['compendia'].find_one({'id': data['compendium_id']})
                    if current_compendium:
                        compendium_files = os.path.join(env_compendium_files, data['compendium_id'])
                        if os.path.isdir(compendium_files):
                            file_name = str(data['compendium_id']) + '.zip'
                            data['deposition_id'] = zen_create_depot(env_repository_zenodo_host, env_repository_zenodo_token)
                            data['deposition_url'] = ''.join((env_repository_zenodo_host.replace('api', 'record/'), data['deposition_id']))
                            zen_add_zip_to_depot(env_repository_zenodo_host, data['deposition_id'], file_name, compendium_files, env_repository_zenodo_token)
                            if 'metadata' in current_compendium:
                                if 'zenodo' in current_compendium['metadata']:
                                    md = current_compendium['metadata']['zenodo']
                                    zen_add_metadata(env_repository_zenodo_host, data['deposition_id'], md, env_repository_zenodo_token)
                            data['status'] = 'deposited'
                        else:
                            status_note('! error, invalid path to compendium: ' + compendium_files)
                            data['status'] = 'error'
                            status = 500

                # save shipment to database            
                db['shipments'].save(data)

                # build and send response
                response.status = status
                response.content_type = 'application/json'
                d = {}
                d['id'] = data['id']
                d['recipient'] = data['recipient']
                d['status'] = data['status']
                return json.dumps(d)
            else:
                # not zenodo (currently no others supported)
                response.status = 400
                response.content_type = 'application/json'
                return json.dumps({'error': 'unknown recipient'})
        else:
            response.status = 403
            response.content_type = 'application/json'
            return json.dumps({'error': 'insufficient permissions'})
    except requests.exceptions.RequestException as exc:
        status_note(''.join(('! error: ', exc.args[0], '\n', traceback.format_exc())))
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'bad request'})
    except Exception as exc:
        #raise
        status_note(''.join(('! error: ', exc.args[0], '\n', traceback.format_exc())))
        message = ''.join('bad request:', exc.args[0])
        response.status = 500
        response.content_type = 'application/json'
        return json.dumps({'error': message})


# Session
def session_get_cookie(val, secret):
    try:
        # Create session cookie string for session ID.
        signature = hmac.new(str.encode(secret), msg=str.encode(val), digestmod=hashlib.sha256).digest()
        signature_enc = base64.b64encode(signature)
        cookie = ''.join(('s:', val, '.', signature_enc.decode()))
        cookie = re.sub(r'\=+$', '', cookie)  # remove trailing = characters
        return cookie
    except Exception as exc:
        #raise
        status_note(''.join(('! error: ', exc.args[0])))

def session_get_user(cookie, my_db):
    session_id = cookie.split('.')[0].split('s:')[1]
    if hmac.compare_digest(cookie, session_get_cookie(session_id, env_session_secret)):
        sessions = my_db['sessions']
        try:
            session = sessions.find_one({'_id': session_id})
            session_user = session['session']['passport']['user']
            user_doc = my_db['users'].find_one({'orcid': session_user})
            return user_doc['orcid']
        except Exception as exc:
            # raise
            status_note(''.join(('! error: ', exc.args[0])))
    else:
        return None


def session_user_entitled(cookie, min_lvl):
    if cookie:
        user_orcid = session_get_user(cookie, db)
        this_user = db['users'].find_one({'orcid': user_orcid})
        if this_user['level'] >= min_lvl:
            return this_user['orcid']
        else:
            return None
    else:
        return None


# Zenodo
def zen_create_depot(base, token):
    try:
        # create new empty upload depot:
        headers = {"Content-Type": "application/json"}
        r = requests.post(''.join((base, '/deposit/depositions/?access_token=', token)), data='{}', headers=headers)
        if r.status_code == 201:
            status_note(''.join((str(r.status_code), ' created depot <', str(r.json()['id']),'>')))
        else:
            status_note(r.status_code)
        return str(r.json()['id'])
    except requests.exceptions.Timeout:
        status_note('server at <'+base+'> timed out')
    except Exception as exc:
        # raise
        status_note(''.join(('! error: ', exc.args[0])))


def zen_add_zip_to_depot(base, deposition_id, zip_name, target_path, token):
    try:
        fsum = files_dir_size(target_path)
        if fsum <= env_max_dir_size_mb:
            # get bucket url:
            headers = {"Content-Type": "application/json"}
            r = requests.get(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)), headers=headers)
            bucket_url = r.json()['links']['bucket']
            if r.status_code == 200:
                status_note(str(r.status_code) + ' using bucket <' + bucket_url + '>')
            else:
                status_note(r.status_code)
            # upload file into bucket:
            headers = {"Content-Type": "application/octet-stream"}
            # create a filelike object in memory
            filelike = BytesIO()
            # fill memory object into zip constructor
            zipf = zipfile.ZipFile(filelike, 'w', zipfile.ZIP_DEFLATED)
            # walk target dir recursively
            for root, dirs, files in os.walk(target_path):  #.split(os.sep)[-1]):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), target_path))
            zipf.close()
            filelike.seek(0)
            r = requests.put("".join((bucket_url, '/', zip_name, '?access_token=', token)), data=filelike.read(), headers=headers)
            if r.status_code == 200:
                status_note(''.join((str(r.status_code), ' uploaded file <', zip_name, '> to depot <', deposition_id, '> ', str(r.json()['checksum']))))
            else:
                status_note(r.status_code)
        else:
            status_note("! error: file not found")
    except Exception as exc:
        # raise
        status_note(''.join(('! error: ', exc.args[0])))


def zen_add_metadata(base, deposition_id, md, token):
    try:
        headers = {"Content-Type": "application/json"}
        r = requests.put(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)), data=json.dumps(md), headers=headers)
        if r.status_code == 200:
            status_note(str(r.status_code) + ' updated metadata at <'+deposition_id+'>')
        else:
            status_note(r.status_code)
    except Exception as exc:
        # raise
        status_note(''.join(('! error: ', exc.args[0])))


def zen_del_from_depot(base, deposition_id, token):
    pass


def zen_del_depot(base, deposition_id, token):
    try:
        r = requests.delete(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)))
        if r.status_code == 204:
            status_note(''.join((str(r.status_code), ' removed depot <', deposition_id, '>')))
        else:
            status_note(r.status_code)
    except Exception as exc:
        # raise
        status_note(''.join(('! error: ', exc.args[0])))


# File interaction
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


# Self
def status_note(msg):
    print(''.join(('[shipper] ', str(msg))))

# Main
if __name__ == "__main__":
    status_note('starting ...')
    my_version = 1
    my_mod = ''
    try:
        my_mod = datetime.fromtimestamp(os.stat(__file__).st_mtime)
    except OSError as exc:
        status_note(''.join(('! error: ', exc.args[0], '\n', traceback.format_exc())))
        sys.exit(1)

    status_note(''.join(('v', str(my_version), ' - ', str(my_mod))))
    parser = argparse.ArgumentParser(description='shipper arguments')
    # args required:
    # args optional:
    parser.add_argument('-t', '--token', help='access token', required=False)
    parser.add_argument('-x', '--testmode', help='remove depot immediately after upload, for testing purpose.', action='store_true', required=False)
    # args parsed:
    args = vars(parser.parse_args())
    arg_test_mode = args['testmode']
    status_note(''.join(('args: ', str(args))))

    # environment vars and defaults
    with open('config.json') as data_file:
        config = json.load(data_file)
    env_mongo_host = os.environ.get('SHIPPER_MONGODB', config['mongodb_host'])
    env_mongo_db_name = os.environ.get('SHIPPER_MONGO_NAME', config['mongodb_db'])
    env_bottle_host = os.environ.get('SHIPPER_BOTTLE_HOST', config['bottle_host'])
    env_bottle_port = os.environ.get('SHIPPER_BOTTLE_PORT', config['bottle_port'])
    env_repository_zenodo_host = os.environ.get('SHIPPER_REPO_ZENODO_HOST', config['repository_zenodo_host'])
    if args['token'] is None:
        env_repository_zenodo_token = os.environ.get('SHIPPER_REPO_ZENODO_TOKEN', config['repository_zenodo_token'])
    else:
        env_repository_zenodo_token = args['token']
    env_file_base_path = os.environ.get('SHIPPER_BASE_PATH', config['base_path'])
    env_max_dir_size_mb = os.environ.get('SHIPPER_MAX_DIR_SIZE', config['max_size_mb'])
    env_session_secret = os.environ.get('SHIPPER_SECRET', config['session_secret'])
    env_user_level_min = os.environ.get('SHIPPER_USERLEVEL_MIN', config['userlevel_min'])
    env_cookie_name = os.environ.get('SHIPPER_COOKIE_NAME', config['cookie_name'])
    env_compendium_files = os.path.join(env_file_base_path, 'compendium')  #config, + compendium_id
    env_user_id = None
    status_note(''.join(('loaded config and env:', '\n\tMongoDB: ', env_mongo_host, env_mongo_db_name, '\n\tbottle: ', env_bottle_host, ':', str(env_bottle_port))))

    # connect to db
    try:
        status_note('connecting to ' + str(env_mongo_host))
        client = MongoClient(env_mongo_host, serverSelectionTimeoutMS=12000)
        db = client[env_mongo_db_name]
        status_note('connected. MongoDB server version: ' + str(client.server_info()['version']))
    except errors.ServerSelectionTimeoutError as exc:
        status_note('! error: mongodb timeout error: ' + str(exc))
        sys.exit(1)
    except Exception as exc:
        status_note('! error: mongodb connection error: ' + str(exc))
        print(traceback.format_exc())
        sys.exit(1)
    
    # start service
    try:
        status_note(''.join(('starting bottle at ' + env_bottle_host + ':' + str(env_bottle_port), '...')))
        status_note(base64.b64decode('bGF1bmNoaW5nDQouLS0tLS0tLS0tLS0tLS0uDQp8ICAgICBfLl8gIF8gICAgYC4sX19fX19fDQp8ICAgIChvMnIoKF8oICAgICAgX19fKF8oKQ0KfCAgXCctLTotLS06LS4gICAsJw0KJy0tLS0tLS0tLS0tLS0tJ8#K0DQo=').decode('utf-8'))
        time.sleep(0.1)
        app = WSGILogger(app, [ logging.StreamHandler(sys.stdout) ], ApacheFormatter())
        run(app=app, host=env_bottle_host, port=env_bottle_port, debug=True)
    except Exception as exc:
        status_note('! error: bottle server could not be started: ' + traceback.format_exc())
        sys.exit(1)

