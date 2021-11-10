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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION_LIST = os.environ.get('REGION_LIST').split(",")
ORIGINAL_TGW_LIST = os.environ.get('TGW_LIST')

if not REGION_LIST:
    raise RuntimeError("Environment Variable REGION_LIST is empty - At least one region must be specified")

if ORIGINAL_TGW_LIST:
    tgw_list = ORIGINAL_TGW_LIST.split(",")
else:
    tgw_list = []

def log_exception(exception_type, exception_value, exception_traceback):
    """Function to create a JSON object containing exception details, which can then be logged as one line to the logger."""
    traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
    err_msg = json.dumps({"errorType": exception_type.__name__, "errorMessage": str(exception_value), "stackTrace": traceback_string})
    logger.error(err_msg)

def get_ec2_client(region: str):
    """Create a regional EC2 boto client."""
    return boto3.client('ec2', region_name=region)
    
def list_transit_gateway_attachments(accountList: list, region: str):
    """Returns all TGW attachments for the specified Region."""
    logger.info(f"Getting list of TGW Attachments for region {region}")
    ec2 = get_ec2_client(region)
    result_object = []
    try:
        # Get all TGW attachments in the region which have type: vpc and are available
        paginator = ec2.get_paginator('describe_transit_gateway_attachments')
        iterator  = paginator.paginate(
            Filters=[
                {
                    'Name': 'state',
                    'Values': [
                        'available',
                    ]
                },
                {
                    'Name': 'resource-type',
                    'Values': [
                        'vpc',
                    ]
                },
            ] 
        )
    except:
        log_exception(*sys.exc_info())
        raise RuntimeError(f"Error getting list of TGW attachments for region {region}")
    for page in iterator:
        for attachment in page['TransitGatewayAttachments']:
            # Check TGW has not been excluded from processing
            if attachment['TransitGatewayId'] not in tgw_list:
                logger.info(f"Processing Attachment: {attachment['TransitGatewayAttachmentId']}")
                tgw_name = "MISSING"
                for i in attachment['Tags']:
                    # Check whether Name tag exists
                    if "Name" == i['Key']:
                        tgw_name = i['Value']   
                account_name = "MISSING"
                # Check account list object for a match against the TGW resource owner
                for account in [x for x in accountList if x['id'] == attachment['ResourceOwnerId']]:
                    account_name = account['name']           
                result_object.append({"tgwId": attachment['TransitGatewayId'], "attachmentId": attachment['TransitGatewayAttachmentId'], "accountId": attachment['ResourceOwnerId'],"accountName": account_name, "nametag": tgw_name})
    return result_object

def lambda_handler(event, context):
    """
    Lambda handler function. 
    
    Queries the EC2 API for Transit Gateway Attachment details for each configured region, before returning a dictionary of lists with TGW attachment information.
    """
    response_data = {}
    response_data['MapInput'] = []
    if event['AccountDetails']:
        for region in REGION_LIST:
            logger.info(f"Processing Region: {region}")
            result = list_transit_gateway_attachments(event['AccountDetails'], region)
            response_data['MapInput'].append({region: result}) 
    return(response_data)
