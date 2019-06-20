#
# Copyright 2017-2018 Government of Canada
# Public Services and Procurement Canada - buyandsell.gc.ca
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Implementation of the standard manager class for the :class:`IndyService`
"""

import logging
from typing import Mapping

from vonx.common.config import load_config
from vonx.common.manager import ConfigServiceManager
from vonx.indy.config import IndyConfigError, SchemaManager
from vonx.indy.tob import CRED_TYPE_PARAMETERS, extract_translated

from .client import IndyClient
from .service import IndyService

LOGGER = logging.getLogger(__name__)


def load_credential_type(ctype, schema_mgr: SchemaManager) -> dict:
    """
    Load the credential types defined by our config into a standard format
    """
    if "topic" not in ctype:
        raise IndyConfigError("Credential type must define 'topic'")
    if "schema" not in ctype:
        raise IndyConfigError("Credential type must define 'schema'")
    if isinstance(ctype["schema"], str):
        name = ctype["schema"]
        version = None
        origin_did = None
        attributes = None
        dependencies = ctype.get("depends_on") or []
    elif isinstance(ctype["schema"], dict):
        name = ctype["schema"].get("name")
        version = ctype["schema"].get("version")
        origin_did = ctype["schema"].get("origin_did")
        attributes = ctype["schema"].get("attributes")
        dependencies = ctype.get("depends_on") or []
    else:
        raise IndyConfigError("Credential type schema must be string or dict")

    if not name:
        raise IndyConfigError("Credential type schema missing 'name'")
    if isinstance(dependencies, str):
        dependencies = [dependencies]

    schema = schema_mgr.find(name, version)
    if schema:
        version = schema.version
        if not attributes:
            attributes = schema.attr_names
        if not origin_did:
            origin_did = schema.origin_did
    elif not version or not (attributes or origin_did):
        raise IndyConfigError(
            "Schema definition not found: {} {}".format(name, version)
        )

    details = ctype.get("details", {})
    for k in ("endpoint", "logo_b64", "logo_path"):
        if k in ctype:
            details[k] = ctype[k]

    # TODO: remove, temporary compatibility with older config format
    if "description" in ctype:
        details["label"] = ctype["description"]
    if "issuer_url" in ctype:
        details["url"] = ctype["issuer_url"]

    params = {
        "category_labels": {},
        "claim_descriptions": {},
        "claim_labels": {},
    }
    for k in CRED_TYPE_PARAMETERS:
        if k in ctype:
            params[k] = ctype[k]
    params["details"] = details

    if schema:
        deflang = "en"
        for attr_spec in schema.attributes:
            attr_name = attr_spec["name"]
            a_lbls = extract_translated(attr_spec, "label", None, deflang)
            if a_lbls[deflang] and attr_name not in params["claim_labels"]:
                params["claim_labels"][attr_name] = a_lbls
            a_desc = extract_translated(attr_spec, "description", None, deflang)
            if a_desc[deflang] and attr_name not in params["claim_descriptions"]:
                params["claim_descriptions"][attr_name] = a_desc

    return {
        "schema_name": name,
        "schema_version": version,
        "origin_did": origin_did,
        "attributes": attributes,
        "dependencies": dependencies,
        "params": params,
    }


class IndyManager(ConfigServiceManager):
    """
    A manager for initializing the Indy service from standard configuration files
    """

    def __init__(self, env: Mapping = None, pid: str = 'manager'):
        super(IndyManager, self).__init__(env, pid)
        self._schema_mgr = None

    def _init_services(self):
        """
        Initialize the Indy service
        """
        super(IndyManager, self)._init_services()

        indy = self.init_indy_service()
        self.add_service("indy", indy)

    def get_client(self) -> IndyClient:
        """
        Obtain an IndyClient attached to the registered Indy service
        """
        #return IndyClient(self.get_service_request_target("indy"))
        return IndyClient(self.get_service("indy"))

    def get_service_init_params(self) -> dict:
        """
        Get a dictionary of parameters for initializing the :class:`IndyService` instance
        """
        agent_admin_url = self._env.get("AGENT_ADMIN_URL")
        if not agent_admin_url:
            raise IndyConfigError(
                "Indy agent admin url (AGENT_ADMIN_URL) not defined"
            )
        tob_connection_name = self._env.get("TOB_CONNECTION_NAME")
        if not tob_connection_name:
            raise IndyConfigError("TOB connection name (TOB_CONNECTION_NAME) not defined")
        return {
            "AUTO_REGISTER": self._env.get("AUTO_REGISTER_DID", 1),
            "AGENT_ADMIN_URL": agent_admin_url,
            "TOB_CONNECTION_NAME": tob_connection_name,
            "TOB_INVITATION_FILE": self._env.get("TOB_INVITATION_FILE", None),
        }

    def init_indy_service(self, pid: str = "indy") -> IndyService:
        """
        Initialize the Hyperledger Indy service

        Args:
            pid: the identifier for the :class:`IndyService` instance
        """
        spec = self.get_service_init_params()
        LOGGER.info("Initializing Indy service")
        return IndyService(pid, spec)

    async def _service_start(self) -> bool:
        """
        After running processing load our schemas and initialize all services
        """
        ret = await super(IndyManager, self)._service_start()
        if ret:
            self._schema_mgr = self._load_schemas()
            self.run_task(self._load_config())
        return ret

    def _load_schemas(self) -> SchemaManager:
        """
        Load all configured schemas
        """
        mgr = SchemaManager()
        std = load_config('vonx.config:schemas.yml')
        if std:
            mgr.load(std)
        ext = self.load_config_path('SCHEMAS_CONFIG_PATH', 'schemas.yml')
        if ext:
            mgr.load(ext)
        return mgr

    async def _load_config(self) -> None:
        """
        Initialize our client and populate services based on configuration
        """
        client = self.get_client()
        await self._register_proof_requests(client)
        await self._register_agents(client)
        await client.sync(False)

    async def _register_agents(self, client: IndyClient) -> None:
        """
        Load agent settings from our configuration files
        """
        limit_agents = self._env.get("AGENTS")
        limit_agents = (
            set(limit_agents.split())
            if (limit_agents and limit_agents != "all")
            else None
        )

        await self._register_issuers(client, limit_agents)
        await self._register_holders(client, limit_agents)
        await self._register_verifiers(client, limit_agents)

    async def _register_issuers(self, client: IndyClient, limit_agents: set):
        """
        Register all issuer services from the configuration
        """
        issuers = []
        issuer_ids = []
        config_issuers = self.services_config("issuers")
        if not config_issuers:
            LOGGER.debug("No issuers defined by configuration")
        for issuer_key, issuer_cfg in config_issuers.items():
            if not issuer_cfg.get("id"):
                issuer_cfg["id"] = issuer_key
            if limit_agents is None or issuer_cfg["id"] in limit_agents:
                issuers.append(issuer_cfg)
                issuer_ids.append(issuer_cfg["id"])
        if issuers:
            for issuer_cfg in issuers:
                await self._register_issuer(client, issuer_cfg)
        elif config_issuers:
            LOGGER.warning("No defined issuers referenced by AGENTS")

    async def _register_issuer(self, client: IndyClient, issuer_cfg: dict) -> str:
        """
        Register a single issuer service from the configuration
        """
        issuer_id = issuer_cfg["id"]
        if "credential_types" not in issuer_cfg:
            raise IndyConfigError("Missing credential_types for issuer: {}".format(issuer_id))
        cred_types = issuer_cfg["credential_types"]
        if "connection" not in issuer_cfg:
            raise IndyConfigError("Missing connection for issuer: {}".format(issuer_id))
        connection_cfg = issuer_cfg["connection"]

        details = issuer_cfg.get("details", {})
        params = {"id": issuer_id}

        # TODO: remove, temporary compatibility with older config format
        if "name" in issuer_cfg:
            details["label"] = issuer_cfg["name"]
        for k in ("endpoint", "abbreviation", "email", "logo_b64", "logo_path", "url"):
            if k in issuer_cfg:
                details[k] = issuer_cfg[k]

        for k in ("link_secret_name",):
            if k in issuer_cfg:
                params[k] = issuer_cfg[k]
        params["details"] = details

        issuer_id = await client.register_issuer(params)

        for type_spec in cred_types:
            cred_type = load_credential_type(type_spec, self._schema_mgr)
            await client.register_credential_type(
                issuer_id,
                cred_type["schema_name"],
                cred_type["schema_version"],
                cred_type["origin_did"],
                cred_type["attributes"],
                cred_type["params"],
                cred_type["dependencies"],
            )

        if connection_cfg:
            if not connection_cfg.get("id"):
                connection_cfg["id"] = issuer_id
            conn_type = connection_cfg.get("type", "OrgBook")
            if conn_type == "OrgBook" or conn_type == "TheOrgBook":
                _conn_id = await client.register_orgbook_connection(
                    issuer_id, connection_cfg)
            else:
                _conn_id = await client.register_http_connection(
                    issuer_id, connection_cfg)
        return issuer_id

    async def _register_holders(self, client: IndyClient, limit_agents: set):
        """
        Register all holder services from the configuration
        """
        holders = []
        holder_ids = []
        config_holders = self.services_config("holders")
        if not config_holders:
            LOGGER.debug("No holders defined by configuration")
        for holder_key, holder_cfg in config_holders.items():
            if not holder_cfg.get("id"):
                holder_cfg["id"] = holder_key
            if limit_agents is None or holder_cfg["id"] in limit_agents:
                holders.append(holder_cfg)
                holder_ids.append(holder_cfg["id"])
        if holders:
            for holder_cfg in holders:
                await self._register_holder(client, holder_cfg)
        elif config_holders:
            LOGGER.info("No defined holders referenced by AGENTS")

    async def _register_holder(self, client: IndyClient, holder_cfg: dict) -> str:
        """
        Register a single holder service from the configuration
        """
        holder_id = holder_cfg["id"]
        holder_id = await client.register_holder(holder_cfg)
        return holder_id

    async def _register_verifiers(self, client: IndyClient, limit_agents: set):
        """
        Register all verifier services from the configuration
        """
        verifiers = []
        verifier_ids = []
        config_verifiers = self.services_config("verifiers")
        if not config_verifiers:
            LOGGER.debug("No verifiers defined by configuration")
        for verifier_key, verifier_cfg in config_verifiers.items():
            if not verifier_cfg.get("id"):
                verifier_cfg["id"] = verifier_key
            if limit_agents is None or verifier_cfg["id"] in limit_agents:
                verifiers.append(verifier_cfg)
                verifier_ids.append(verifier_cfg["id"])
        if verifiers:
            for verifier_cfg in verifiers:
                await self._register_verifier(client, verifier_cfg)
        elif config_verifiers:
            LOGGER.info("No defined verifiers referenced by AGENTS")

    async def _register_verifier(self, client: IndyClient, verifier_cfg: dict) -> str:
        """
        Register a single verifier service from the configuration
        """
        verifier_id = verifier_cfg["id"]
        if "connection" not in verifier_cfg:
            raise IndyConfigError("Missing connection for verifier: {}".format(verifier_id))
        connection_cfg = verifier_cfg["connection"]
        del verifier_cfg["connection"]

        verifier_id = await client.register_verifier(verifier_cfg)

        if connection_cfg:
            if not connection_cfg.get("id"):
                connection_cfg["id"] = verifier_id
            conn_type = connection_cfg.get("type", "OrgBook")
            if conn_type == "OrgBook" or conn_type == "TheOrgBook":
                _conn_id = await client.register_orgbook_connection(
                    verifier_id, connection_cfg)
            else:
                _conn_id = await client.register_http_connection(
                    verifier_id, connection_cfg)
        return verifier_id

    async def _register_proof_requests(self, client: IndyClient):
        """
        Register all proof request specifications from the configuration
        """
        config_prs = self.services_config("proof_requests")
        if config_prs:
            for pr_id, pr_spec in config_prs.items():
                if not pr_spec.get("id"):
                    pr_spec["id"] = pr_id
                _spec_id = await client.register_proof_spec(pr_spec)
