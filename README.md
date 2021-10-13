## Transit Gateway Attachment Tagger

### Summary

AWS Transit Gateway (TGW) can be shared via AWS Resource Access Manager across AWS account boundaries. When creating TGW attachments across AWS account boundaries, attachments are created without a Name tag - which can make identifying attachments time consuming. 

This solution provides an automated mechanism to gather information about each TGW attachment for accounts within an AWS Organization, including looking up the Classless Inter-Domain Routing (CIDR) range from the TGW Route Table. The solution will then apply a Name tag in the form of "CIDR-AccountName" to the attachment within the AWS account which owns the TGW.

This solution can be used alongside a solution such as the Serverless Transit Network Orchestrator from the AWS Solutions Library, which enables the automated creation of TGW attachments at scale.

### Detailed Documentation 

See APG document - link TBC

### Usage Instructions

1. Obtain pre-requisite information

* Account ID for the AWS Organizations management account
* Account ID for the shared networking account which contains the Transit Gateways
* The AWS regions which you wish to process with this solution
* The Ids of any Transit Gateways which you wish to exclude from processing

2. Deploy the main stack (tgw-attachment-tagger-main-stack.yaml) using CloudFormation in the AWS account which contains the Transit Gateways. Populate the stack parameters with the information gathered in the first step. Note that this stack must be deployed before the Organizations stack.

3. Deploy the organizations stack (tgw-attachment-tagger-organizations-stack.yaml) using CloudFormation in the AWS Organizations management account.

The solution will run each day at 06:00 UTC. Alternatively you may manually trigger the solution by executing the "tgw-attachment-tagger-state-machine" from the Step Functions console. The Step Function needs no specific input, so any valid JSON may be used.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

