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
        return RepoClassZenodo.get_host(self)

    def get_label(self):
        return RepoClassZenodo.get_label(self)

    def get_id(self):
        return RepoClassZenodo.get_id(self)

    def verify_token(self, token):
        return RepoClassZenodo.verify_token(self, token)

    def create_depot(self, token):
        return RepoClassZenodo.create_depot(self, token)

    def add_zip_to_depot(self, deposition_id, zip_name, target_path, token, max_dir_size_mb):
        RepoClassZenodo.add_zip_to_depot(self, deposition_id, zip_name, target_path, token, max_dir_size_mb)

    def add_metadata(self, deposition_id, md, token):
        RepoClassZenodo.add_metadata(self, deposition_id, md, token)

    def publish(self, shipmentid, token):
        RepoClassZenodo.publish(self, shipmentid, token)

    def create_empty_depot(self, deposition_id, token):
        RepoClassZenodo.create_empty_depot(self, deposition_id, token)

    def get_list_of_files_from_depot(self, deposition_id, token):
        RepoClassZenodo.get_list_of_files_from_depot(self, deposition_id, token)

    def del_from_depot(self, deposition_id, file_id, token):
        RepoClassZenodo.del_from_depot(self, deposition_id, file_id, token)

    def del_depot(self, deposition_id, token):
        RepoClassZenodo.del_depot(self, deposition_id, token)