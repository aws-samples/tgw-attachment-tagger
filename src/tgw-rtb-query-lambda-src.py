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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_exception(exception_type, exception_value, exception_traceback):
    """Function to create a JSON object containing exception details, which can then be logged as one line to the logger."""
    traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
    err_msg = json.dumps({"errorType": exception_type.__name__, "errorMessage": str(exception_value), "stackTrace": traceback_string})
    logger.error(err_msg)

def get_ec2_client(region: str):
    """Create a regional EC2 boto client."""
    ec2 = boto3.client('ec2', region_name=region)
    return ec2

def list_tgw_route_tables(region: str):
    """Get TGW RTB for the specified Region."""
    ec2 = get_ec2_client(region)    
    result_object = []
    try:
        paginator = ec2.get_paginator('describe_transit_gateway_route_tables')    
        iterator  = paginator.paginate(
            Filters=[
                {
                    'Name': 'state',
                    'Values': [
                        'available',
                    ]
                },
            ] 
        )
        for page in iterator:
            for rtb in page['TransitGatewayRouteTables']:
                result_object.append({"tgwId": rtb['TransitGatewayId'], "rtbId": rtb['TransitGatewayRouteTableId']})
    except:
        log_exception(*sys.exc_info())   
        raise RuntimeError(f"Error getting TGW RTB for region {region}")    
    return result_object

def find_tgw_attachment_cidr(attachment_id: str, route_table_list: list, region: str):
    """Get CIDR for TGW Attachment."""
    result_object = []
    for route_table in route_table_list:
        cidr_range = search_rtb_for_attachment(attachment_id, route_table['rtbId'], region)
        if cidr_range:
            result_object.append({"cidr": cidr_range})
    if len(result_object) == 1:
        return result_object[0]['cidr']
    else:
        return None

def search_rtb_for_attachment(attachment_id: str, route_table_id: str, region: str):
    """Search RTB for TGW Attachment."""
    ec2 = get_ec2_client(region)
    result_object = None
    try:
        response = ec2.search_transit_gateway_routes(
            TransitGatewayRouteTableId=route_table_id,
            Filters=[
                {
                    'Name': 'attachment.transit-gateway-attachment-id',
                    'Values': [
                        attachment_id,
                    ]
                },
            ]
        )
    except:
        log_exception(*sys.exc_info())
        raise RuntimeError(f"Error searching TGW Route Table: {route_table_id}")
    if response['Routes']:
        result_object = response['Routes'][0]['DestinationCidrBlock']
    return result_object

def lambda_handler(event, context):
    logger.info(f"{event}")
    map_region = next(iter(event))
    rtb = list_tgw_route_tables(map_region)
    for a in event[map_region]:
        logger.info(f"Processing attachment {a['attachmentId']}")
        cidr = find_tgw_attachment_cidr(a['attachmentId'], rtb, map_region)
        if None is not cidr:
            a['cidr'] = cidr
        else:
            a['cidr'] = "MISSING"
    return event