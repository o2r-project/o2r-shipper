from .repoclass import *
from .helpers import *


# Download repo surrogate
class RepoClassDownload(Repo):
    def __init__(self):
        self.HOST = ""
        self.ID = 'download'
        self.LABEL = "Download"

    def get_host(self):
        return str(self.HOST)

    def get_label(self):
        return str(self.LABEL)

    def get_id(self):
        return str(self.ID)

    def verify_token(self, token):
        # always valid, since repo is a surrogate without token
        status_note(['<', self.ID, '> (surrogate) OK'])
        return True

    def get_dl(self, zip_name, target_path):
        return xstr(target_path)

    def add_metadata(self, deposition_id, md, token):
        pass
