
class IndyClient:
    _service = None
    _issuers = []
    _holders = []
    _verifiers = []
    _pr_specs = {}
    
    def __init__(self, service):
        print("client init")
        self._service = service

    async def sync(self, flag):
        print("client sync", flag)
        print("call remote agent to send issuer data to TOB")
        for issuer in self._issuers:
            await self._service.register_issuer(issuer)

    async def register_proof_spec(self, pr_spec):
        print("client register_proof_spec", pr_spec)
        # keep a list of defined proof specs
        self._pr_specs[pr_spec['id']] = pr_spec

    async def register_issuer(self, params):
        print("client register_issuer", params)
        issuer_id = len(self._issuers)
        issuer = {
            'credential_types': [],
            'issuer': params['details'],
        }
        self._issuers.append(issuer)
        return issuer_id

    async def register_holder(self, holder_cfg):
        print("client register_holder", holder_cfg)
        holder_id = len(self._holders)
        self._holders.append(holder_cfg)
        return holder_id

    async def register_verifier(self, verifier_cfg):
        print("client register_verifier", verifier_cfg)
        verifier_id = len(self._verifiers)
        self._holders.append(verifier_cfg)
        return verifier_id

    async def register_credential_type(self,
                issuer_id,
                schema_name,
                schema_version,
                origin_did,
                attributes,
                params,
                dependencies
                ):
        print("client register_credential_type", 
                issuer_id,
                schema_name,
                schema_version,
                origin_did,
                attributes,
                params,
                dependencies)
        credential = {
            'cardinality_fields': {},
            'category_labels': {},
            'claim_descriptions': params['claim_descriptions'],
            'claim_labels': attributes,
            'credential': params['credential'],
            'credential_def_id': 'tbd',
            'description': params['details']['label'],
            'endpoint': params['details']['url'],
            'logo_b64': 'tbd',
            'mapping': params['mapping'],
            'name': 'tbd',
            'origin_did': origin_did,
            'schema': schema_name,
            'topic': params['topic'],
            'version': schema_version,
            'visible_fields': [],
        }
        self._issuers[issuer_id]['credential_types'].append(credential)

    async def register_orgbook_connection(self,
                    issuer_id, connection_cfg):
        print("client register_orgbook_connection", issuer_id, connection_cfg)
        pass

    async def register_http_connection(self,
                    issuer_id, connection_cfg):
        print("client register_http_connection", issuer_id, connection_cfg)
        pass

