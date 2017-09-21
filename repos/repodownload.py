from .repoclass import *
from .helpers import *

# Download repo surrogate
MD_DB_KEY = ""  # Metadata keyname for database retrieval
HOST = ""
ID = "download"
LABEL = "Download"


class RepoClassDownload(Repo):
    def get_label(self):
        return str(LABEL)

    def get_id(self):
        return str(ID)

    def create_dl(self, path):
        try:
            status_note("test dl: ", xstr(path))
        except:
            raise
