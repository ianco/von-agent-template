
import logging.config
from typing import Coroutine

from aiohttp import web, ClientRequest
import aiohttp_jinja2

from vonx.common import config, manager
from vonx.web.view_helpers import (
    IndyRequestError,
    get_handle_id,
    get_manager,
    get_request_json,
    indy_client,
    perform_issue_credential,
    perform_store_credential,
    service_request,
)
from vonx.web.routes import RouteDefinitions
from .view_helpers import (
    call_orgbook_api,
    orgbook_creds_for_org,
    orgbook_topic_to_creds,
    filter_by_dependent_proof_requests,
)

from .agent_callbacks import webhooks_base

LOGGER = logging.getLogger(__name__)


# agent webhook callbacks
class agent_webhooks(webhooks_base):
    def handle_credentials(self, state, message):
        # TODO
        return ""

    def handle_presentations(self, state, message):
        # TODO
        return ""


AGENT_WEBHOOKS = agent_webhooks()


def get_agent_routes(app) -> list:
    """
    Get the standard list of routes for the von-x agent
    """
    handler = AgentHandler(app['manager'])

    routes = []
    routes.extend([
        web.post('/agent_register_issuer', handler.agent_register_issuer),
        web.post('/agent_issue_credential', handler.agent_issue_credential),
        web.post('/callback/topic/{topic}/', handler.agent_handle_webhook),
    ])

    # add routes for all configured forms
    routes.extend(
        web.view(form['path'] + '/{org_name}', form_handler(form, handler), name=form['name'] + '-ivy')
                    for form in handler.forms)

    return routes


class AgentHandler:
    def __init__(self, cfg_mgr: manager.ConfigServiceManager):
        self.forms = RouteDefinitions.load(cfg_mgr).forms
        self.proofs = cfg_mgr.services_config("proof_requests")
        pass

    async def agent_form_handler(self, form: dict, request: web.Request) -> web.Response:
        org_name = request.match_info.get("org_name")

        result_creds = await orgbook_creds_for_org(org_name)

        cred_ids = []
        if "proof_request" in form:
            if not form["proof_request"]["id"] in self.proofs:
                raise RuntimeError(
                    'Proof request not found for service: {} {}'.format(service_name, form["proof_request"]["id"])
                )
            proof = self.proofs[form["proof_request"]["id"]]
            result_creds = filter_by_dependent_proof_requests(form, proof, result_creds, True)
            print(result_creds)
            for key in result_creds:
                creds = result_creds[key]
                for cred in creds:
                    cred_ids.append(cred['wallet_id'])
        else:
            print(result_creds)
            for cred in result_creds:
                cred_ids.append(cred['wallet_id'])

        print("Redirecting :-D", len(cred_ids), cred_ids)
        location = request.app.router[form['id']].url_for()
        if 0 < len(cred_ids):
            query = 'credential_ids='
            for i in range(len(cred_ids)):
                if i > 0:
                    query = query + ','
                query = query + cred_ids[i]
            location = location.with_query(query)
        print("Redirecting --> ", location)
        raise web.HTTPFound(location=location)

    async def filter_credential(self, request: web.Request) -> web.Response:
        return await self.search_credential(request, True)

    async def search_credential(self, request: web.Request, latest=False) -> web.Response:
        org_name = request.match_info.get("org_name")
        service_name = request.match_info.get("service_name")

        result_creds = await orgbook_creds_for_org(org_name)

        if service_name is not None and 0 < len(service_name):
            found = False
            for form in self.forms:
                if form["name"] == service_name:
                    found = True
                    if "proof_request" in form:
                        if not form["proof_request"]["id"] in self.proofs:
                            raise RuntimeError(
                                'Proof request not found for service: {} {}'.format(service_name, form["proof_request"]["id"])
                            )
                        proof = self.proofs[form["proof_request"]["id"]]
                        result_creds = filter_by_dependent_proof_requests(form, proof, result_creds, latest)
            if not found:
                raise RuntimeError(
                    'Service not found: {}'.format(service_name)
                )

        response = web.json_response(result_creds)
        return response


    async def agent_register_issuer(self, request: web.Request) -> web.Response:
        """
        Register our issuer with OrgBook (Indy Cat Credential Registry)
        """
        # TODO
        response = web.json_response("{}")
        return response


    async def agent_issue_credential(self, request: web.Request) -> web.Response:
        """
        Issue a credential to OrgBook (Indy Cat Credential Registry)
        """
        # TODO
        response = web.json_response("{}")
        return response


    async def agent_handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle a callback from the Indy Cat agent
        """
        # check the  topic and dispatch the request
        topic = request.match_info.get("topic")
        payload = await request.json()

        ret = AGENT_WEBHOOKS.POST(topic, payload)

        response = web.json_response(ret)
        return response


def form_handler(form: dict, handler: AgentHandler) -> Coroutine:
    """
    Return a request handler for processing form routes
    """
    async def _process(request: ClientRequest):
        if request.method == 'GET' or request.method == 'HEAD':
            return await handler.agent_form_handler(form, request)
        elif request.method == 'POST':
            return await handler.agent_form_handler(form, request)
        return web.Response(status=405)
    return _process
