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

tracer = Tracer(service="tgw_tagger_attachment_tagger")
logger = Logger(service="tgw_tagger_attachment_tagger")

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
def tag_tgw_attachment(attachment: dict, region: str):
    """
    Apply Tags to TGW Attachments
    
    Parameters:
        attachment (dict): Dictionary with TGW attachment metadata
        region (str): The AWS region where the attachment is found
    """
    ec2_client = get_ec2_client(region)
    tagValue = f"{attachment['cidr']}-{attachment['accountName']}"

    try:
        # Add Name tag to TGW attachment
        ec2_client.create_tags(
            Resources=[
                attachment['attachmentId'],
            ],
            Tags=[
                {
                    'Key': 'Name',
                    'Value': tagValue
                },
            ]
        )
    except:
        logger.exception(f"Error updating TGW attachment tag for {attachment['attachmentId']}")
        raise RuntimeError(f"Error updating TGW attachment tag for {attachment['attachmentId']}")

@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """
    Applies missing Name tags to TGW attachments where we have the necessary information and there is no existing Name tag

    Parameters:
        event (dict): The Lambda event object
        context (dict): The Lambda context object   
    
    Returns:
        event (dict): Updated event object, with the TGW Attachment CIDR if available
    """
    # Get the next item in the supplied dictionary. 
    # The Map iterator in the surrounding Step Function will supply a single region at a time to this function, 
    # however we do not know which at runtime
    map_region = next(iter(event))

    logger.info(f"Processing region {map_region}")
    for attachment in event[map_region]:
        # Logic to determine whether we should tag the attachment
        if ("MISSING" == attachment['nametag']) and ("MISSING" != attachment['cidr']):
            # Attachment has no Name tag and we were able find the CIDR from the propagated Route Table entry
            logger.info(f"Tagging attachment {attachment['attachmentId']}")
            tag_tgw_attachment(attachment, map_region)
            attachment['tagCreated'] = True
        else:
            logger.info(f"Skipping attachment {attachment['attachmentId']}")
            attachment['tagCreated'] = False        
    return event