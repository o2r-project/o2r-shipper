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
from gevent import monkey
monkey.patch_all()
import argparse
import ast
import hashlib
import json
import logging
import traceback
import urllib.parse
import uuid
import bagit
import requests
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=PendingDeprecationWarning)
    from bottle import *
    from pymongo import MongoClient, errors
import inspect
from repos import *
from repos.helpers import *

# Bottle
app = Bottle()
logging.getLogger('bagit').setLevel(logging.CRITICAL)


@app.hook('before_request')
def strip_path():
    # remove trailing slashes
    try:
        request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')
    except Exception as exc:
        status_note(['! error: ', xstr(exc.args[0])], d=is_debug)


@app.route('/api/v1/shipment/<name>', method='GET')
def shipment_get_one(name):
    data = db['shipments'].find_one({'id': name})
    if data is not None:
        response.status = 200
        response.content_type = 'application/json'
        if '_id' in data:
            data.pop('_id', None)
            data.pop('dl_filepath', None)
        return json.dumps(data)
    else:
        status_note(['user requested non-existing shipment ', name], d=is_debug)
        response.status = 404
        response.content_type = 'application/json'
        return json.dumps({'error': 'a compendium with that id does not exist'})


@app.route('/api/v1/shipment', method='GET')
def shipment_get_all():
    try:
        cid = request.query.compendium_id
        find_args = {}
        if cid:
            find_args.update({'compendium_id': cid})
        answer_list = []
        for key in db['shipments'].find(find_args):
            answer_list.append(key['id'])
        response.content_type = 'application/json'
        response.status = 200
        return json.dumps(answer_list)
    except Exception as exc:
        status_note(str(exc), d=is_debug)
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
        global REPO_TARGET
        global REPO_TOKEN
        current_depot = db_find_depotid_from_shipment(shipmentid)
        db_fill_repo_target_and_list(shipmentid)
        headers = {"Content-Type": "application/json"}
        r = requests.get(''.join((REPO_TARGET.get_host(), '/deposit/depositions/', current_depot, '?access_token=', REPO_TOKEN)), headers=headers)
        if 'files' in r.json():
            response.status = 200
            response.content_type = 'application/json'
            return json_dumps({'files': r.json()['files']})
        else:
            response.status = 400
            response.content_type = 'application/json'
            return {'error': 'no files object in repository response'}
    except:
        raise

@app.route('/api/v1/shipment/<shipmentid>/dl', method='GET')
def shipment_get_dl_file(shipmentid):
    try:
        global REPO_TARGET
        global REPO_LIST
        if REPO_LIST is not None:
            # allows for multiple DL sources:
            for repo in REPO_LIST:
                REPO_TARGET = repo
                if hasattr(REPO_TARGET, 'get_id'):
                    # default for now:
                    if REPO_TARGET.get_id() == 'download':
                        break
                    else:
                        REPO_TARGET = None
        if REPO_TARGET is None:
            status_note('! no repository with download feature configured', d=is_debug)
            response.status = 501
            response.content_type = 'application/json'
            return json.dumps({'error': 'no repository with download feature configured'})
        else:
            response.status = 202
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = ''.join(('attachment; filename=', shipmentid, '.zip'))
            p = os.path.normpath(db_find_dl_filepath_from_shipment(shipmentid))
            status_note(str(generate_zipstream(p)), d=is_debug)
            return generate_zipstream(p)
    except Exception as exc:
        status_note(['! error: ', xstr(exc.args[0])], d=is_debug)
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'bad request'})


@app.route('/api/v1/shipment/<shipmentid>/publishment', method='PUT')
def shipment_put_publishment(shipmentid):
    try:
        #! once published, cannot delete in most repos
        global REPO_TARGET
        global REPO_TOKEN
        current_depot = db_find_depotid_from_shipment(shipmentid)
        # get a return of the response of the publish request from the corresponding repo class
        a = REPO_TARGET.publish(current_depot, REPO_TOKEN)
        if not a:
            status_note('! error, failed to call publish', d=is_debug)
            response.status = 500
            response.content_type = 'application/json'
            r = {'id': shipmentid, 'status': 'error'}
            return json.dumps(r)
        else:
            if a == 200 or a == 202:  # note that some repos will return a 202 CREATED
                r = {'id': shipmentid, 'status': 'published'}
                # update shipment data in database
                data = db['shipments'].find_one({'id': shipmentid})
                if data is not None:
                    if 'status' in data:
                        data['status'] = 'published'
                        db['shipments'].update_one({'_id': data['_id']}, {'$set': data}, upsert=True)
                        status_note(['updated shipment object ', xstr(data['_id'])], d=is_debug)
            else:
                r = {'id': shipmentid, 'status': 'error'}
            response.status = 200
            response.content_type = 'application/json'
            return json.dumps(r)
    except:
        raise


@app.route('/api/v1/shipment/<shipmentid>/publishment', method='GET')
def shipment_get_publishment(shipmentid):
    try:
        global REPO_TARGET
        global REPO_TOKEN
        db_fill_repo_target_and_list(shipmentid)
        current_depot = db_find_depotid_from_shipment(shipmentid)
        db_fill_repo_target_and_list(shipmentid)
        REPO_TARGET.get_list_of_files_from_depot(current_depot, REPO_TOKEN)
    except:
        raise


@app.route('/api/v1/shipment/<shipmentid>/files/<fileid>', method='DELETE')
def shipment_del_file_id(shipmentid, fileid):
    # delete specific file in a depot of a shipment
    try:
        global REPO_TARGET
        global REPO_TOKEN
        current_depot = db_find_depotid_from_shipment(shipmentid)
        db_fill_repo_target_and_list(shipmentid)
        if hasattr(REPO_TARGET, 'del_from_depot'):
            if REPO_TARGET.del_from_depot(current_depot, fileid, REPO_TOKEN) == 204:
                response.status = 204
                return '', 204
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
            if cookie is None:
                cookie = request.get_cookie(env_cookie_name)
        except:
            cookie = request.get_cookie(env_cookie_name)
        if cookie is None:
            status_note(['cookie <', env_cookie_name, '> cannot be found!'], d=is_debug)
            response.status = 400
            response.content_type = 'application/json'
            return json.dumps({'error': 'bad request: authentication cookie is missing'})
        cookie = urllib.parse.unquote(cookie)
        user_entitled = session_user_entitled(cookie, env_user_level_min)
        status_note(['validating session with cookie <', cookie, '> and minimum level ', str(env_user_level_min), '. found user <', str(user_entitled), '>'], d=is_debug)
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
                    'update_packaging': request.forms.get('update_packaging'),
                    'recipient': request.forms.get('recipient'),
                    'last_modified': str(datetime.now()),
                    'user': user_entitled,
                    'status': 'to be shipped',
                    'md': new_md
                    }
            current_mongo_doc = db.shipments.insert_one(data)
            status_note(['created shipment object ', xstr(current_mongo_doc.inserted_id)], d=is_debug)
            status = 200
            if data['recipient'] not in REPO_LIST_availables_as_IDstr:
                # that recipient is not available, hence cancel new shipment
                status_note("! error: recipient not available in configured repos", d=is_debug)
                data['status'] = 'error'
                status = 400
            else:
                # set REPO TARGET object from REPO LIST:
                global REPO_TARGET
                global REPO_TOKEN
                db_fill_repo_target_and_list(str(new_id))
                if data['deposition_id'] is None or data['deposition_id'] == {}:
                    # no depot yet, go create one
                    current_compendium = db['compendia'].find_one({'id': data['compendium_id']})
                    if current_compendium is None:
                        status_note('! Invalid compendium id', d=is_debug)
                        data['status'] = 'error'
                        status = 400
                    else:
                        # check if candidate
                        if 'candidate' not in current_compendium:
                            status_note('no <candidate> element in db doc for that compendium', d=is_debug)
                            data['status'] = 'error'
                            status = 403
                        else:
                            if current_compendium['candidate'] is True:
                                status_note('ERC candidate may not be shipped.')
                                data['status'] = 'error'
                                status = 403
                            else:
                                # Aquire path to files via env var and id:
                                compendium_files = os.path.normpath(os.path.join(env_compendium_files, data['compendium_id']))
                                # Determine state of that compendium: Is is a bag or not, zipped, valid, etc:
                                compendium_state = files_scan_path(compendium_files)
                                if not compendium_state == 0:
                                    # Case path does not exist:
                                    if compendium_state == 1:
                                        # Case: Is a bagit bag:
                                        try:
                                            bag = bagit.Bag(compendium_files)
                                            bag.validate()
                                            status_note(['valid bagit bag at <', str(data['compendium_id']), '>'], d=is_debug)
                                        except bagit.BagValidationError as e:
                                            status_note(['! invalid bagit bag at <', str(data['compendium_id']), '>'], d=is_debug)
                                            details = []
                                            for d in e.details:
                                                details.append(str(d))
                                                status_note(xstr(d))
                                            # Exit point for invalid not to be repaired bags
                                            if not strtobool(data['update_packaging']):
                                                data['status'] = 'error'
                                                # update shipment data in database
                                                db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data}, upsert=True)
                                                response.status = 400
                                                response.content_type = 'application/json'
                                                return json.dumps({'error': str(details)})
                                            else:
                                                status_note('updating bagit bag...')
                                                # Open bag object and update:
                                                try:
                                                    bag = bagit.Bag(compendium_files)
                                                    bag.save(manifests=True)
                                                    # Validate a second time to ensure successful update:
                                                    try:
                                                        bag.validate()
                                                        status_note(['Valid updated bagit bag at <', str(data['compendium_id']), '>'], d=is_debug)
                                                    except bagit.BagValidationError:
                                                        status_note('! error while validating updated bag')
                                                        data['status'] = 'error'
                                                        # update shipment data in database
                                                        db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data}, upsert=True)
                                                        response.status = 400
                                                        response.content_type = 'application/json'
                                                        return json.dumps({'error': 'unable to validate updated bag'})
                                                except Exception as e:
                                                    status_note(['! error while bagging: ', str(e)], d=is_debug)
                                    elif compendium_state == 2:
                                        # Case: dir is no bagit bag, needs to become a bag first
                                        try:
                                            bag = bagit.make_bag(compendium_files)
                                            bag.save()
                                            status_note('New bagit bag written')
                                        except Exception as e:
                                            status_note(['! error while bagging: ', xstr(e)], d=is_debug)
                                    #elif compendium_state == 3: # would be dealing with zip files...
                                else:
                                    status_note(['! error, invalid path to compendium: ', compendium_files], d=is_debug)
                                    data['status'] = 'error'
                                    # update shipment data in database
                                    db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data}, upsert=True)
                                    response.status = 400
                                    response.content_type = 'application/json'
                                    return json.dumps({'error': 'invalid path to compendium'})
                                # Continue with zipping and upload
                                # update shipment data in database
                                db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data}, upsert=True)
                                status_note(['updated shipment object ', xstr(current_mongo_doc.inserted_id)], d=is_debug)
                                # Ship to the selected repository
                                file_name = '.'.join((str(data['compendium_id']), 'zip'))
                                if not hasattr(REPO_TARGET, 'create_depot'):
                                    # fetch DL link if available
                                    if hasattr(REPO_TARGET, 'get_dl'):
                                        data['dl_filepath'] = REPO_TARGET.get_dl(file_name, compendium_files)
                                        status_note('started download stream...', d=False)
                                        data['status'] = 'shipped'
                                        db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data},
                                                                upsert=True)
                                        return shipment_get_dl_file(data['id'])
                                    else:
                                        status_note('! error, the selected recipient repo class has no method to create a new depot', d=is_debug)
                                        response.status = 500
                                        response.content_type = 'application/json'
                                        return json.dumps(
                                            {'error': 'recipient repo class misses a method to create a new file depot'})
                                else:
                                    data['deposition_id'] = REPO_TARGET.create_depot(REPO_TOKEN)
                                    # zip all files in dir and submit as zip:
                                    REPO_TARGET.add_zip_to_depot(data['deposition_id'], file_name, compendium_files, REPO_TOKEN, env_max_dir_size_mb)
                                    # Add metadata that are in compendium in db:
                                    if 'metadata' in current_compendium and 'deposition_id' in data:
                                        REPO_TARGET.add_metadata(data['deposition_id'], current_compendium['metadata'], REPO_TOKEN)
                                        data['status'] = 'shipped'
                                        db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data},
                                                            upsert=True)
                # update shipment data in database
                db.shipments.update_one({'_id': current_mongo_doc.inserted_id}, {'$set': data}, upsert=True)
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
        raise
        status_note(['! error: ', xstr(exc)], d=is_debug)
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'error': 'bad request'})
    except Exception as exc:
        raise
        status_note(['! error: ', xstr(exc.args[0])], d=is_debug)
        message = ''.join('bad request:', exc.args[0])
        response.status = 500
        response.content_type = 'application/json'
        return json.dumps({'error': message})


@app.route('/api/v1/recipient', method='GET')
def recipient_get_repo_list():
    try:
        global REPO_LIST
        output = {'recipients': []}
        for repo in REPO_LIST:
            try:
                output['recipients'].append({'id': xstr(repo.get_id()), 'label': repo.get_label()})
            except AttributeError:
                status_note(['! error: repository class ', xstr(repo), ' @ ', xstr(name), ' is unlabled or has no function to return its label.'], d=is_debug)
        response.status = 200
        response.content_type = 'application/json'
        return json.dumps(output)
    except Exception as exc:
        status_note(['! error: ', xstr(exc)], d=is_debug)
        raise


#http errors
#@app.error(404)
#def error404(error):
#    response.content_type = 'application/json'
#    return json.dumps(str(error))


#@app.error(500)
#def error500(error):
#    response.content_type = 'application/json'
#    return json.dumps(str(error))


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
        status_note(['! error: ', exc.args[0]])


def session_get_user(cookie, my_db):
    session_id = cookie.split('.')[0].split('s:')[1]
    if not session_id:
        status_note(['no session found for cookie <', xstr(cookie), '>'])
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
            status_note(['! error: ', str(exc.args[0])])
    else:
        return None


def session_user_entitled(cookie, min_lvl):
    if cookie:
        user_orcid = session_get_user(cookie, db)
        if not user_orcid:
            status_note(['no orcid found for cookie <', xstr(cookie), '>'])
            return None
        this_user = db['users'].find_one({'orcid': user_orcid})
        status_note(['found user <', xstr(this_user), '> for orcid ', user_orcid])
        if this_user:
            if this_user['level'] >= min_lvl:
                return this_user['orcid']
            else:
                return None
        else:
            return None
    else:
        return None


def db_fill_repo_target_and_list(shipmentid):
    global REPO_TARGET
    global REPO_TOKEN
    global REPO_LIST
    global TOKEN_LIST
    if shipmentid is not None:
        data = db['shipments'].find_one({'id': shipmentid})
        if data is not None:
            if 'recipient' in data:
                # check if in repo list
                for repo in REPO_LIST:
                    if data['recipient'].lower() == repo.get_id():
                        REPO_TARGET = repo
                        try:
                            REPO_TOKEN = TOKEN_LIST[repo.get_id()]
                        except:
                            status_note([' ! missing token for', repo.get_id()], d=is_debug)
            else:
                status_note(' ! no recipient specified in db dataset', d=is_debug)
        else:
            status_note(' ! no shipment specified in db dataset', d=is_debug)
    else:
        status_note(' ! error retrieving shipment id and recipient', d=is_debug)


def db_find_depotid_from_shipment(shipmentid):
    data = db['shipments'].find_one({'id': shipmentid})
    if data is not None:
        if 'deposition_id' in data:
            return str(data['deposition_id'])
    else:
        return None


def db_find_dl_filepath_from_shipment(shipmentid):
    data = db['shipments'].find_one({'id': shipmentid})
    if data is not None:
        if 'dl_filepath' in data:
            return str(data['dl_filepath'])
    else:
        return None


def register_repos():
    # dynamically instantiate repositories that are in 'repo' folder
    # 'configured' means both repoclass and token of that repo are available
    global REPO_LIST
    global TOKEN_LIST
    global REPO_LIST_availables_as_IDstr
    if TOKEN_LIST is None:
        status_note('! no repository tokens available, unable to proceed')
        sys.exit(1)
    else:
        try:
            shortlist = []
            for name, obj in inspect.getmembers(sys.modules[__name__]):
                if name.startswith('repo'):
                    for n, class_obj in inspect.getmembers(obj):
                        if n.startswith('RepoClass') and class_obj not in shortlist:
                            shortlist.append(class_obj)
            # unique list without import cross references
            for class_obj in shortlist:
                i = class_obj()
                for listed_token in TOKEN_LIST:
                    if listed_token == i.get_id():
                        # see if function to verify the token exists in repo class:
                        if hasattr(i, 'verify_token'):
                            # only add to list, if valid token:
                            if i.verify_token(TOKEN_LIST[listed_token]):
                                # add instantiated class module for each repo
                                REPO_LIST.append(class_obj())
                                # add name id of that repo to a list for checking recipients available later
                                REPO_LIST_availables_as_IDstr.append(i.get_id())
            if len(REPO_LIST) > 0:
                status_note([str(len(REPO_LIST)), ' repositories configured'])
            else:
                status_note('! no repositories configured')
        except:
            raise


def save_get_from_config(element, config_dict):
    try:
        if config_dict is None:
            return None
        else:
            if element in config_dict:
                return config_dict[element]
            else:
                return None
    except Exception as erc:
        status_note(['! error, ', xstr(exc)], d=is_debug)
        return None


# Main
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='shipper arguments')
    parser.add_argument('-d', '--debug', help='enable debug mode', required=False, action='store_true', default=False)
    parser.add_argument('-t', '--token', type=json.loads, help='access tokens', required=False)
    # args parsed:
    args = vars(parser.parse_args())
    status_note(['args: ', xstr(args)])
    global is_debug
    is_debug = args['debug']
    try:
        if not os.path.isfile('config.json'):
            status_note('configuration file missing. unable to proceed', d=is_debug)
            exit(1)
        else:
            with open('config.json') as data_file:
                config = json.load(data_file)
            env_mongo_host = os.environ.get('SHIPPER_MONGODB', save_get_from_config('mongodb_host', config))
            env_mongo_db_name = os.environ.get('SHIPPER_MONGO_NAME', save_get_from_config('mongodb_db', config))
            env_bottle_host = os.environ.get('SHIPPER_BOTTLE_HOST', save_get_from_config('bottle_host', config))
            env_bottle_port = os.environ.get('SHIPPER_BOTTLE_PORT', save_get_from_config('bottle_port', config))
            TOKEN_LIST = []
            rt = os.environ.get('SHIPPER_REPO_TOKENS', save_get_from_config('repository_tokens', config))
            if type(rt) is str:
                try:
                    TOKEN_LIST = json.loads(os.environ.get('SHIPPER_REPO_TOKENS', save_get_from_config('repository_tokens', config)))
                except:
                    TOKEN_LIST = None
            elif type(rt) is dict:
                TOKEN_LIST = rt
            # overwrite if token is given via:
            if args is not None:
                if 'token' in args:
                    if args['token'] is not None:
                        if args['token'] == {}:
                            status_note('token argument is empty. unable to proceed', d=is_debug)
                            sys.exit(1)
                        else:
                            TOKEN_LIST = args['token']
            # Get environment variables
            env_file_base_path = os.environ.get('SHIPPER_BASE_PATH', save_get_from_config('base_path', config))
            env_max_dir_size_mb = os.environ.get('SHIPPER_MAX_DIR_SIZE', save_get_from_config('max_size_mb', config))
            env_session_secret = os.environ.get('SHIPPER_SECRET', save_get_from_config('session_secret', config))
            env_user_level_min = os.environ.get('SHIPPER_USERLEVEL_MIN', save_get_from_config('userlevel_min', config))
            env_cookie_name = os.environ.get('SHIPPER_COOKIE_NAME', save_get_from_config('cookie_name', config))
            env_compendium_files = os.path.join(env_file_base_path, 'compendium')
            env_user_id = None
            status_note(['loaded environment vars and db config:',
                '\n\tMongoDB: ', env_mongo_host, env_mongo_db_name,
                '\n\tbottle: ', env_bottle_host, ':', env_bottle_port,
                '\n\ttokens: ', TOKEN_LIST], d=is_debug)
            REPO_TARGET = None  # generic repository object
            REPO_LIST = []
            REPO_LIST_availables_as_IDstr = []
            # load repo classes from /repo and register
            register_repos()
            REPO_TOKEN = ''  # generic secret token from remote api
    except OSError as oexc:
        status_note(['! error, unable to process environmental vars. unable to proceed.', xstr(oexc)], d=is_debug)
        sys.exit(1)
    except Exception as exc:
        status_note(['! error, unable to configure shipper. unable to proceed.', xstr(exc)], d=is_debug)
        sys.exit(1)
    # connect to db
    try:
        status_note(['connecting to ', env_mongo_host], d=is_debug)
        client = MongoClient(env_mongo_host, serverSelectionTimeoutMS=12000)
        db = client[env_mongo_db_name]
        status_note(['connected. MongoDB server version: ', client.server_info()['version']], d=is_debug)
    except errors.ServerSelectionTimeoutError as texc:
        status_note(['! error: mongodb timeout error: ', xstr(texc)])
        sys.exit(1)
    except Exception as exc:
        status_note(['! error: mongodb connection error: ', xstr(exc)])
        status_note(traceback.format_exc(), d=is_debug)
        sys.exit(1)
    # start service
    try:
        # shipper logo
        status_note(base64.b64decode('IA0KLi0tLS0tLS0tLS0tLS0tLg0KfCAgICAgXy5fICBfICAgIGAuLF9fX19fXw0KfCAgICAobzJyKChfKCAgICAgIF9fXyhfKCkNCnwgIFwnLS06LS0tOi0uICAgLCcNCictLS0tLS0tLS0tLS0tLSc=').decode('utf-8'))
        time.sleep(0.1)
        # start bottle-gevent
        run(app=app, host=env_bottle_host, port=env_bottle_port, server='gevent', debug=True)
    except Exception as exc:
        status_note(['! error, bottle server could not be started: ', traceback.format_exc()], d=is_debug)
        sys.exit(1)
