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

import argparse
import json
import os

import requests


def get_user(token):
    # retrieve user from o2r api
    pass


def create_depot(base, token):
    try:
        # create new empty upload depot:
        headers = {"Content-Type": "application/json"}
        r = requests.post(''.join((base, '/deposit/depositions/?access_token=', token)), data='{}', headers=headers)
        if r.status_code == 201:
            status_note(str(r.status_code)+' created depot <' + str(r.json()['id']) + '>')
        else:
            status_note(r.status_code)
        #deposition_id = r.json()['id']
        return str(r.json()['id'])
    except:
        raise


def add_to_depot(base, deposition_id, file_path, token):
    try:
        # get bucket url:
        headers = {"Content-Type": "application/json"}
        r = requests.get(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)), headers=headers)
        bucket_url = r.json()['links']['bucket']
        if r.status_code == 200:
            status_note(str(r.status_code)+' using bucket <' + bucket_url + '>')
        else:
            status_note(r.status_code)
        # upload file into bucket:
        headers = {"Content-Type": "application/octet-stream"}
        stream = open(file_path, 'rb').read()
        r = requests.put("".join((bucket_url, '/', os.path.basename(file_path), '?access_token=', token)), data=stream, headers=headers)
        if r.status_code == 200:
            status_note(str(r.status_code)+' uploaded file <'+os.path.basename(file_path)+'> to depot <'+deposition_id+'> '+r.json()['checksum'])
        else:
            status_note(r.status_code)
    except:
        raise


def add_metadata(base, deposition_id, md, token):
    try:
        headers = {"Content-Type": "application/json"}
        r = requests.put(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)), data=json.dumps(md), headers=headers)
        if r.status_code == 200:
            status_note(str(r.status_code)+' updated metadata at <'+deposition_id+'>')
        else:
            status_note(r.status_code)
    except:
        raise


def del_from_depot(base, deposition_id, token):
    pass


def del_depot(base, deposition_id, token):
    try:
        r = requests.delete(''.join((base, '/deposit/depositions/', deposition_id, '?access_token=', token)))
        if r.status_code == 204:
            status_note(str(r.status_code)+' removed depot ' + '<' + deposition_id + '>')
        else:
            status_note(r.status_code)
    except:
        raise


def status_note(msg):
    print(''.join(('[shipper] ', str(msg))))


# main:
if __name__ == "__main__":
    status_note('initializing')
    parser = argparse.ArgumentParser(description='description')
    parser.add_argument('-i', '--inputfilepath', help='input file abs path', required=True)
    parser.add_argument('-t', '--token', help='accesstoken', required=True)
    parser.add_argument('-d', '--depositionid', help='deposition id to work with. leave out for new upload depot', required=False)
    parser.add_argument('-m', '--metadata', help='metadata json to add or modify', required=False)
    parser.add_argument('-b', '--baseurl', help='api endpoint as url. leave out to use zenodo sandbox', required=False)
    parser.add_argument('-x', '--testmode', help='remove depot immediately after upload, for testing purpose.', action='store_true', required=False)
    args = parser.parse_args()
    args_dict = vars(args)
    input_filepath = args_dict['inputfilepath']
    access_token = args_dict['token']
    deposition = args_dict['depositionid']
    meta = args_dict['metadata']
    base_url = args_dict['baseurl']
    test_mode = args_dict['testmode']
    if not base_url:
        base_url = 'https://sandbox.zenodo.org/api'
    if not deposition:
        # have to build new depot:
        deposition = create_depot(base_url, access_token)
        add_to_depot(base_url, deposition, input_filepath, access_token)
    else:
        # will use existing depot:
        my_depot_id = deposition
        add_to_depot(base_url, deposition, input_filepath, access_token)
    if meta:
        try:
            # path to file that has the json:
            with open(os.path.abspath(meta), encoding='utf-8') as meta_file:
                m = json.load(meta_file)
            add_metadata(base_url, deposition, m, access_token)
        except:
            raise
    if test_mode:
        # instant removal to avoid spamming upload folder:
        del_depot(base_url, deposition, access_token)
