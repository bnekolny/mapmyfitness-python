import json

import requests

from mapmyfitness.exceptions import BadRequestException, UnauthorizedException, NotFoundException, InternalServerErrorException, InvalidObjectException, InvalidSearchArgumentsException


class BaseAPI(object):
    http_exception_map = {
        400: BadRequestException,
        403: UnauthorizedException,
        404: NotFoundException,
        500: InternalServerErrorException,
    }

    def __init__(self, api_config):
        self.api_config = api_config

    def search(self, **kwargs):
        self.validator = self.validator_class(search_kwargs=kwargs)
        if not self.validator.valid:
            raise InvalidSearchArgumentsException(self.validator)
        if self.__class__.__name__ == 'Route':
            # Routes are special, and need to be requested with additional params
            kwargs.update({'field_set': 'detailed'})
        api_resp = self.call('get', self.path + '/', params=kwargs)

        objs = []
        for obj in api_resp['_embedded'][self.embedded_name]:
            serializer = self.serializer_class(obj)
            objs.append(serializer.serialized)
        return objs

    def create(self, obj):
        self.validator = self.validator_class(create_obj=obj)
        if not self.validator.valid:
            raise InvalidObjectException(self.validator)

        inflator = self.inflator_class(obj)
        data = inflator.inflated

        params = None
        if self.__class__.__name__ == 'Route':
            # Routes are special, and need to be created with additional params
            params = {'field_set': 'detailed'}

        api_resp = self.call('post', '{0}/'.format(self.path), data=data, extra_headers={'Content-Type': 'application/json'}, params=params)

        serializer = self.serializer_class(api_resp)
        return serializer.serialized

    def delete(self, id):
        self.call('delete', '{0}/{1}'.format(self.path, id))

    def find(self, id):
        params = None
        if self.__class__.__name__ == 'Route':
            # Routes are special, and need to be requested with additional params
            params = {'field_set': 'detailed'}
        api_resp = self.call('get', '{0}/{1}'.format(self.path, id), params=params)
        serializer = self.serializer_class(api_resp)
        return serializer.serialized

    def call(self, method, path, data=None, extra_headers=None, params=None):
        full_path = self.api_config.api_root + path
        headers = {
            'Api-Key': self.api_config.api_key,
            'Authorization': 'Bearer {0}'.format(self.api_config.access_token)
        }
        if extra_headers is not None:
            headers.update(extra_headers)

        kwargs = {'headers': headers}

        if data is not None:
            kwargs['data'] = json.dumps(data)

        if params is not None:
            kwargs['params'] = params

        resp = getattr(requests, method)(full_path, **kwargs)

        if resp.status_code in self.http_exception_map:
            bad_request_json = resp.json()
            if resp.status_code == 400 and '_diagnostics' in bad_request_json and 'validation_failures' in bad_request_json['_diagnostics'] and len(bad_request_json['_diagnostics']['validation_failures']):
                printable_errors = []
                validation_failures = bad_request_json['_diagnostics']['validation_failures']
                for validation_dict in validation_failures:
                    for validation_dict_key, validation_dict_list in validation_dict.items():
                        for validation_error in validation_dict_list:
                            printable_errors.append('{0} {1}'.format(validation_dict_key, validation_error))
                raise self.http_exception_map[resp.status_code](' '.join(printable_errors))
            else:
                raise self.http_exception_map[resp.status_code]

        if method != 'delete':
            return resp.json()

    def update(self, id, obj):
        self.validator = self.validator_class(obj)
        if not self.validator.valid:
            raise InvalidObjectException(self.validator)

        inflator = self.inflator_class(obj)
        data = inflator.inflated

        api_resp = self.call('put', '{0}/{1}/'.format(self.path, id), data=data, extra_headers={'Content-Type': 'application/json'})
        serializer = self.serializer_class(api_resp)
        return serializer.serialized
