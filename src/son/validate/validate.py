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

import sys
import inspect
import coloredlogs
import networkx as nx
from son.schema.validator import SchemaValidator
from son.workspace.workspace import Workspace, Project
from son.validate.objects import DescriptorStorage
from son.validate.util import *

log = logging.getLogger(__name__)


class Validator(object):

    CXPT_KEY_SEPARATOR = ':'         # connection point key separator

    def __init__(self, workspace=None, log_level='debug'):
        """
        Initialize the Validator.
        A workspace may be provided for an easy parameter configuration,
        such as location and extension of descriptors, verbosity level, etc.
        :param workspace: SONATA workspace object
        :param log_level: verbosity level
        """
        self._workspace = workspace
        self._log_level = log_level
        self._syntax = True
        self._integrity = True
        self._topology = True

        # create "virtual" workspace if not provided (don't actually create
        # file structure)
        if not self._workspace:
            self._workspace = Workspace('.', log_level=log_level)

        # load configuration from workspace
        self._dext = self._workspace.default_descriptor_extension
        self._dpath = '.'
        self._log_level = self._workspace.log_level

        # configure logs
        coloredlogs.install(level=self._log_level)

        # storage descriptors
        self._storage = DescriptorStorage(log_level=self._log_level)

        # syntax validation
        self._schema_validator = SchemaValidator(self._workspace)

        # number of warnings
        self._warnings_count = 0

    @property
    def warnings_count(self):
        """
        Provides the number of warnings given during validation.
        This property should be read after the validation process.
        :return:
        """
        return self._warnings_count

    def configure(self, syntax=None, integrity=None, topology=None,
                  dpath=None, dext=None, log_level=None):
        """
        Configure parameters for validation. It is recommended to call this
        function before performing a validation.
        :param syntax: specifies whether to validate syntax
        :param integrity: specifies whether to validate integrity
        :param topology: specifies whether to validate network topology
        :param dpath: directory to search for function descriptors (VNFDs)
        :param dext: extension of descriptor files (default: 'yml')
        :param log_level: verbosity level of logger
        """
        # assign parameters
        if syntax is not None:
            self._syntax = syntax
        if integrity is not None:
            self._integrity = integrity
        if topology is not None:
            self._topology = topology
        if dext is not None:
            self._dext = dext
        if dpath is not None:
            self._dpath = dpath
        if log_level:
            coloredlogs.set_level(log_level)

    def _assert_configuration(self):
        """
        Ensures that the current configuration is compatible with the
        validation to perform. If issues are found the application is
        interrupted with the appropriate error.
        This is an internal function which must be invoked only by:
            - 'validate_project'
            - 'validate_service'
            - 'validate_function'
        """
        # ensure this function is called by specific functions
        caller = inspect.stack()[1][3]
        if caller != 'validate_function' and caller != 'validate_service' and \
           caller != 'validate_project':
            log.error("Cannot assert a correct configuration. Validation "
                      "scope couldn't be determined. Aborting")
            sys.exit(1)

        # general rules - apply to all validations
        if self._integrity and not self._syntax:
            log.error("Cannot validate integrity without validating syntax "
                      "first. Aborting.")
            sys.exit(1)

        if self._topology and not self._integrity:
            log.error("Cannot validate topology without validating integrity "
                      "first. Aborting.")
            sys.exit(1)

        if caller == 'validate_project':
            pass

        elif caller == 'validate_service':
            # check SERVICE validation parameters
            if (self._integrity or self._topology) and not \
               (self._dpath and self._dext):
                log.critical("Invalid validation parameters. To validate the "
                             "integrity or topology of a service both "
                             "'--dpath' and '--dext' parameters must be "
                             "specified.")
                sys.exit(1)

        elif caller == 'validate_function':
            pass

    def validate_project(self, project):
        """
        Validate a SONATA project.
        By default, it performs the following validations: syntax, integrity
        and network topology.
        :param project: SONATA project
        :return: True if all validations were successful, False otherwise
        """
        self._assert_configuration()

        log.info("Validating project '{0}'".format(project.project_root))
        log.info("... syntax: {0}, integrity: {1}, topology: {2}"
                 .format(self._syntax, self._integrity, self._topology))

        # retrieve project configuration
        self._dpath = project.vnfd_root
        self._dext = project.descriptor_extension

        # load all project descriptors present at source directory
        log.debug("Loading project service")
        nsd_file = Validator._load_project_service_file(project)

        return self.validate_service(nsd_file)

    def validate_service(self, nsd_file):
        """
        Validate a SONATA service.
        By default, it performs the following validations: syntax, integrity
        and network topology.
        :param nsd_file: service descriptor filename
        :return: True if all validations were successful, False otherwise
        """
        self._assert_configuration()

        log.info("Validating service '{0}'".format(nsd_file))
        log.info("... syntax: {0}, integrity: {1}, topology: {2}"
                 .format(self._syntax, self._integrity, self._topology))

        service = self._storage.create_service(nsd_file)
        if not service:
            log.critical("Failed to read the service descriptor of file '{}'"
                         .format(nsd_file))
            return

        # validate service syntax
        if self._syntax and not self._validate_service_syntax(service):
            return

        if self._integrity and not self._validate_service_integrity(service):
            return

        if self._topology and not self._validate_service_topology(service):
            return

        return True

    def validate_function(self, vnfd_path):
        """
        Validate one or multiple SONATA functions (VNFs).
        By default, it performs the following validations: syntax, integrity
        and network topology.
        :param vnfd_path: function descriptor (VNFD) filename or
                          a directory to search for VNFDs
        :return: True if all validations were successful, False otherwise
        """
        self._assert_configuration()

        # validate multiple VNFs
        if os.path.isdir(vnfd_path):
            log.info("Validating functions in path '{0}'".format(vnfd_path))

            vnfd_files = list_files(vnfd_path, self._dext)
            for vnfd_file in vnfd_files:
                if not self.validate_function(vnfd_file):
                    return
            return True

        log.info("Validating function '{0}'".format(vnfd_path))
        log.info("... syntax: {0}, integrity: {1}, topology: {2}"
                 .format(self._syntax, self._integrity, self._topology))

        function = self._storage.create_function(vnfd_path)
        if not function:
            log.critical("Couldn't store VNF of file '{0}'".format(vnfd_path))
            return

        if self._syntax and not self._validate_function_syntax(function):
            return

        if self._integrity and not self._validate_function_integrity(function):
            return

        if self._topology and not self._validate_function_topology(function):
            return

        return True

    def _validate_service_syntax(self, service):
        """
        Validate a the syntax of a service (NS) against its schema.
        :param service: service to validate
        :return: True if syntax is correct, None otherwise
        """
        log.info("Validating syntax of service '{0}'".format(service.id))
        if not self._schema_validator.validate(
              service.content, SchemaValidator.SCHEMA_SERVICE_DESCRIPTOR):
            log.error("Invalid syntax in service: '{0}'".format(service.id))
            return
        return True

    def _validate_function_syntax(self, function):
        """
        Validate the syntax of a function (VNF) against its schema.
        :param function: function to validate
        :return: True if syntax is correct, None otherwise
        """
        log.info("Validating syntax of function '{0}'".format(function.id))
        if not self._schema_validator.validate(
              function.content, SchemaValidator.SCHEMA_FUNCTION_DESCRIPTOR):
            log.error("Invalid syntax in function '{0}'".format(function.id))
            return
        return True

    def _validate_service_integrity(self, service):
        """
        Validate the integrity of a service (NS).
        It checks for inconsistencies in the identifiers of connection
        points, virtual links, etc.
        :param service: service to validate
        :return: True if integrity is correct
        :param service:
        :return:
        """
        log.info("Validating integrity of service '{0}'".format(service.id))

        # get referenced function descriptors (VNFDs)
        if not self._load_service_functions(service):
            log.error("Failed to read service function descriptors")
            return

        # load service interfaces
        if not service.load_interfaces():
            log.error("Couldn't load the interfaces of service id='{0}'"
                      .format(service.id))
            return

        # load service links
        if not service.load_links():
            log.error("Couldn't load the links of service id='{0}'"
                      .format(service.id))
            return

        # verify integrity between vnf_ids and links
        for lid, link in service.links.items():
            for iface in link.iface_pair:
                if iface not in service.interfaces:
                    iface_tokens = iface.split(':')
                    if len(iface_tokens) != 2:
                        log.error("Connection point '{0}' in virtual link "
                                  "'{1}' is not defined"
                                  .format(iface, lid))
                        return
                    vnf_id = iface_tokens[0]
                    function = service.mapped_function(vnf_id)
                    if not function:
                        log.error("Function (VNF) of vnf_id='{0}' declared "
                                  "in connection point '{0}' in virtual link "
                                  "'{1}' is not defined"
                                  .format(vnf_id, iface, lid))
                        return

        # validate service function descriptors (VNFDs)
        for fid, function in service.functions.items():
            if not self.validate_function(function.filename):
                return

        return True

    def _validate_function_integrity(self, function):
        """
        Validate the integrity of a function (VNF).
        It checks for inconsistencies in the identifiers of connection
        points, virtual deployment units (VDUs), ...
        :param function: function to validate
        :return: True if integrity is correct
        """
        log.info("Validating integrity of function descriptor '{0}'"
                 .format(function.id))

        # load function interfaces
        if not function.load_interfaces():
            log.error("Couldn't load the interfaces of function id='{0}'"
                      .format(function.id))
            return

        # load units
        if not function.load_units():
            log.error("Couldn't load the units of function id='{0}'"
                      .format(function.id))
            return

        # load interfaces of units
        if not function.load_unit_interfaces():
            log.error("Couldn't load unit interfaces of function id='{0}'"
                      .format(function.id))
            return

        # load function links
        if not function.load_links():
            log.error("Couldn't load the links of function id='{0}'"
                      .format(function.id))
            return

        # verify integrity between unit interfaces and units
        for lid, link in function.links.items():
            for iface in link.iface_pair:
                iface_tokens = iface.split(':')
                if len(iface_tokens) > 1:
                    print(function.units.keys())
                    if iface_tokens[0] not in function.units.keys():
                        log.error("Invalid interface id='{0}' of link id='{1}'"
                                  ": Unit id='{2}' is not defined"
                                  .format(iface, lid, iface_tokens[0]))
                        return
        return True

    def _validate_service_topology(self, service):
        """
        Validate the network topology of a service.
        :return:
        """
        log.info("Validating topology of service '{0}'".format(service.id))

        # build service topology graph
        service.build_topology_graph(deep=False, interfaces=True,
                                     link_type='e-line')

        log.debug("Built topology graph of service '{0}': {1}"
                  .format(service.id, service.graph.edges()))

        if nx.is_connected(service.graph):
            log.debug("Topology graph of service '{0}' is connected"
                      .format(service.id))
        else:
            log.warning("Topology graph of service '{0}' is disconnected"
                        .format(service.id))

        # load forwarding paths
        if not service.load_forwarding_paths():
            log.error("Couldn't load service forwarding paths")
            return

        # analyse forwarding paths
        for fpid, fw_path in service.fw_paths.items():
            trace = service.trace_path(fw_path)
            if 'BREAK' in trace:
                log.warning("The forwarding path id='{0}' is invalid for the "
                            "specified topology. {1} breakpoints were "
                            "found in the path: {2}"
                            .format(fpid, trace.count('BREAK'), trace))
                # skip further analysis on this path
                continue

            # path is valid in specified topology, let's check for cycles
            fpg = nx.Graph()
            fpg.add_path(trace)
            cycles = Validator._find_graph_cycles(fpg, fpg.nodes()[0])
            if cycles and len(cycles) > 0:
                log.warning("Found cycles forwarding path id={0}: {1}"
                            .format(fpid, cycles))
                self._warnings_count += 1

        # TODO: find a more coherent method to do this
        nx.write_graphml(service.graph, "{0}.graphml".format(service.id))
        return True

    def _validate_function_topology(self, function):
        """
        Validate the network topology of a function.
        It builds the topology graph of the function, including VDU
        connections.
        :param function: function to validate
        :return: True if topology doesn't present issues
        """
        log.info("Validating topology of function '{0}'"
                 .format(function.id))

        # build function topology graph
        function.build_topology_graph(link_type='e-line')

        # # build function topology graph
        # ftg = self._build_function_graph(function)
        # if not ftg:
        #     return
        #
        log.debug("Built topology graph of function '{0}': {1}"
                  .format(function.id, function.graph.edges()))
        #
        # # store function topology graph
        # function.graph = ftg
        #

        # check for path cycles
        cycles = Validator._find_graph_cycles(function.graph,
                                              function.graph.nodes()[0])
        if cycles and len(cycles) > 0:
            log.warning("Found cycles in network graph of function "
                        "'{0}':\n{0}".format(function.id, cycles))
            self._warnings_count += 1

        return True

    def _load_service_functions(self, service):
        """
        Loads and stores functions (VNFs) referenced in the specified service
        :param service: service
        :return: True if successful, None otherwise
        """

        log.debug("Loading functions of the service.")

        # get VNFD file list from provided dpath
        vnfd_files = list_files(self._dpath, self._dext)
        log.debug("Found {0} descriptors in dpath='{2}': {1}"
                  .format(len(vnfd_files), vnfd_files, self._dpath))

        # load all VNFDs
        path_vnfs = read_descriptor_files(vnfd_files)

        # check for errors
        if 'network_functions' not in service.content:
            log.error("Service doesn't have any functions. "
                      "Missing 'network_functions' section.")
            return

        functions = service.content['network_functions']
        if functions and not path_vnfs:
            log.error("Service references VNFs but none could be found in "
                      "'{0}'. Please specify another '--dpath'"
                      .format(self._dpath))
            return

        # store function descriptors referenced in the service
        for function in functions:
            fid = build_descriptor_id(function['vnf_vendor'],
                                      function['vnf_name'],
                                      function['vnf_version'])
            if fid not in path_vnfs.keys():
                log.error("Referenced VNF descriptor '{0}' couldn't be "
                          "found in path '{1}'".format(fid, self._dpath))
                return

            vnf_id = function['vnf_id']
            new_func = self._storage.create_function(path_vnfs[fid])
            service.associate_function(new_func, vnf_id)

        return True

    @staticmethod
    def _load_project_service_file(project):
        """
        Load descriptors from a SONATA SDK project.
        :param project: SDK project
        :return: True if successful, False otherwise
        """

        # load project service descriptor (NSD)
        nsd_files = project.get_ns_descriptor()
        if not nsd_files:
            log.critical("Couldn't find a service descriptor in project '[0}'"
                         .format(project.project_root))
            return False

        if len(nsd_files) > 1:
            log.critical("Found multiple service descriptors in project "
                         "'{0}': {1}"
                         .format(project.project_root, nsd_files))
            return False

        return nsd_files[0]

    @staticmethod
    def _find_graph_cycles(graph, node, prev_node=None, backtrace=None):

        if not backtrace:
            backtrace = []

        # get node's neighbors
        neighbors = graph.neighbors(node)

        # remove previous node from neighbors
        if prev_node:
            neighbors.pop(neighbors.index(prev_node))

        # ensure node has neighbors
        if not len(neighbors) > 0:
            return None

        # check is this node was already visited
        if node in backtrace:
            cycle = backtrace[backtrace.index(node):]
            return cycle

        # mark this node as visited and trace it
        backtrace.append(node)

        # iterate through neighbor nodes
        for neighbor in neighbors:
            return Validator._find_graph_cycles(graph,
                                                neighbor,
                                                prev_node=node,
                                                backtrace=backtrace)
        return backtrace


def main():
    import argparse

    # specify arguments
    parser = argparse.ArgumentParser(
        description="Validate a SONATA Service. By default it performs a "
                    "validation to the syntax, integrity and network "
                    "topology.\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Example usage:
        son-validate --project /home/sonata/projects/project_X
                     --workspace /home/sonata/.son-workspace
        son-validate --service ./nsd_file.yml --path ./vnfds/ --dext yml
        son-validate --function ./vnfd_file.yml
        son-validate --function ./vnfds/ --dext yml
        """
    )

    exclusive_parser = parser.add_mutually_exclusive_group(
        required=True
    )

    parser.add_argument(
        "-w", "--workspace",
        dest="workspace_path",
        help="Specify the directory of the SDK workspace for validating the "
             "SDK project. If not specified will assume the directory: '{}'"
             .format(Workspace.DEFAULT_WORKSPACE_DIR),
        required=False
    )

    exclusive_parser.add_argument(
        "--project",
        dest="project_path",
        help="Validate the service of the specified SDK project. If "
             "not specified will assume the current directory: '{}'\n"
             .format(os.getcwd()),
        required=False
    )
    exclusive_parser.add_argument(
        "--package",
        dest="pd",
        help="Validate the specified package descriptor. "
    )
    exclusive_parser.add_argument(
        "--service",
        dest="nsd",
        help="Validate the specified service descriptor. "
             "The directory of descriptors referenced in the service "
             "descriptor should be specified using the argument '--path'.",
        required=False
    )
    exclusive_parser.add_argument(
        "--function",
        dest="vnfd",
        help="Validate the specified function descriptor. If a directory is "
             "specified, it will search for descriptor files with extension "
             "defined in '--dext'",
        required=False
    )
    parser.add_argument(
        "--dpath",
        help="Specify a directory to search for descriptors. Particularly "
             "useful when using the '--service' argument.",
        required=False
    )
    parser.add_argument(
        "--dext",
        help="Specify the extension of descriptor files. Particularly "
             "useful when using the '--function' argument",
        required=False
    )
    parser.add_argument(
        "--syntax", "-s",
        help="Perform a syntax validation.",
        required=False,
        action="store_true",
        default=False
    )
    parser.add_argument(
        "--integrity", "-i",
        help="Perform an integrity validation.",
        required=False,
        action="store_true",
        default=False
    )
    parser.add_argument(
        "--topology", "-t",
        help="Perform a network topology validation.",
        required=False,
        action="store_true",
        default=False
    )
    parser.add_argument(
        "--debug",
        help="sets verbosity level to debug",
        required=False,
        action="store_true")

    # parse arguments
    args = parser.parse_args()

    # by default, perform all validations
    if not args.syntax and not args.integrity and not args.topology:
        args.syntax = args.integrity = args.topology = True

    if args.project_path:

        if args.workspace_path:
            ws_root = args.workspace_path
        else:
            ws_root = Workspace.DEFAULT_WORKSPACE_DIR

        prj_root = args.project_path if args.project_path else os.getcwd()

        # Obtain Workspace object
        workspace = Workspace.__create_from_descriptor__(ws_root)
        if not workspace:
            log.error("Invalid workspace path: '%s'\n" % ws_root)
            exit(1)

        project = Project.__create_from_descriptor__(workspace, prj_root)
        if not project:
            log.error("Invalid project path: '%s'\n  " % prj_root)
            exit(1)

        validator = Validator(workspace=workspace)
        validator.configure(syntax=args.syntax,
                            integrity=args.integrity,
                            topology=args.topology,
                            log_level=args.debug)

        if not validator.validate_project(project):
            log.critical("Project validation has failed.")
            exit(1)
        if validator.warnings_count == 0:
            log.info("Validation of project '{0}' has succeeded."
                     .format(project.project_root))
        else:
            log.warning("Validation of project '{0}' returned {1} warning(s)"
                        .format(project.project_root,
                                validator.warnings_count))
    elif args.pd:
        pass

    elif args.nsd:
        validator = Validator()
        validator.configure(dpath=args.dpath, dext=args.dext,
                            syntax=args.syntax,
                            integrity=args.integrity,
                            topology=args.topology,
                            log_level=args.debug)

        if not validator.validate_service(args.nsd):
            log.critical("Project validation has failed.")
            exit(1)
        if validator.warnings_count == 0:
            log.info("Validation of service '{0}' has succeeded."
                     .format(args.nsd))
        else:
            log.warning("Validation of service '{0}' returned {1} warning(s)"
                        .format(args.nsd, validator.warnings_count))

    elif args.vnfd:
        validator = Validator()
        validator.configure(dext=args.dext,
                            syntax=args.syntax,
                            integrity=args.integrity,
                            topology=args.topology,
                            log_level=args.debug)

        if not validator.validate_function(args.vnfd):
            log.critical("Function validation has failed.")
            exit(1)
        if validator.warnings_count == 0:
            log.info("Validation of function '{0}' has succeeded."
                     .format(args.vnfd))
        else:
            log.warning("Validation of function '{0}' returned {1} warning(s)"
                        .format(args.vnfd, validator.warnings_count))
    else:
        log.error("Provided arguments are invalid.")
        exit(1)

    log.info("Done.")

    exit(0)
