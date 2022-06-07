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

tracer = Tracer(service="tgw_tagger_rtb_query")
logger = Logger(service="tgw_tagger_rtb_query")

@tracer.capture_method
def get_ec2_client(region: str):
    """
    Create a regional EC2 boto client
    
    Parameters: 
        region (str): the AWS region where the client should be created
    
    Returns:
        boto3 ec2 client for the target region
    """
    return boto3.client('ec2', region_name=region)

@tracer.capture_method
def list_tgw_route_tables(region: str):
    """
    Returns the TGW route tables for the supplied region

    Parameters:
        region (str): The AWS region to process

    Returns:
        result_object (list): List of TGW route tables (dict inc TGW and RTB IDs)
    """
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
    except:
        logger.exception(f"Error getting TGW RTB for region {region}")  
        raise RuntimeError(f"Error getting TGW RTB for region {region}")    
    for page in iterator:
        for rtb in page['TransitGatewayRouteTables']:
            result_object.append(
                {
                    "tgwId": rtb['TransitGatewayId'], 
                    "rtbId": rtb['TransitGatewayRouteTableId']
                }
            )
    return result_object

@tracer.capture_method
def find_tgw_attachment_cidr(attachment_id: str, route_table_list: list, region: str):
    """
    Returns the cidr range for a TGW attachment

    Parameters:
        attachment_id (str): The TGW attachment ID
        route_table_list (list): The list of route table information
        region (str): The AWS region to process
    
    Returns:
        Either the TGW cidr as a string or None
    """
    result_object = []
    for route_table in route_table_list:
        cidr_range = search_rtb_for_attachment(attachment_id, route_table['rtbId'], region)
        if cidr_range:
            result_object.append(
                {
                    "cidr": cidr_range
                }
            )
    if len(result_object) == 1:
        return result_object[0]['cidr']
    else:
        return None

@tracer.capture_method
def search_rtb_for_attachment(attachment_id: str, route_table_id: str, region: str):
    """
    Searches RTB for the TGW Attachment ID

    Parameters:
        attachment_id (str): The TGW attachment ID
        route_table_id (str): The Route Table ID
        region (str): The AWS region to process
    
    Returns:
        result_object: Either the CIDR block as a string or None    
    """
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
        logger.exception(f"Error searching TGW Route Table: {route_table_id}") 
        raise RuntimeError(f"Error searching TGW Route Table: {route_table_id}")
    if response['Routes']:
        # An attachment may only be associated with a single Route Table, however the API returns a list containing a single element
        for route in response['Routes']:
            result_object = route['DestinationCidrBlock']
    return result_object

@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """
    Queries the TGW route tables for the supplied region, to find out the CIDR range associated with the attachment

    Parameters:
        event (dict): The Lambda event object
        context (dict): The Lambda context object   
    
    Returns:
        event (dict): Updated event object, with the TGW Attachment CIDR if available
    """
    # Get the next item in the supplied dictionary. The Map iterator in the surrounding Step Function will supply a single region at a time to this function - however we do not know which at runtime
    map_region = next(iter(event))
    rtb = list_tgw_route_tables(map_region)
    for a in event[map_region]:
        logger.info(f"Processing attachment {a['attachmentId']}")
        cidr = find_tgw_attachment_cidr(a['attachmentId'], rtb, map_region)
        if cidr:
            a['cidr'] = cidr
        else:
            a['cidr'] = "MISSING"
    return event