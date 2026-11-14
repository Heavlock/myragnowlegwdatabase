#!/usr/bin/env python3
"""Repository-local MCP client for save, update, search, and read contracts."""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

FIELDS = {'title', 'content', 'source_uri', 'source_type', 'language', 'metadata'}


class ContractError(Exception):
    pass


class Client:
    def __init__(self, url, timeout):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
            raise ContractError('The MCP endpoint must be an http(s) URL.')
        self.url = url
        self.timeout = timeout
        self.sequence = 0
        # Endpoint identity is useful in results without echoing URL credentials/query strings.
        host = parsed.hostname if ':' not in parsed.hostname else '[' + parsed.hostname + ']'
        self.identity = f'{parsed.scheme}://{host}' + (f':{parsed.port}' if parsed.port else '') + parsed.path

    def rpc(self, method, params):
        self.sequence += 1
        request = urllib.request.Request(self.url, data=json.dumps({'jsonrpc': '2.0', 'id': self.sequence, 'method': method, 'params': params}, ensure_ascii=False).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                message = json.load(response)
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise ContractError(f'MCP transport/response failure: {error}. If a write was sent, its outcome may be unknown; inspect stored data before retrying.') from error
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or message.get('id') != self.sequence:
            raise ContractError('Invalid MCP response; do not infer whether a write succeeded.')
        if 'error' in message:
            error = message['error']
            raise ContractError(f'MCP error {error.get("code")}: {error.get("message")}')
        if 'result' not in message:
            raise ContractError('MCP response has no result.')
        return message['result']

    def tool(self, name, arguments):
        result = self.rpc('tools/call', {'name': name, 'arguments': arguments})
        if result.get('isError'):
            raise ContractError(f'MCP tool failed: {result.get("content")}')
        data = result.get('structuredContent')
        if not isinstance(data, dict):
            raise ContractError('Expected this repository server to return structuredContent.')
        return data


def read_input(filename):
    try:
        if filename == '-':
            value = json.load(sys.stdin)
        else:
            with Path(filename).open() as stream:
                value = json.load(stream)
    except (OSError, ValueError) as error:
        raise ContractError(f'Cannot read input JSON: {error}') from error
    if not isinstance(value, dict):
        raise ContractError('Input must be a JSON object.')
    return value


def validate_fields(value, complete=False):
    unknown = set(value) - FIELDS
    if unknown:
        raise ContractError('Unknown fields: ' + ', '.join(sorted(unknown)))
    for field, item in value.items():
        if field == 'metadata':
            if not isinstance(item, dict):
                raise ContractError('metadata must be a JSON object.')
        elif not isinstance(item, str):
            raise ContractError(f'{field} must be a string.')
    for field in ['title', 'content']:
        if (complete or field in value) and not value.get(field, '').strip():
            raise ContractError(f'{field} must be nonempty.')


def merge_metadata(original, patch):
    result = copy.deepcopy(original)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_metadata(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def expected_document(payload):
    return {'title': payload['title'].strip(), 'content': payload['content'].strip(), 'source_uri': payload.get('source_uri', '').strip(), 'source_type': payload.get('source_type', '').strip() or 'manual', 'language': payload.get('language', '').strip() or 'en', 'metadata': payload.get('metadata', {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['postgres', 'qdrant'], default=os.environ.get('PROFILE', 'postgres'))
    parser.add_argument('--url', default=os.environ.get('MYRAG_MCP_URL'), help='Explicit MCP endpoint; defaults to the selected profile port.')
    parser.add_argument('--timeout', type=float, default=120)
    sub = parser.add_subparsers(dest='operation', required=True)
    save = sub.add_parser('save', help='Create a new document and verify its stored body.')
    save.add_argument('--input', default='-', help='JSON document file or - for stdin.')
    update = sub.add_parser('update', help='Read, merge, replace, and verify an existing document.')
    update.add_argument('--document-id', type=int, required=True)
    update.add_argument('--input', default='-', help='JSON patch file or - for stdin.')
    update.add_argument('--replace-metadata', action='store_true', help='Replace the entire metadata object instead of recursively merging it.')
    search = sub.add_parser('search', help='Search semantic chunks without writing anything.')
    search.add_argument('--query', required=True)
    search.add_argument('--limit', type=int, default=5)
    get = sub.add_parser('get', help='Read a complete source document.')
    get.add_argument('--document-id', type=int, required=True)
    args = parser.parse_args()
    if args.profile not in {'postgres', 'qdrant'}:
        raise ContractError('PROFILE must be postgres or qdrant.')
    if args.timeout <= 0:
        raise ContractError('timeout must be positive.')
    if args.operation in {'get', 'update'} and not 0 < args.document_id <= 2**53 - 1:
        raise ContractError('document-id must be a positive JSON-safe integer.')
    payload = None
    if args.operation in {'save', 'update'}:
        payload = read_input(args.input)
        if args.operation == 'save' and 'document_id' in payload:
            if type(payload['document_id']) is not int or payload['document_id'] != 0:
                raise ContractError('save only creates documents; use update for an existing ID.')
            payload.pop('document_id')
        validate_fields(payload, complete=args.operation == 'save')
        if args.operation == 'update' and not payload:
            raise ContractError('Update patch is empty.')
        if args.operation == 'update' and args.replace_metadata and 'metadata' not in payload:
            raise ContractError('--replace-metadata requires a metadata object in the patch.')
    if args.operation == 'search' and (not args.query.strip() or args.limit < 1):
        raise ContractError('Search requires a nonempty query and a positive result limit.')
    port = os.environ.get('POSTGRES_MCP_PORT', '8081') if args.profile == 'postgres' else os.environ.get('QDRANT_MCP_PORT', '8083')
    client = Client(args.url or f'http://127.0.0.1:{port}/mcp', args.timeout)
    client.rpc('initialize', {})
    result = {'operation': args.operation, 'profile': 'custom' if args.url else args.profile, 'endpoint': client.identity}
    if args.operation == 'search':
        result['result'] = client.tool('search_chunks', {'query': args.query, 'limit': args.limit})
    elif args.operation == 'get':
        result['document'] = client.tool('get_document', {'document_id': args.document_id})
    else:
        if args.operation == 'update':
            old = client.tool('get_document', {'document_id': args.document_id})
            patch = payload
            payload = {field: copy.deepcopy(old[field]) for field in FIELDS}
            for field, value in patch.items():
                payload[field] = merge_metadata(payload['metadata'], value) if field == 'metadata' and not args.replace_metadata else value
            validate_fields(payload, complete=True)
            payload['document_id'] = args.document_id
        else:
            payload.setdefault('language', 'en')
        # Always send an explicit language so updates retain the stored value.
        payload['language'] = payload.get('language', '').strip() or ('en' if args.operation == 'save' else old['language'])
        written = client.tool('insert_document', payload)
        identifier = written.get('document_id')
        expected_status = 'created' if args.operation == 'save' else 'reindexed'
        if type(identifier) is not int or identifier <= 0 or written.get('status') != expected_status:
            raise ContractError('Unexpected write result; inspect stored data before retrying.')
        if args.operation == 'update' and identifier != args.document_id:
            raise ContractError('Update changed the document ID unexpectedly.')
        actual = client.tool('get_document', {'document_id': identifier})
        if any(actual.get(field) != value for field, value in expected_document(payload).items()):
            raise ContractError(f'Write returned document {identifier}, but read-back differs from the requested fields. Inspect it before retrying.')
        result.update(result=written, document=actual, verified=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except ContractError as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
