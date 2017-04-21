#!/usr/bin/python3
"""
    Copyright (c) 2016, 2017 - o2r project

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

import ast
import argparse
import base64
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

import requests
from bottle import *
from pymongo import MongoClient, errors
from requestlogger import WSGILogger, ApacheFormatter

# Bottle
app = Bottle()

@app.hook('before_request')
def strip_path():
    # remove trailing slashes
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
        response.status = 404
        response.content_type = 'application/json'
        return json.dumps({'error': 'a compendium with that id does not exist'})


@app.route('/api/v1/shipment', method='GET')
def shipment_get_all():
    try:
        cid = request.query.compendium_id
        answer_list = []
        for key in db['shipments'].find():
            answer_list.append(key['id'])
        response.status = 200
        response.content_type = 'application/json'
        if cid:
            answer_list = []
            for key in db['shipments'].find({'compendium_id': cid}):
                answer_list.append(key['id'])
        return json.dumps(answer_list)
    except:
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'bad request'})


@app.route('/api/v1/shipment/<shipmentid>/status', method='GET')
def shipment_get_status(shipmentid):
    try:
        data = db['shipments'].find_one({'id': shipmentid})
        if data is not None:
            if 'status' in data:
                response.status = 200
                response.content_type = 'application/json'
                return {'id': shipmentid, 'status': str(data['status'])}
            else:
                response.status = 400
                response.content_type = 'application/json'
                return {'error': 'shipment not found'}
    except:
        raise


@app.route('/api/v1/shipment/<shipmentid>/files', method='GET')
def shipment_get_file_id(shipmentid):
    try:
        current_depot = db_find_depotid_from_shipment(shipmentid)
        if db_find_recipient_from_shipment(shipmentid) == 'zenodo':
            headers = {"Content-Type": "application/json"}
            r = requests.get(''.join((env_repository_zenodo_host, '/deposit/depositions/', current_depot, '?access_token=', env_repository_zenodo_token)), headers=headers)
            if 'files' in r.json():
                response.status = 200
                response.content_type = 'application/json'
                return json_dumps({'files': r.json()['files']})
            else:
                response.status = 400
                response.content_type = 'application/json'
                return {'error': 'no files object in repository response'}
        elif db_find_recipient_from_shipment(shipmentid) == 'eudat':
            # todo: add eudat b2share
            response.content_type = 'application/json'
            return {'id': shipmentid, 'status': 'not yet implemented'}
        else:
            status_note('unknown recipient')
    except:
        raise


@app.route('/api/v1/shipment/<shipmentid>/publishment', method='PUT')
def shipment_put_publishment(shipmentid):
    try:
        #! once published, cant delete
        current_depot = db_find_depotid_from_shipment(shipmentid)
        if db_find_recipient_from_shipment(shipmentid) == 'zenodo':
            r = requests.post(''.join((env_repository_zenodo_host, '/deposit/depositions/', current_depot, '/actions/publish?access_token=',
                              env_repository_zenodo_token)))
            if r.status_code == 202:
                db.shipments.update_one({'id': shipmentid}, {'$set': {'status': 'published'}}, upsert=True)
                if 'doi_url' in r.json():
                    db.shipments.update_one({'id': shipmentid}, {'$set': {'doi_url': r.json()['doi_url']}}, upsert=True)
                response.status = r.status_code
                response.content_type = 'application/json'
                return {'id': shipmentid, 'status': 'published'}
            else:
                response.status = r.status_code
        elif db_find_recipient_from_shipment(shipmentid) == 'eudat':
            # todo: add eudat b2share
            response.content_type = 'application/json'
            return {'id': shipmentid, 'status': 'not yet implemented'}
        else:
            status_note('unknown recipient')
    except:
        raise


@app.route('/api/v1/shipment/<shipmentid>/files/<fileid>', method='DELETE')
def shipment_del_file_id(shipmentid, fileid):
    # delete specific of a depot of a shipment
    try:
        current_depot = db_find_depotid_from_shipment(shipmentid)
        if db_find_recipient_from_shipment(shipmentid) == 'zenodo':
            zenodo_del_from_depot(env_repository_zenodo_host, current_depot, fileid, env_repository_zenodo_token)
        elif db_find_recipient_from_shipment(shipmentid) == 'eudat':
            # todo: add eudat b2share
            response.content_type = 'application/json'
            return {'id': shipmentid, 'status': 'not yet implemented'}
        else:
            status_note('unknown recipient')
    except:
        raise


@app.route('/api/v1/shipment', method='POST')
def shipment_post_new():
    try:
        status_note('# # # New shipment request # # #')
        global env_compendium_files
        # First check if user level is high enough:
        try:
            # prefer this if provided via request (for non-browser use and testing)
            cookie = request.forms.get('cookie')
        except:
            cookie = request.get_cookie(env_cookie_name)
        if cookie is None:
            status_note(''.join(('cookie <', env_cookie_name, '> cannot be found!')))
            response.status = 400
            response.content_type = 'application/json'
            return json.dumps({'error': 'bad request: authentication cookie is missing'})
        cookie = urllib.parse.unquote(cookie)
        user_entitled = session_user_entitled(cookie, env_user_level_min)
        status_note(''.join(('validating session with cookie <', cookie, '> and minimum level ', str(env_user_level_min), '. found user <', str(user_entitled), '>')))
        if user_entitled:
            # get shipment id
            new_id = request.forms.get('_id')
            if new_id is None:
                # create new shipment id because request did not include one
                new_id = uuid.uuid4()
            new_md = request.forms.get('md')
            if new_md is None:
                new_md = {}
            else:
                try:
                    new_md = ast.literal_eval(new_md)
                except:
                    new_md = {}
            data = {'id': str(new_id),
                    'compendium_id': request.forms.get('compendium_id'),
                    'deposition_id': request.forms.get('deposition_id'),
                    'deposition_url': request.forms.get('deposition_url'),
                    'recipient': request.forms.get('recipient'),
                    'last_modified': str(datetime.now()),
                    'user': user_entitled,
                    'status': 'shipped',
                    'md': new_md
                    }
            #db['shipments'].save(data)  # deprecated (pymongo)
            current_mongo_doc = db.shipments.insert_one(data)
            status_note('created shipment object ' + str(current_mongo_doc.inserted_id))
            status = 200
            if not data['deposition_id']:
                # no depot yet, go create one
                current_compendium = db['compendia'].find_one({'id': data['compendium_id']})
                if current_compendium:
                    # zip all files in dir and submit as zip:
                    compendium_files = os.path.join(env_compendium_files, data['compendium_id'])
                    if os.path.isdir(compendium_files):
                        file_name = '.'.join((str(data['compendium_id']), 'zip'))
                        if data['recipient'] == 'zenodo':
                            data['deposition_id'] = zenodo_create_depot(env_repository_zenodo_host, env_repository_zenodo_token)
                            data['deposition_url'] = ''.join((env_repository_zenodo_host.replace('api', 'deposit/'), data['deposition_id']))
                            zenodo_add_zip_to_depot(env_repository_zenodo_host, data['deposition_id'], file_name, compendium_files, env_repository_zenodo_token)
                            # Add metadata that are in compendium in db:
                            if 'metadata' in current_compendium:
                                if 'zenodo' in current_compendium['metadata']:
                                    md = current_compendium['metadata']['zenodo']
                                    zenodo_add_metadata(env_repository_zenodo_host, data['deposition_id'], md,
                                                        env_repository_zenodo_token)
                        elif data['recipient'] == 'eudat':
                            data['deposition_id'] = eudat_create_depot(env_repository_eudat_host, env_repository_eudat_token)
                            data['deposition_url'] = ''.join((env_repository_eudat_host.replace('api', 'records/'), data['deposition_id']))
                            eudat_add_zip_to_depot(env_repository_eudat_host, data['deposition_id'], file_name, compendium_files, env_repository_eudat_token)
                            # Add metadata that are in compendium in db:
                            if 'metadata' in current_compendium:
                                if 'eudat' in current_compendium['metadata']:
                                    md = current_compendium['metadata']['eudat']
                                    eudat_update_md(env_repository_eudat_host, data['deposition_id'], md, env_repository_eudat_token)
                    else:
                        status_note('! error, invalid path to compendium: ' + compendium_files)
                        data['status'] = 'error'
                        status = 400
            # update shipment data in database
            #db['shipments'].save(data)  # deprecated (pymongo)
            db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data}, upsert=True)
            status_note('updated shipment object ' + str(current_mongo_doc.inserted_id))
            # build and send response
            response.status = status
            response.content_type = 'application/json'
            # preview object for logger:
            d = {'id': data['id'],
                 'recipient': data['recipient'],
                 'deposition_id': data['deposition_id'],
                 'status': data['status']
                 }
            return json.dumps(d)
        else:
            response.status = 403
            response.content_type = 'application/json'
            return json.dumps({'error': 'insufficient permissions (not logged in?)'})
    except requests.exceptions.RequestException as exc:
        raise  # debug
        status_note(''.join(('! error: ', exc.args[0], '\n', traceback.format_exc())))
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'bad request'})
    except Exception as exc:
        raise  # debug
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
    if not session_id:
        status_note(''.join(('no session found for cookie "', cookie, '"')))
        return None
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
        if not user_orcid:
            status_note(''.join(('No orcid found for cookie "', xstr(cookie))))
            return None
        this_user = db['users'].find_one({'orcid': user_orcid})
        status_note(''.join(('found user <', xstr(this_user), '> for orcid ', user_orcid)))
        if this_user:
            if this_user['level'] >= min_lvl:
                return this_user['orcid']
            else:
                return None
        else:
            return None
    else:
        return None


# Repository Eudat b2share
def eudat_create_depot(base, access_token):
    try:
        headers = {"Content-Type": "application/json"}
        base_url = ''.join((base, "/records/?access_token=", access_token))
        # test md
        d = {"titles": [{"title": "TestRest"}], "community": "e9b9792e-79fb-4b07-b6b4-b9c2bd06d095", "open_access": True, "community_specific": {}}
        r = requests.post(base_url, data=json.dumps(d), headers=headers)
        status_note(str(r.status_code) + " " + str(r.reason))
        status_note('[debug] ' + str(r.json()))
        status_note('created depot <' + r.json()['id'] + '>')
        return str(r.json()['id'])
    except:
        raise


def eudat_add_zip_to_depot(base, deposition_id, zip_name, target_path, token):
    try:
        fsum = files_dir_size(target_path)
        if fsum <= env_max_dir_size_mb:
            # get bucket url:
            headers = {"Content-Type": "application/json"}
            r = requests.get(''.join((base, '/records/', deposition_id, '/draft?access_token=', token)), headers=headers)
            bucket_url = r.json()['links']['files']
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


def eudat_update_md(base, record_id, my_md, access_token):
    try:
        base_url = ''.join((base, "/api/records/", record_id, "/draft?access_token=", access_token))
        # test:
        # test_md = [{"op": "add", "path": "/keywords", "value": ["keyword1", "keyword2"]}]
        headers = {"Content-Type": "application/json-patch+json"}
        r = requests.patch(base_url, data=json.dumps(my_md), headers=headers)
        status_note(str(r.status_code) + " " + str(r.reason))
        status_note(str(r.json()))
    except:
        raise


# Repository Zenodo
def zenodo_create_depot(base, token):
    try:
        # create new empty upload depot:
        headers = {"Content-Type": "application/json"}
        r = requests.post(''.join((base, '/deposit/depositions/?access_token=', token)), data='{}', headers=headers)
        if r.status_code == 201:
            status_note(''.join((str(r.status_code), ' created depot <', str(r.json()['id']),'>')))
        else:
            status_note(r.status_code)
        # return id of newly created depot as response
        return str(r.json()['id'])
    except requests.exceptions.Timeout:
        status_note('server at <'+base+'> timed out')
    except Exception as exc:
        # raise
        status_note(''.join(('! error: ', exc.args[0])))


def zenodo_add_zip_to_depot(base, deposition_id, zip_name, target_path, token):
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


def zenodo_add_files_to_depot(target_path):
    pass
    #todo: -get bucket of depot
    #for root, dirs, files in os.walk(target_path):  # .split(os.sep)[-1]):
    #    for file in files:
    #        #  -put each file into bucket


def zenodo_add_metadata(base, deposition_id, md, token):
    try:
        # official zenodo test md:
        #md = {"metadata": {"title": "My first upload", "upload_type": "poster", "description": "This is my first upload", "creators": [{"name": "Doe, John", "affiliation": "Zenodo"}]}}
        status_note('updating metadata ' + str(md)[:500])
        headers = {"Content-Type": "application/json"}
        r = requests.put(''.join((base, '/deposit/depositions/', str(deposition_id), '?access_token=', token)), data=json.dumps(md), headers=headers)
        if r.status_code == 200:
            status_note(str(r.status_code) + ' updated metadata at <' + str(deposition_id) + '>')
        elif r.status_code == 400:
            status_note(str(r.status_code) + ' ! failed to update metadata at <' + str(deposition_id) + '>. Possibly missing required elements or malformed MD-object.')
            status_note(str(r.text))
        elif r.status_code == 404:
            status_note(str(r.status_code) + ' ! failed to update metadata at <' + str(deposition_id) + '>. URL path not found.')
        else:
            status_note(str(r.status_code))
            status_note(str(r.text))
    except Exception as exc:
        #raise
        status_note(''.join(('! failed to submit metadata: ', exc.args[0])))


def zenodo_create_empty_depot(base, deposition_id, token):
    try:
        r = requests.delete(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)))
        if r.status_code == 204:
            status_note(''.join((str(r.status_code), ' removed depot <', deposition_id, '>')))
        else:
            status_note(r.status_code)
    except Exception as exc:
        raise


def zenodo_get_list_of_files_from_depot(base, deposition_id, token):
    try:
        # get file id from bucket url:
        headers = {"Content-Type": "application/json"}
        r = requests.get(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)),
                         headers=headers)
        file_list = r.json()['files']
        if r.status_code == 200:
            status_note(str(r.status_code) + ". File list of depot " + str(deposition_id) + ":")
            status_note(json.dumps(file_list))
        elif r.status_code == 403:
            status_note(str(r.status_code) + ' ! insufficient access rights <' + str(
                deposition_id) + '>. Cannot delete from an already published deposition.')
            status_note(str(r.text))
        elif r.status_code == 404:
            status_note(str(r.status_code) + ' ! failed to retrieve file at <' + str(deposition_id) + '>')
        else:
            status_note(str(r.status_code))
            status_note(str(r.text))
    except Exception as exc:
        raise
        # status_note(''.join(('! error: ', exc.args[0])))


def zenodo_del_from_depot(base, deposition_id, file_id, token):
    # Zenodo reference:
    # r = requests.delete("https://zenodo.org/api/deposit/depositions/1234/files/21fedcba-9876-5432-1fed-cba987654321?access_token=ACCESS_TOKEN")

    # DELETE /api/deposit/depositions/:id/files/:file_id
    try:
        # get file id from bucket url:
        status_note(''.join(('attempting to delete from <', deposition_id, '>')))
        headers = {"Content-Type": "application/json"}
        r = requests.get(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)),
                         headers=headers)
        # currently: use first and only file
        # todo: delete selected files (parameter is file_id from bucket) OR delete all files form depot
        if file_id is None:
            # no target file specified, hence delete first file
            file_id = r.json()['files'][0]['links']['self'].rsplit('/', 1)[-1]
        # make delete request for that file
        r = requests.delete(''.join((base, '/deposit/depositions/', deposition_id, '/files/', file_id, '?access_token=', token)))
        if r.status_code == 204:
            status_note(str(r.status_code) + ' deleted <' + file_id+ '> from <' + str(deposition_id) + '>')
        elif r.status_code == 403:
            status_note(str(r.status_code) + ' ! insufficient access rights <' + str(deposition_id) + '>. Cannot delete from an already published deposition.')
            status_note(str(r.text))
        elif r.status_code == 404:
            status_note(str(r.status_code) + ' ! failed to retrieve file at <' + str(deposition_id) + '>')
        else:
            status_note(str(r.status_code))
            status_note(str(r.text))
    except Exception as exc:
        raise
        #status_note(''.join(('! error: ', exc.args[0])))


def zenodo_del_depot(base, deposition_id, token):
    # DELETE /api/deposit/depositions/:id
    try:
        r = requests.delete(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)))
        if r.status_code == 204:
            status_note(''.join((str(r.status_code), ' deleted depot <', deposition_id, '>')))
        else:
            status_note(r.status_code)
    except Exception as exc:
        raise
        #status_note(''.join(('! error: ', exc.args[0])))


def db_find_recipient_from_shipment(shipmentid):
    data = db['shipments'].find_one({'id': shipmentid})
    if data is not None:
        if 'recipient' in data:
            return str(data['recipient'])
    else:
        return None


def db_find_depotid_from_shipment(shipmentid):
    data = db['shipments'].find_one({'id': shipmentid})
    if data is not None:
        if 'deposition_id' in data:
            return str(data['deposition_id'])
    else:
        return None


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
def status_note(msgtxt):
    print(''.join(('[shipper] ', str(msgtxt))))


def xstr(s):
    return '' if s is None else str(s)


# Main
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='shipper arguments')
    # args optional:
    parser.add_argument('-t', '--token', help='access token', required=False)
    parser.add_argument('-x', '--testmode', help='remove depot immediately after upload, for testing purpose.', action='store_true', required=False)
    # args parsed:
    args = vars(parser.parse_args())
    arg_test_mode = args['testmode']
    status_note(''.join(('args: ', str(args))))
    # environment vars and defaults
    try:
        with open('config.json') as data_file:
            config = json.load(data_file)
        env_mongo_host = os.environ.get('SHIPPER_MONGODB', config['mongodb_host'])
        env_mongo_db_name = os.environ.get('SHIPPER_MONGO_NAME', config['mongodb_db'])
        env_bottle_host = os.environ.get('SHIPPER_BOTTLE_HOST', config['bottle_host'])
        env_bottle_port = os.environ.get('SHIPPER_BOTTLE_PORT', config['bottle_port'])
        env_repository_zenodo_host = os.environ.get('SHIPPER_REPO_ZENODO_HOST', config['repository_zenodo_host'])
        env_repository_eudat_host = os.environ.get('SHIPPER_REPO_EUDAT_HOST', config['repository_eudat_host'])
        if args['token'] is None:
            env_repository_zenodo_token = os.environ.get('SHIPPER_REPO_ZENODO_TOKEN', config['repository_zenodo_token'])
            env_repository_eudat_token = os.environ.get('SHIPPER_REPO_EUDAT_TOKEN', config['repository_eudat_token'])
        else:
            env_repository_zenodo_token = args['token']
            env_repository_eudat_token = args['token']
        env_file_base_path = os.environ.get('SHIPPER_BASE_PATH', config['base_path'])
        env_max_dir_size_mb = os.environ.get('SHIPPER_MAX_DIR_SIZE', config['max_size_mb'])
        env_session_secret = os.environ.get('SHIPPER_SECRET', config['session_secret'])
        env_user_level_min = os.environ.get('SHIPPER_USERLEVEL_MIN', config['userlevel_min'])
        env_cookie_name = os.environ.get('SHIPPER_COOKIE_NAME', config['cookie_name'])
        env_compendium_files = os.path.join(env_file_base_path, 'compendium')
        env_user_id = None
        status_note(''.join(('loaded config and env:', '\n\tMongoDB: ', env_mongo_host, env_mongo_db_name, '\n\tbottle: ', env_bottle_host, ':', str(env_bottle_port))))
    except:
        raise
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
        status_note(''.join(('starting bottle at ', env_bottle_host, ':', str(env_bottle_port), '...')))
        status_note(base64.b64decode('bGF1bmNoaW5nDQouLS0tLS0tLS0tLS0tLS0uDQp8ICAgICBfLl8gIF8gICAgYC4sX19fX19fDQp8ICAgIChvMnIoKF8oICAgICAgX19fKF8oKQ0KfCAgXCctLTotLS06LS4gICAsJw0KJy0tLS0tLS0tLS0tLS0tJ8#K0DQo=').decode('utf-8'))
        time.sleep(0.1)
        app = WSGILogger(app, [logging.StreamHandler(sys.stdout)], ApacheFormatter())
        run(app=app, host=env_bottle_host, port=env_bottle_port, debug=True)
    except Exception as exc:
        status_note('! error: bottle server could not be started: ' + traceback.format_exc())
        sys.exit(1)
