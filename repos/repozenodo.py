from .repoclass import *
from .helpers import *


class RepoClassZenodo(Repo):
    def __init__(self):
        self.HOST = "https://zenodo.org/api"  # api base url
        self.LABEL = "Zenodo"
        self.ID = 'zenodo'

    def get_host(self):
        return self.HOST

    def get_label(self):
        return self.LABEL

    def get_id(self):
        return self.ID

    def verify_token(self, token):
        try:
            # get file id from bucket url:
            headers = {'Content-Type': 'application/json',
                       'Authorization': ''.join(('Bearer ', token))}
            r = requests.get(''.join((self.HOST, '/deposit/depositions')), headers=headers, verify=True, timeout=3)
            status_note(['<', self.ID, '> token verification: ', xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 200:
                return True
            elif r.status_code == 401:
                return False
        except Exception as exc:
            status_note(['! error, ', str(exc)])
            return False
            #raise

    def create_depot(self, token):
        try:
            # create new empty upload depot:
            headers = {'Content-Type': 'application/json',
                       'Authorization': ''.join(('Bearer ', token))}
            r = requests.post(''.join((self.HOST, '/deposit/depositions')), data='{}', headers=headers)
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 201:
                status_note(['created depot <', xstr(r.json()['id']), '>'])
            else:
                status_note(xstr(r.status_code))
            # return id of newly created depot as response
            return str(r.json()['id'])
        except requests.exceptions.Timeout:
            status_note(['server at <', xstr(base), '> timed out'])
        except Exception as exc:
            # raise
            status_note(['! error: ', xstr(exc)])

    def add_zip_to_depot(self, deposition_id, zip_name, target_path, token, max_dir_size_mb):
        #todo: try out zipstream here, too
        try:
            fsum = files_dir_size(target_path)
            if fsum <= max_dir_size_mb:
                # get bucket url:
                headers = {'Content-Type': 'application/json',
                           'Authorization': ''.join(('Bearer ', token))}
                r = requests.get(''.join((self.HOST, '/deposit/depositions/', deposition_id)),
                                 headers=headers)
                status_note([xstr(r.status_code), ' ', xstr(r.reason)])
                bucket_url = ''
                if r.status_code == 200:
                    if 'links' in r.json():
                        if 'bucket' in r.json()['links']:
                            bucket_url = r.json()['links']['bucket']
                            status_note(['using bucket <', bucket_url, '>'])
                else:
                    status_note(xstr(r.text))
                # upload file into bucket:
                headers = {"Content-Type": "application/octet-stream"}
                # create a filelike object in memory
                filelike = BytesIO()
                # fill memory object into zip constructor
                zipf = zipfile.ZipFile(filelike, 'w', zipfile.ZIP_DEFLATED)
                # walk target dir recursively
                for root, dirs, files in os.walk(target_path):  # .split(os.sep)[-1]):
                    for file in files:
                        zipf.write(os.path.join(root, file),
                                   arcname=os.path.relpath(os.path.join(root, file), target_path))
                zipf.close()
                filelike.seek(0)
                r = requests.put(''.join((bucket_url, '/', zip_name, '?access_token=', token)), data=filelike.read(),
                                 headers=headers)
                status_note([xstr(r.status_code), ' ', xstr(r.reason)])
                if r.status_code == 200:
                    status_note(
                        ['uploaded file <', zip_name, '> to depot <', deposition_id, '> ', str(r.json()['checksum'])])
            else:
                status_note('! error: file not found')
        except Exception as exc:
            # raise
            status_note(['! error: ', xstr(exc.args[0])])

    def add_files_to_depot(target_path):
        pass
        # todo: -get bucket of depot
        # for root, dirs, files in os.walk(target_path):  # .split(os.sep)[-1]):
        #    for file in files:
        #        #  -put each file into bucket

    def add_metadata(self, deposition_id, md, token):
        try:
            # official zenodo test md:
            # md = {"metadata": {"title": "My first upload", "upload_type": "poster", "description": "This is my first upload", "creators": [{"name": "Doe, John", "affiliation": "Zenodo"}]}}
            status_note(['updating metadata ', xstr(md)[:500]])
            try:
                md = md[self.ID]
            except Exception as e:
                status_note(['! error while unwrapping MD object from db: ', xstr(e)])
            headers = {'Content-Type': 'application/json',
                       'Authorization': ''.join(('Bearer ', token))}
            r = requests.put(''.join((self.HOST, '/deposit/depositions/', str(deposition_id))),
                             data=json.dumps(md), headers=headers)
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 200:
                status_note(['updated metadata at <', str(deposition_id), '>'])
            elif r.status_code == 400:
                status_note(['! failed to update metadata at <', str(deposition_id), '>'])
                if 'message' in r.json() and 'errors' in r.json():
                    for err in r.json()['errors']:
                        status_note([xstr(r.json()['message']), ': ', xstr(err)])
            elif r.status_code == 404:
                status_note(['! failed to update metadata at <', xstr(deposition_id), '>. URL path not found.'])
            elif r.status_code == 500:
                status_note(['! failed to update metadata. <', self.ID, '> at <', self.HOST, '> says ', xstr(r.status_code), ' ', xstr(r.reason)])
            else:
                status_note(['! error updating metadata', xstr(r.text)])
        except Exception as exc:
            # raise
            status_note(['! failed to submit metadata: ', xstr(exc.args[0])])

    def publish(self, shipmentid, token):
        try:
            current_depot = db_find_depotid_from_shipment(shipmentid)
            headers = {'Authorization': ''.join(('Bearer ', token))}
            r = requests.post(''.join((self.HOST, '/deposit/depositions/', current_depot, '/actions/publish')), headers=headers)
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 202:
                db.shipments.update_one({'id': shipmentid}, {'$set': {'status': 'published'}}, upsert=True)
                if 'doi_url' in r.json():
                    db.shipments.update_one({'id': shipmentid}, {'$set': {'doi_url': r.json()['doi_url']}}, upsert=True)
                response.status = r.status_code
                response.content_type = 'application/json'
                return {'id': shipmentid, 'status': 'published'}
            else:
                status_note('unknown recipient')
        except:
            raise

    def create_empty_depot(self, deposition_id, token):
        try:
            headers = {'Authorization': ''.join(('Bearer ', token))}
            r = requests.delete(''.join((self.HOST, '/deposit/depositions/', deposition_id)), headers=headers)
            if r.status_code == 204:
                status_note([xstr(r.status_code), ' removed depot <', deposition_id, '>'])
            else:
                status_note(xstr(r.status_code))
        except Exception as exc:
            raise

    def get_list_of_files_from_depot(self, deposition_id, token):
        try:
            # get file id from bucket url:
            headers = {'Content-Type': 'application/json',
                       'Authorization': ''.join(('Bearer ', token))}
            r = requests.get(''.join((self.HOST, '/deposit/depositions/', deposition_id)), headers=headers)

            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 200:
                if 'files' in r.json():
                    file_list = r.json()['files']
                    status_note(['File list of depot', str(deposition_id), ':'])
                    status_note(xstr(json.dumps(file_list)))
            elif r.status_code == 403:
                status_note(['! insufficient access rights <', str(deposition_id),
                             '>. Cannot delete from an already published deposition.'])
                status_note(xstr(r.text))
            elif r.status_code == 404:
                status_note(['! failed to retrieve file at <', str(deposition_id), '>'])
            else:
                status_note(xstr(r.text))
        except Exception as exc:
            raise

    def del_from_depot(self, deposition_id, file_id, token):
        # Zenodo reference:
        # r = requests.delete("https://zenodo.org/api/deposit/depositions/1234/files/21fedcba-9876-5432-1fed-cba987654321?access_token=ACCESS_TOKEN")
        # DELETE /api/deposit/depositions/:id/files/:file_id
        try:
            # get file id from bucket url:
            status_note(['attempting to delete from <', deposition_id, '>'])
            headers = {"Content-Type": "application/json"}
            r = requests.get(''.join((self.HOST, '/deposit/depositions/', deposition_id, '?access_token=', token)),
                             headers=headers)
            # currently: use first and only file
            # todo: delete selected files (parameter is file_id from bucket) OR delete all files form depot
            if file_id is None:
                # no target file specified, hence delete first file
                file_id = r.json()['files'][0]['links']['self'].rsplit('/', 1)[-1]
            # make delete request for that file
            r = requests.delete(
                ''.join((base, '/deposit/depositions/', deposition_id, '/files/', file_id, '?access_token=', token)))
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 204:
                status_note(['deleted <', xstr(file_id), '> from <', str(deposition_id), '>'])
            elif r.status_code == 403:
                status_note(['! insufficient access rights <', str(deposition_id),
                             '>. Cannot delete from an already published deposition.'])
                status_note(xstr(r.text))
            elif r.status_code == 404:
                status_note(['failed to retrieve file at >', str(deposition_id), '>'])
            else:
                status_note(xstr(r.text))
        except Exception as exc:
            raise

    def del_depot(self, deposition_id, token):
        # DELETE /api/deposit/depositions/:id
        try:
            headers = {"Content-Type": "application/json"}
            r = requests.delete(''.join((self.HOST, '/deposit/depositions/', deposition_id), headers=headers))
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 204:
                status_note(['deleted depot <', deposition_id, '>'])
            else:
                status_note(xstr(r.status_code))
        except Exception as exc:
            raise
