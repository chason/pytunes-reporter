import pytest
import responses
from faker import Factory
from requests.exceptions import HTTPError

# library to test
import reporter

sales_url = 'https://reportingitc-reporter.apple.com/reportservice/sales/v1'
financial_url = 'https://reportingitc-reporter.apple.com/reportservice/finance/v1'


@pytest.fixture(scope='session')
def faker():
    return Factory.create('ja_JP')


def test_reporter_have_token_create(faker):
    access_token = faker.uuid4()
    account = faker.pyint()
    new_reporter = reporter.Reporter(
        access_token=access_token,
        account=account,
    )

    assert type(new_reporter) is reporter.Reporter
    assert new_reporter.access_token == access_token
    assert new_reporter.account == account


@responses.activate
def test_reporter_have_password_create(faker):
    request_id = faker.uuid4()
    user_id = faker.email()
    password = faker.password()
    access_token = faker.uuid4()

    responses.add(
        responses.POST,
        sales_url,
        body=(
            b'If you generate a new access token, your existing token will be '
            b'deleted. You will need to save your new access token within your'
            b' properties file. Do you still want to continue? (y/n): '),
        status=200,
        headers={
            'SERVICE_REQUEST_ID': request_id,
        }
    )
    response_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<ViewToken>\n    <AccessToken>{access_token}</AccessToken>\n    <ExpirationDate>2018-09-24</ExpirationDate>\n    <Message>Your new access token has been generated.</Message>\n</ViewToken>\n'
    responses.add(
        responses.POST,
        sales_url,
        status=200,
        body=response_xml,
    )

    new_reporter = reporter.Reporter(
        user_id=user_id,
        password=password
    )

    assert type(new_reporter) is reporter.Reporter
    assert new_reporter.access_token


def test_vendor_numbers(faker):
    access_token = faker.uuid4()
    vendor_numbers = [str(faker.random_int(800000, 899999))
                      for _ in range(faker.random_int())]
    response_xml = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Vendors>
{vendors}
</Vendors>
    '''.format(vendors=''.join(['<Vendor>{num}</Vendor>'.format(num=num)
                                for num in vendor_numbers]))
    responses.add(
        responses.POST,
        sales_url,
        body=response_xml,
        status=200
    )

    new_reporter = reporter.Reporter(
        access_token=access_token
    )

    assert new_reporter.vendors == vendor_numbers


def test_finanical_vendors_and_regions(faker):
    access_token = faker.uuid4()
    response_xml = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VendorsAndRegions>
    <Vendor>
        <Number>80012345</Number>
        <Region>
            <Code>US</Code>
            <Reports>
                <Report>Financial</Report>
            </Reports>
        </Region>
        <Region>
            <Code>JP</Code>
            <Reports>
                <Report>Financial</Report>
            </Reports>
        </Region>
    </Vendor>
    <Vendor>
        <Number>80067891</Number>
        <Region>
            <Code>US</Code>
            <Reports>
                <Report>Financial</Report>
            </Reports>
        </Region>
    </Vendor>
</VendorsAndRegions>
'''
    responses.add(
        responses.POST,
        financial_url,
        body=response_xml,
        status=200
    )
    expected_result = {
        '80012345': {
            'id': '80012345',
            'regions': [
                {
                    'code': 'US',
                    'reports': [
                        'Financial',
                    ],
                },
                {
                    'code': 'JP',
                    'reports': [
                        'Financial',
                    ],
                },
            ],
        },
        '80067891': {
            'id': '80067891',
            'regions': [
                {
                    'code': 'US',
                    'reports': [
                        'Financial',
                    ],
                },
            ],
        },
    }

    new_reporter = reporter.Reporter(access_token=access_token)
    assert new_reporter.vendors_and_regions == expected_result


@responses.activate
def test_error_handling():
    error_xml = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Error>
    <Code>101</Code>
    <Message>Invalid command.</Message>
</Error>"""
    responses.add(
        responses.POST,
        sales_url,
        body=error_xml,
        status=400
    )
    new_reporter = reporter.Reporter(user_id='asdf@asdf.com', password='12345')
    with pytest.raises(HTTPError):
        new_reporter.access_token
