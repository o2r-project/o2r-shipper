from .repoclass import *
from .helpers import *

# Download repo surrogate
HOST = ""
ID = "download"
LABEL = "Download"


class RepoClassDownload(Repo):
    def get_host(self):
        return str(HOST)

    def get_label(self):
        return str(LABEL)

    def get_id(self):
        return str(ID)

    def verify_token(self, token):
        global ID
        # always valid, since repo is a surrogate without token
        status_note(['<', ID, '> (surrogate) OK'])
        return True

    def get_dl(self, zip_name, target_path):
        return xstr(target_path)


    def create_depot(self, token):
        # no token needed, since repos is surrogate
        # function is required to mimic the other repos
        return None
        pass

    def add_zip_to_depot(self, deposition_id, zip_name, target_path, token, max_dir_size_mb):
        # not needed, will be streamed
        # todo: return DL link
        pass

    def add_metadata(self, deposition_id, md, token):
        pass
