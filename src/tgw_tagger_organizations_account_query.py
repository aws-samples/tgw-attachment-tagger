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

import boto3 # type: ignore
import logging
import sys
import traceback
import os
import json
from aws_lambda_powertools import Tracer # type: ignore
from aws_lambda_powertools import Logger # type: ignore

sts_client = boto3.client('sts')
tracer = Tracer(service="tgw-tagger-organizations-account-query")
logger = Logger(service="tgw-tagger-organizations-account-query")

ORGANIZATIONS_ROLE = os.environ.get('ORGANIZATIONS_ROLE_ARN')

@tracer.capture_method
def assume_role(role_arn: str, boto_client):
    """
    Function to assume an IAM Role
    
    Parameters: 
        role_arn (str): the ARN of the role to assume
        boto_client:  The boto client object to use, exposed to enable mocking in unit tests
    
    Returns:
        boto3 session object
    """
    try:
        logger.info(f"Assuming Role: {role_arn}")
        assumed_role = boto_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='sh-notifier-send-email'
        )
    except:
        logger.exception("Exception assuming role")
        raise RuntimeError(f"Exception assuming role: {role_arn}")
    return boto3.Session(
        aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
        aws_session_token=assumed_role['Credentials']['SessionToken'])

@tracer.capture_method
def get_account_details_from_organization(organizations_client):
    """
    Query the Organizations API to build a list of Account Ids and Names.
    
    Parameters:
        organizations_client: the boto client object to use for the Organizations API calls
    
    Returns:
        result_object (list): List of accounts/Names in the Organization with status of ACTIVE    
    """
    result_object = []
    try:
        paginator = organizations_client.get_paginator('list_accounts')
        iterator  = paginator.paginate()
        for page in iterator:
            for account in page['Accounts']:
                if "ACTIVE" == account['Status']:
                    logger.debug(f"Account ID {account['Id']} has status: {account['Status']}")
                    result_object.append(
                        {
                            "id": account['Id'], 
                            "name": account['Name']
                        }
                    )
                else:
                    logger.debug(f"Account ID {account['Id']} has status: {account['Status']}")
    except:
        logger.exception("Error calling list_accounts for the organization")
        raise RuntimeError(f"Error calling list_accounts for the organization")
    return result_object

@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """
    Queries the AWS Organizations API to determine menmber account IDs and Names, before returning a list of dictionaries with account information.

    Parameters:
        event (dict): The Lambda event object
        context (dict): The Lambda context object   
    
    Returns:
        response_data (dict): Dictionary containing a list of the accounts/names to process to the Step Function
    """
    boto3_session_object = assume_role(ORGANIZATIONS_ROLE, sts_client)

    organizations_client = boto3_session_object.client('organizations')

    account_list = get_account_details_from_organization(organizations_client)

    logger.info(f"{account_list}")

    response_data = {}
    response_data['AccountDetails'] = account_list
    return(response_data)