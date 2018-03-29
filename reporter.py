import csv
import io
import json
import xml.etree.ElementTree as ET
import zlib
from typing import Dict

import requests


class Reporter:
    mode = 'Robot.XML'
    version = '2.2'
    endpoint = 'https://reportingitc-reporter.apple.com/reportservice/{type}/v1'
    _access_token = ''
    _vendors = None
    _vendors_regions = None

    def __init__(self,
                 account: str = '',
                 access_token: str = '',
                 password: str = '',
                 user_id: str = ''):
        if access_token:
            self._access_token = access_token
        else:
            self.user_id = user_id
            self.password = password

        # If there are multiple accounts, we need an account number as well for
        # some reports
        self.account = account

    @property
    def access_token(self):
        if not self._access_token:
            self._access_token = self.obtain_access_token()
        return self._access_token

    @property
    def vendors(self):
        if not self._vendors:
            self._vendors = self.obtain_vendor_list()
        return self._vendors

    @property
    def vendors_and_regions(self):
        if not self._vendors_regions:
            self._vendors_regions = self.obtain_vendor_regions()
        return self._vendors_regions

    @staticmethod
    def _process_regions(child):
        return [
            {
                'code': region[0].text,
                'reports': [report.text for report in region[1]]
            }
            for region in child if region.tag == 'Region'
        ]

    def obtain_vendor_regions(self):
        credentials = {
            'accesstoken': self.access_token
        }

        response = self.make_request('finance', 'getVendorsAndRegions',
                                     credentials)
        xml_data = ET.fromstring(response.text.strip('\n'))

        return_dict = {}
        for child in xml_data:
            return_dict[child[0].text] = {
                'id': child[0].text,
                'regions': self._process_regions(child)
            }

        return return_dict

    def obtain_vendor_list(self):
        credentials = {
            'accesstoken': self.access_token
        }

        response = self.make_request('sales', 'getVendors', credentials)
        xml_data = ET.fromstring(response.text.strip('\n'))
        return [child.text for child in xml_data]

    @staticmethod
    def format_data(data):
        return {
            'jsonRequest': json.dumps(data)
        }

    def obtain_access_token(self) -> str:
        credentials = {
            'userid': self.user_id,
            'password': self.password,
        }

        response = self.make_request('sales', 'generateToken', credentials)

        # annoyingly enough, this takes two requests to accomplish
        service_request_id = response.headers['service_request_id']

        params = {
            'isExistingToken': 'Y',
            'requestId': service_request_id,
        }
        response = self.make_request('sales', 'generateToken', credentials,
                                     extra_params=params)
        xml_data = ET.fromstring(response.text.strip('\n'))
        return xml_data.find('AccessToken').text

    def make_request(self,
                     cmd_type: str,
                     command: str,
                     credentials: Dict[str, str],
                     extra_params: Dict[str, str] = None):
        if not extra_params:
            extra_params = {}

        command = '[p=Reporter.properties, {cmd_type}.{command}]'.format(
            cmd_type=cmd_type.capitalize(), command=command
        )
        endpoint = self.endpoint.format(type=cmd_type)

        data = {
            'account': '13391800',
            'version': self.version,
            'mode': self.mode,
            **credentials,
            'userid': 'appli@rainbird.co.jp',
            'queryInput': command,
        }

        data = self.format_data(data)
        data.update(extra_params)

        response = requests.post(endpoint, data=data)
        response.raise_for_status()
        return response

    def _process_gzip(self, response):
        content = zlib.decompress(response.content, 15 + 32)
        file_obj = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(file_obj, dialect=csv.excel_tab)
        return [row for row in reader]

    def download_sales_report(self,
                              vendor: str,
                              report_type: str,
                              date_type: str,
                              date: str,
                              report_subtype: str = '',
                              report_version: str = ''):
        credentials = {
            'accesstoken': self.access_token
        }
        command = (f'getReport, {vendor},{report_type},{report_subtype},'
                   f'{date_type},{date},{report_version}')

        return self._process_gzip(self.make_request('sales', command, credentials))

    def download_financial_report(self,
                                  vendor: str,
                                  region_code: str,
                                  report_type: str,
                                  fiscal_year: str,
                                  fiscal_period: str):
        credentials = {
            'accesstoken': self.access_token
        }
        command = (f'getReport {vendor}, {region_code}, {report_type}, '
                   f'{fiscal_year}, {fiscal_period}')

        return self._process_gzip(self.make_request('finance', command, credentials))
