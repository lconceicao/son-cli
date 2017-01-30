#  Copyright (c) 2015 SONATA-NFV, UBIWHERE
# ALL RIGHTS RESERVED.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Neither the name of the SONATA-NFV, UBIWHERE
# nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written
# permission.
#
# This work has been performed in the framework of the SONATA project,
# funded by the European Commission under Grant number 671517 through
# the Horizon 2020 and 5G-PPP programmes. The authors would like to
# acknowledge the contributions of their colleagues of the SONATA
# partner consortium (www.sonata-nfv.eu).

import logging
import coloredlogs
import sys
import os
from os.path import expanduser
import yaml

from son.workspace.project import Project

log = logging.getLogger(__name__)


class Workspace:
    WORKSPACE_VERSION = "0.03"

    DEFAULT_WORKSPACE_DIR = os.path.join(expanduser("~"), ".son-workspace")
    DEFAULT_SCHEMAS_DIR = os.path.join(expanduser("~"), ".son-schema")

    # Parameter strings for the configuration descriptor.
    CONFIG_STR_NAME = "name"
    CONFIG_STR_VERSION = "version"
    CONFIG_STR_CATALOGUES_DIR = "catalogues_dir"
    CONFIG_STR_CATALOGUE_NS_DIR = "ns_catalogue"
    CONFIG_STR_CATALOGUE_VNF_DIR = "vnf_catalogue"
    CONFIG_STR_CONFIG_DIR = "configuration_dir"
    CONFIG_STR_PLATFORMS_DIR = "platforms_dir"
    CONFIG_STR_PROJECTS_DIR = "projects_dir"
    CONFIG_STR_SCHEMAS_REMOTE_MASTER = "schemas_remote_master"
    CONFIG_STR_SCHEMAS_LOCAL_MASTER = "schemas_local_master"
    CONFIG_STR_DESCRIPTOR_EXTENSION = "default_descriptor_extension"
    CONFIG_STR_SERVICE_PLATFORMS = "service_platforms"
    CONFIG_STR_DEF_SERVICE_PLATFORM = "default_service_platform"
    CONFIG_STR_LOGGING_LEVEL = "log_level"

    __descriptor_name__ = "workspace.yml"

    def __init__(self, ws_root, ws_name='SONATA workspace', log_level='INFO'):
        self.log_level = log_level
        coloredlogs.install(level=log_level)
        self.ws_root = ws_root
        self.ws_name = ws_name
        self.dirs = dict()
        self.schemas = dict()
        self.default_descriptor_extension = ""
        self.load_default_config()

        # Catalogue servers
        self._service_platforms = dict()
        self._service_platforms['sp1'] = \
            {'url': 'http://sp.int3.sonata-nfv.eu:32001',
             'credentials': {'username': 'sonata',
                             'password': 's0n@t@',
                             'token_file': 'token.txt'}
             }
        self._default_service_platform = 'sp1'

    def load_default_config(self):
        self.dirs[self.CONFIG_STR_CATALOGUES_DIR] = 'catalogues'
        self.dirs[self.CONFIG_STR_CONFIG_DIR] = 'configuration'
        self.dirs[self.CONFIG_STR_PLATFORMS_DIR] = 'platforms'

        self.schemas[self.CONFIG_STR_SCHEMAS_LOCAL_MASTER] = \
            Workspace.DEFAULT_SCHEMAS_DIR

        self.schemas[self.CONFIG_STR_SCHEMAS_REMOTE_MASTER] = \
            "https://raw.githubusercontent.com/sonata-nfv/son-schema/v1.0/"

        # Sub-directories of catalogues
        self.dirs[self.CONFIG_STR_CATALOGUE_NS_DIR] = \
            os.path.join(self.dirs[self.CONFIG_STR_CATALOGUES_DIR],
                         self.CONFIG_STR_CATALOGUE_NS_DIR)

        self.dirs[self.CONFIG_STR_CATALOGUE_VNF_DIR] = \
            os.path.join(self.dirs[self.CONFIG_STR_CATALOGUES_DIR],
                         self.CONFIG_STR_CATALOGUE_VNF_DIR)

        # Projects dir (optional)
        self.dirs[self.CONFIG_STR_PROJECTS_DIR] = 'projects'

        # Extension for YAML - schema/descriptor files
        self.default_descriptor_extension = "yml"

    def create_dirs(self):
        """
        Create the base directory structure for the workspace
        Invoked upon workspace creation.
        :return:
        """

        log.info('Creating workspace at %s', self.ws_root)
        os.makedirs(self.ws_root, exist_ok=False)
        for d in self.dirs:
            path = os.path.join(self.ws_root, self.dirs[d])
            os.makedirs(path, exist_ok=True)

    def create_catalog_sample(self):
        d = {'name': 'My personal catalog',
             'credentials': 'personal'
             }

        ws_file_path = os.path.join(self.ws_root,
                                    self.dirs[self.CONFIG_STR_CATALOGUES_DIR],
                                    'personal.yml')

        with open(ws_file_path, 'w') as ws_file:
            ws_file.write(yaml.dump(d, default_flow_style=False))

    def create_ws_descriptor(self):
        """
        Creates a workspace configuration file descriptor.
        This is triggered by workspace creation and configuration changes.
        :return:
        """
        cfg_d = {self.CONFIG_STR_VERSION:
                 Workspace.WORKSPACE_VERSION,

                 self.CONFIG_STR_NAME:
                 self.ws_name,

                 self.CONFIG_STR_CATALOGUES_DIR:
                 self.dirs[self.CONFIG_STR_CATALOGUES_DIR],

                 self.CONFIG_STR_CONFIG_DIR:
                 self.dirs[self.CONFIG_STR_CONFIG_DIR],

                 self.CONFIG_STR_PLATFORMS_DIR:
                 self.dirs[self.CONFIG_STR_PLATFORMS_DIR],

                 self.CONFIG_STR_SCHEMAS_LOCAL_MASTER:
                 self.schemas[self.CONFIG_STR_SCHEMAS_LOCAL_MASTER],

                 self.CONFIG_STR_SCHEMAS_REMOTE_MASTER:
                 self.schemas[self.CONFIG_STR_SCHEMAS_REMOTE_MASTER],

                 self.CONFIG_STR_SERVICE_PLATFORMS:
                 self._service_platforms,

                 self.CONFIG_STR_DEF_SERVICE_PLATFORM:
                 self._default_service_platform,

                 self.CONFIG_STR_LOGGING_LEVEL:
                 self.log_level,

                 self.CONFIG_STR_DESCRIPTOR_EXTENSION:
                 self.default_descriptor_extension
                 }

        ws_file_path = os.path.join(self.ws_root,
                                    Workspace.__descriptor_name__)

        ws_file = open(ws_file_path, 'w')
        yaml.dump(cfg_d, ws_file, default_flow_style=False)

        return cfg_d

    def create_files(self):
        self.create_ws_descriptor()
        self.create_catalog_sample()

    def check_ws_exists(self):
        ws_file = os.path.join(self.ws_root, Workspace.__descriptor_name__)
        return os.path.exists(ws_file) or os.path.exists(self.ws_root)

    @staticmethod
    def __create_from_descriptor__(ws_root):
        """
        Creates a Workspace object based on a configuration descriptor
        :param ws_root: base path of the workspace
        :return: Workspace object
        """
        ws_filename = os.path.join(ws_root, Workspace.__descriptor_name__)
        if not os.path.isdir(ws_root) or not os.path.isfile(ws_filename):
            log.error("Unable to load workspace descriptor '{}'"
                      .format(ws_filename))
            return None

        ws_file = open(ws_filename)
        ws_config = yaml.load(ws_file)

        if not ws_config[Workspace.CONFIG_STR_VERSION] == \
                Workspace.WORKSPACE_VERSION:
            log.error("Reading a workspace configuration "
                      "with a different version {}"
                      .format(ws_config[Workspace.CONFIG_STR_VERSION]))
            return

        ws = Workspace(ws_root,
                       ws_name=ws_config[Workspace.CONFIG_STR_NAME],
                       log_level=ws_config[Workspace.CONFIG_STR_LOGGING_LEVEL])

        ws.dirs[Workspace.CONFIG_STR_CATALOGUES_DIR] = \
            ws_config[Workspace.CONFIG_STR_CATALOGUES_DIR]

        ws.dirs[Workspace.CONFIG_STR_CONFIG_DIR] = \
            ws_config[Workspace.CONFIG_STR_CONFIG_DIR]

        ws.dirs[Workspace.CONFIG_STR_PLATFORMS_DIR] = \
            ws_config[Workspace.CONFIG_STR_PLATFORMS_DIR]

        ws.schemas[Workspace.CONFIG_STR_SCHEMAS_LOCAL_MASTER] = \
            expanduser(ws_config[Workspace.CONFIG_STR_SCHEMAS_LOCAL_MASTER])

        ws.schemas[Workspace.CONFIG_STR_SCHEMAS_REMOTE_MASTER] = \
            ws_config[Workspace.CONFIG_STR_SCHEMAS_REMOTE_MASTER]

        ws.service_platforms = \
            ws_config[Workspace.CONFIG_STR_SERVICE_PLATFORMS]

        ws.default_service_platform = \
            ws_config[Workspace.CONFIG_STR_DEF_SERVICE_PLATFORM]

        ws.descriptor_extension = \
            ws_config[Workspace.CONFIG_STR_DESCRIPTOR_EXTENSION]

        return ws

    @property
    def default_service_platform(self):
        return self._default_service_platform

    @default_service_platform.setter
    def default_service_platform(self, sp_id):
        self._default_service_platform = sp_id

    @property
    def service_platforms(self):
        return self._service_platforms

    @service_platforms.setter
    def service_platforms(self, sps):
        self._service_platforms = sps

    def get_service_platform(self, sp_id):
        if sp_id not in self.service_platforms.keys():
            return
        return self.service_platforms[sp_id]

    def add_service_platform(self, sp_id):
        if sp_id in self.service_platforms.keys():
            return
        self.service_platforms[sp_id] = {'url': '',
                                         'credentials': {'username': '',
                                                         'password': '',
                                                         'token_file': ''}
                                         }

    def config_service_platform(self, sp_id, url=None, username=None,
                                password=None, token=None, default=None):

        if sp_id not in self.service_platforms.keys():
            return

        sp = self.service_platforms[sp_id]

        if url:
            sp['url'] = url

        if username:
            sp['credentials']['username'] = username

        if password:
            sp['credentials']['password'] = password

        if token:
            sp['credentials']['token_file'] = token

        if default:
            self._default_service_platform = sp_id

        # update workspace config descriptor
        self.create_ws_descriptor()

    def __eq__(self, other):
        """
        Function to assert if two workspaces have the
        same configuration. It overrides the super method
        as is only the need to compare configurations.
        """
        return isinstance(other, type(self)) \
            and self.ws_name == other.ws_name \
            and self.ws_root == other.ws_root \
            and self.dirs == other.dirs \
            and self.schemas == other.schemas


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate new sonata workspaces and project layouts")

    parser.add_argument(
        "--init",
        help="Create a new sonata workspace",
        action="store_true")

    parser.add_argument(
        "--workspace",
        help="location of existing (or new) workspace. "
             "If not specified will assume '{}'"
             .format(Workspace.DEFAULT_WORKSPACE_DIR),
        required=False)

    parser.add_argument(
        "--project",
        help="create a new project at the specified location",
        required=False)

    parser.add_argument(
        "--debug",
        help="increases logging level to debug",
        required=False,
        action="store_true")

    args = parser.parse_args()

    log_level = "INFO"
    if args.debug:
        log_level = "DEBUG"
        coloredlogs.install(level=log_level)

    # Ensure that one argument is given (--init, --workspace or --project)
    if not args.init and not args.workspace and not args.project:
        parser.print_help()
        return

    # Ensure that argument --workspace is not alone
    if not args.init and args.workspace and not args.project:
        parser.print_help()
        return

    # If workspace arg is not given, create a workspace in user home
    if args.workspace is None:
        ws_root = Workspace.DEFAULT_WORKSPACE_DIR

        # If a workspace already exists at user home, throw an error and quit
        if args.init and os.path.isdir(ws_root):
            print("A workspace already exists in {}. "
                  "Please specify a different location.\n"
                  .format(ws_root), file=sys.stderr)
            exit(1)

    else:
        ws_root = expanduser(args.workspace)

    if args.init:
        ws = Workspace(ws_root, log_level=log_level)
        if ws.check_ws_exists():
            print("A workspace already exists at the "
                  "specified location, exiting",
                  file=sys.stderr)
            exit(1)

        log.debug("Attempting to create a new workspace")
        cwd = os.getcwd()
        ws.create_dirs()
        ws.create_files()
        os.chdir(cwd)
        log.debug("Workspace created.")
    else:
        ws = Workspace.__create_from_descriptor__(ws_root)
        if not ws:
            print("Could not find a SONATA workspace "
                  "at the specified location",
                  file=sys.stderr)
            exit(1)

    if args.project is not None:
        log.debug("Attempting to create a new project")

        prj_root = os.path.expanduser(args.project)
        proj = Project(ws, prj_root)
        proj.create_prj()

        log.debug("Project created.")
