# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
import logging
import sys
import traceback
import os
import json
from botocore.exceptions import ClientError

sts_client = boto3.client('sts')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORGANIZATIONS_ROLE = os.environ.get('ORGANIZATIONS_ROLE_ARN')

def log_exception(exception_type, exception_value, exception_traceback):
    """Function to create a JSON object containing exception details, which can then be logged as one line to the logger."""
    traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
    err_msg = json.dumps({"errorType": exception_type.__name__, "errorMessage": str(exception_value), "stackTrace": traceback_string})
    logger.error(err_msg)

def assume_role(role_arn: str):
    """Wrapper function to assume an IAM Role."""
    try:
        logger.info(f"Assuming Role: {role_arn}")
        # Assume a role within the AWS Organizations root account so we can access the service endpoint
        assumedRole = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='cross_account_role'
        )
    except:
        log_exception(*sys.exc_info())    
        raise RuntimeError(f"Could not assume role: {role_arn}")

    return boto3.Session(
        aws_access_key_id=assumedRole['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumedRole['Credentials']['SecretAccessKey'],
        aws_session_token=assumedRole['Credentials']['SessionToken'])

def get_account_details_from_organization(org_object):
    """Query the Organizations API to build a list of Account Ids and Names."""
    result_object = []
    try:
        paginator = org_object.get_paginator('list_accounts')
        iterator  = paginator.paginate()
        for page in iterator:
            for account in page['Accounts']:
                # Capture the Account Id and Name from Organizations if the account is active
                if "ACTIVE" == account['Status']:
                    logger.info(f"Account ID {account['Id']} has status: {account['Status']}")
                    result_object.append({"id": account['Id'], "name": account['Name']})
                else:
                    logger.info(f"Account ID {account['Id']} has status: {account['Status']}")
    except:
        log_exception(*sys.exc_info())
        raise RuntimeError(f"Error calling list_accounts for the organization")
    return result_object

def lambda_handler(event, context):
    boto3_session_object = assume_role(ORGANIZATIONS_ROLE)
    org_object = boto3_session_object.client('organizations')
    account_list = get_account_details_from_organization(org_object)
    logger.info(f"{account_list}")
    response_data = {}
    response_data['AccountDetails'] = account_list
    return(response_data)