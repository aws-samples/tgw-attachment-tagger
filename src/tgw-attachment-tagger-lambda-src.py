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

def tag_tgw_attachment(attachment: dict, region: str):
    """Apply Tags to TGW Attachments."""
    ec2 = get_ec2_client(region)
    tagValue = f"{attachment['cidr']}-{attachment['accountName']}"

    try:
        # Add Name tag to TGW attachment
        response = ec2.create_tags(
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
        log_exception(*sys.exc_info())
        raise RuntimeError(f"Error updating TGW attachment tag for {attachment['attachmentId']}")

def lambda_handler(event, context):
    logger.info(f"{event}")
    map_region = next(iter(event))
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