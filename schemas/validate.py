"""Dependency-free validator for the explicitly supported JSON Schema subset."""
import json
from functools import lru_cache
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def validate(value, schema, path='$'):
    if '$ref' in schema:
        schema = json.loads((ROOT / schema['$ref']).read_text())
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'number': (int, float), 'boolean': bool}
    kind = schema.get('type')
    if kind and (not isinstance(value, types[kind]) or kind in ('integer', 'number') and isinstance(value, bool)):
        raise ValueError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: unsupported value')
    if isinstance(value, dict):
        if set(schema.get('required', [])) - value.keys():
            raise ValueError(f'{path}: missing fields')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError(f'{path}: unknown fields')
        for key, item in value.items():
            if key in props:
                validate(item, props[key], f'{path}.{key}')
    if isinstance(value, list):
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', float('inf')) or schema.get('uniqueItems') and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise ValueError(f'{path}: too many items')
        for item in value:
            validate(item, schema.get('items', {}), path+'[]')
    if isinstance(value, str) and not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', float('inf')):
        raise ValueError(f'{path}: invalid length')
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        import math
        if not math.isfinite(value) or not schema.get('minimum', -float('inf')) <= value <= schema.get('maximum', float('inf')):
            raise ValueError(f'{path}: out of range')
    return value

@lru_cache(maxsize=32)
def load_contract(name):
    return json.loads((ROOT / f'{name}.json').read_text())

def contract(name, value):
    return validate(value, load_contract(name))
