import csv
import io
import json
import xml.etree.ElementTree as ET
import gzip
from typing import Dict, List, Union, Optional, cast
from datetime import datetime

import requests

# Custom types
Region = Dict[str, Union[str, List[str]]]
RegionList = List[Region]
Row = Dict[str, str]
Data = List[Row]


class Reporter:
    """ Class to facilitate using the iTunes Reporter API

    When instantiating the class, you may provide either your user_id and
    password or the AccessKey for your account. If you provide the user_id and
    password, a new AccessKey will be retrieved (invalidating any previous ones)
    and stored when you try and access any data from the iTunes Reporter API.

    Other public methods/properties:
        access_token - AccessToken for this account
        account - if there are multiple accounts attached to the iTunes Reporter
                  account, the account number will need to be provided
        vendors - List of vendor IDs
        vendors_and_regions - dictionary of available reports with the vendor
            IDs as keys
        download_sales_report - method to download sales reports
        download_financial_report - method to download financial reports
        make_request - method to make raw requests against the API
    """
    mode = 'Robot.XML'
    version = '2.2'
    _access_token = ''
    _vendors = None
    _vendors_regions = None

    def __init__(self,
                 account: str = '',
                 access_token: str = '',
                 password: str = '',
                 user_id: str = '') -> None:
        """ Instantiate Reporter object

        Args:
            account - account ID (only necessary in case of multiple accounts
                attached to iTunes Connect account
            access_token - AccessToken for accessing API. Optional in case
                `user_id` and `password` are provided, in which case it will
                be fetched from the API
            user_id - user ID to access account. Only necessary if access_key is
                not provided
            password - password for account. Only necessary if access_key is not
                provided
        """
        if access_token:
            self._access_token = access_token
        else:
            self.user_id = user_id
            self.password = password

        # If there are multiple accounts, we need an account number as well for
        # some reports
        self.account = account

    @property
    def access_token(self) -> str:
        """ AccessToken for account """
        if not self._access_token:
            self._access_token = self._obtain_access_token()
        return self._access_token

    @property
    def vendors(self) -> Optional[List[str]]:
        """ List of vendors attached to account """
        if not self._vendors:
            self._vendors = self._obtain_vendor_list()
        return self._vendors

    @property
    def vendors_and_regions(self) -> Optional[Dict[str, Dict[str, Union[RegionList, str]]]]:
        """ Dictionary of available reports. Dictionary key is vendor IDs"""
        if not self._vendors_regions:
            self._vendors_regions = self._obtain_vendor_regions()
        return self._vendors_regions

    @staticmethod
    def _process_regions(child: ET.Element) -> RegionList:
        return [
            {
                'code': region[0].text,
                'reports': [report.text for report in region[1]]
            }
            for region in child if region.tag == 'Region'
        ]

    def _obtain_vendor_regions(self) -> Dict[str, Dict[str, Union[RegionList, str]]]:
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

    def _obtain_vendor_list(self) -> List[str]:
        credentials = {
            'accesstoken': self.access_token
        }

        response = self.make_request('sales', 'getVendors', credentials)
        xml_data = ET.fromstring(response.text.strip('\n'))
        return [child.text for child in xml_data]

    def download_sales_report(self,
                              vendor: str,
                              report_type: str,
                              date_type: str,
                              date: str,
                              report_subtype: str = '',
                              report_version: str = '') -> Data:
        """Downloads sales report, puts the TSV file into a Python list

        Information on the parameters can be found in the iTunes Reporter
        documentation:
        https://help.apple.com/itc/appsreporterguide/#/itcbd9ed14ac

        Args:
            vendor: Vendor ID supplied by Apple
            report_type: report type as specified by Apple
            date_type: date type as specified by Apple
            date: date to obtain sales report for
            report_subtype: subtype to fetch, optional
            report_version: report version, optional

        Returns:
            List of Dicts with sales information
        """
        credentials = {
            'accesstoken': self.access_token
        }
        command = (f'getReport, {vendor},{report_type},{report_subtype},'
                   f'{date_type},{date},{report_version}')

        return self._process_gzip(self.make_request('sales', command,
                                                    credentials))

    def download_financial_report(self,
                                  vendor: str,
                                  region_code: str,
                                  report_type: str,
                                  fiscal_year: str,
                                  fiscal_period: str) -> Data:
        """Downloads sales report, puts the TSV file into a Python list

        Information on the parameters can be found in the iTunes Reporter
        documentation:
        https://help.apple.com/itc/appsreporterguide/#/itc21263284f

        Args:
            vendor: Vendor ID supplied by Apple
            region_code: string representing region code for report
            report_type: report type as specified by Apple
            fiscal_year: year to obtain the report from
            fiscal_period: period to obtain report from, format as specified by Apple

        Returns:
            A list of Dicts containing the requested information.
        """
        credentials = {
            'accesstoken': self.access_token
        }
        command = (f'getReport, {vendor},{region_code},{report_type},'
                   f'{fiscal_year},{fiscal_period}')

        return self._process_gzip(self.make_request('finance', command,
                                                    credentials))

    @staticmethod
    def _format_data(data: Dict[str, str]) -> Dict[str, str]:
        return {
            'jsonRequest': json.dumps(data)
        }

    def _obtain_access_token(self) -> str:
        credentials = {
            'userid': self.user_id,
            'password': self.password,
        }

        response = self.make_request('sales', 'viewToken', credentials)
        xml_data = ET.fromstring(response.text.strip('\n'))
        expiration_date_elem = xml_data.find('ExpirationDate')
        if expiration_date_elem is not None:
            # User already has token. we will check if it's expired or not
            expiration_date_str = expiration_date_elem.text
            expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d").date()
            if expiration_date > datetime.now().date():
                # token expiration date is greater than today's date
                return xml_data.find('AccessToken').text

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
                     extra_params: Dict[str, str] = None
                     ) -> requests.Response:
        """ Function to make a request against the API

        Makes request to the API and returns the result contained in a `requests.Response`
        object.

        Args:
            cmd_type: A string with the "type" of command (e.g. "sales" or "finance")
            command: Actual command to run, should also include any parameters
            credentials: Dict with user credentials to auth with
            extra_params: Dictionary of any extra params to pass in the data block

        Returns:
            A `requests.Response` object with the API's response contained within

        Raises:
            `requests.exceptions.HTTPError`: If API returns an error.
        """
        if not extra_params:
            extra_params = {}

        if self.account:
            command = f'[p=Reporter.properties, a={self.account} {cmd_type.capitalize()}.{command}]'
        else:
            command = f'[p=Reporter.properties, {cmd_type.capitalize()}.{command}]'

        endpoint = ('https://reportingitc-reporter.apple.com'
                    f'/reportservice/{cmd_type}/v1')

        data = {
            'version': self.version,
            'mode': self.mode,
            **credentials,
            'queryInput': command,
        }

        data = self._format_data(data)
        data.update(extra_params)

        response = requests.post(endpoint, data=data)
        response.raise_for_status()
        return response

    @staticmethod
    def _process_gzip(response: requests.Response) -> Data:
        content = gzip.decompress(response.content)
        file_obj = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(file_obj, dialect=cast(csv.Dialect,
                                                       csv.excel_tab))
        return [row for row in reader]
