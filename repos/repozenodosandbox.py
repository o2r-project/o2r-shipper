from .repoclass import *
from .repozenodo import *
from .helpers import *


class RepoClassZenodoSandbox(RepoClassZenodo, Repo):
    def __init__(self):
        RepoClassZenodo.__init__(self)
        self.HOST = "https://sandbox.zenodo.org/api"  # api base url
        self.ID = 'zenodo_sandbox'
        self.LABEL = "Zenodo Sandbox"

    def get_host(self):
        global HOST
        Repo.get_host(self.HOST)

    def get_label(self):
        global LABEL
        Repo.get_label(self.LABEL)

    def get_id(self):
        global ID
        Repo.get_id(self.ID)

    def verify_token(self, token):
        RepoClassZenodo.verify_token(self, token)
