import json
from aiohttp import ClientSession
import asyncio


async def agent_get_request(
    request_url: str
):
    """Get agent transactions."""
    print("Calling agent request", request_url)
    headers = {}
    headers["Content-Type"] = "application/json"
    async with ClientSession() as client_session:
        response = await client_session.get(request_url, headers=headers)
        response_json = await response.text()
        return response_json

async def agent_post_request(
    request_url: str,
    payload: str
):
    """Get agent transactions."""
    print("Calling agent request", request_url)
    headers = {}
    headers["Content-Type"] = "application/json"
    async with ClientSession() as client_session:
        response = await client_session.post(request_url, data=payload, headers=headers)
        response_json = await response.text()
        return response_json


def run_coroutine_with_args(coroutine, *args):
    #loop = asyncio.get_event_loop()
    #future = asyncio.ensure_future(coroutine(*args), loop=loop)
    ret = (yield from coroutine(*args).__await__())
    print("ret =", ret)
    return ret


class IndyService:
    _pid = ""
    _spec = {}
    _connection = None
    
    def __init__(self, pid, spec):
        print("service init", pid, spec)
        self._pid = pid
        self._spec = spec

    def start(self, flag):
        print("service _start")
        print("service _start - check for existing connections", self._spec['TOB_CONNECTION_NAME'])
        #if not self._connection:
        #    connections = run_coroutine_with_args(agent_get_request, self._spec['AGENT_ADMIN_URL'] + '/connections')
        #    print("connections", connections)
        #    for connection in connections:
        #        if connection['their_label'] == self._spec['TOB_CONNECTION_NAME']:
        #            self._connection = connection
        #if not self._connection:
        #    print("service _start - establish TOB connection if not found")
        #    if self._spec['TOB_INVITATION_FILE']:
        #        f = open(self._spec['TOB_INVITATION_FILE'], "r")
        #        invitation = f.read()
        #        f.close()
        #        connection = run_coroutine_with_args(agent_post_request, self._spec['AGENT_ADMIN_URL'] + '/connections/receive-invitation', invitation)
        #        self._connection = connection
        pass

    async def register_issuer(self, issuer):
        issuer_registration = {
            'issuer_registration': issuer,
            'connection_id': 'my_id', # self._connection['id'],
        }
        print("service register_issuer, credentials, etc, with TOB", json.dumps(issuer_registration))
        pass
