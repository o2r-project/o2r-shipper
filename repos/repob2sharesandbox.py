from .repoclass import *
from .helpers import *

# Repository Eudat b2share Sandbox
HOST = "https://trng-b2share.eudat.eu/api"  # api base url
ID = "b2share_sandbox"
LABEL = "b2share Sandbox"


class RepoClassEudat(Repo):
    def get_host(self):
        return str(HOST)

    def get_label(self):
        return str(LABEL)

    def get_id(self):
        return str(ID)

    def verify_token(self, token):
        try:
            global HOST
            global ID
            # get file id from bucket url:
            r = requests.get(''.join((HOST, '/records', '?access_token=', token)), params={'access_token': token}, verify=True, timeout=3)
            status_note(['<', ID, '> token verification: ', xstr(r.status_code), ' ', xstr(r.reason)])
            if r.status_code == 200:
                return True
            elif r.status_code == 401:
                return False
        except:
            raise

    def create_depot(self, access_token):
        global HOST
        try:
            headers = {"Content-Type": "application/json"}
            base_url = ''.join((HOST, "/records/?access_token=", access_token))
            # test md
            d = {"titles": [{"title": "TestRest"}], "community": "e9b9792e-79fb-4b07-b6b4-b9c2bd06d095",
                 "open_access": True, "community_specific": {}}
            r = requests.post(base_url, data=json.dumps(d), headers=headers)
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            status_note(['[debug] ', xstr(r.json())])  # debug
            status_note(['created depot <', xstr(r.json()['id']), '>'])
            return str(r.json()['id'])
        except:
            raise

    def add_zip_to_depot(self, deposition_id, zip_name, target_path, token):
        global HOST
        try:
            fsum = files_dir_size(target_path)
            if fsum <= env_max_dir_size_mb:
                # get bucket url:
                headers = {"Content-Type": "application/json"}
                r = requests.get(''.join((HOST, '/records/', deposition_id, '/draft?access_token=', token)),
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
                    status_note([xstr(r.status_code), ' uploaded file <', zip_name, '> to depot <', deposition_id, '> ',
                                 xstr(r.json()['checksum'])])
                else:
                    status_note(xstr(r.text))
            else:
                status_note("! error: file not found")
        except Exception as exc:
            # raise
            status_note(['! error: ', xstr(exc.args[0])])

    def update_md(self, record_id, my_md, access_token):
        global HOST
        try:
            base_url = ''.join((HOST, "/api/records/", record_id, "/draft?access_token=", access_token))
            # test:
            # test_md = [{"op": "add", "path": "/keywords", "value": ["keyword1", "keyword2"]}]
            headers = {"Content-Type": "application/json-patch+json"}
            r = requests.patch(base_url, data=json.dumps(my_md), headers=headers)
            status_note([xstr(r.status_code), ' ', xstr(r.reason)])
            status_note(xstr(r.json()))
        except:
            raise
