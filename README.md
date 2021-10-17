## Transit Gateway Attachment Tagger

### Summary

AWS Transit Gateway (TGW) can be shared via AWS Resource Access Manager across AWS account boundaries. When creating TGW attachments across AWS account boundaries, attachments are created without a Name tag - which can make identifying attachments time consuming. 

This solution provides an automated mechanism to gather information about each TGW attachment for accounts within an AWS Organization, including looking up the Classless Inter-Domain Routing (CIDR) range from the TGW Route Table. The solution will then apply a Name tag in the form of **CIDR-AccountName** to the attachment within the AWS account which owns the TGW.

This solution can be used alongside a solution such as the *[Serverless Transit Network Orchestrator](https://aws.amazon.com/solutions/implementations/serverless-transit-network-orchestrator/)* from the AWS Solutions Library, which enables the automated creation of TGW attachments at scale.

### Solution Architecture

The solution architecture is shown below:

![Solution Architecture](https://github.com/aws-samples/tgw-attachment-tagger/blob/main/docs/solution-architecture.png)

The solution is delivered via two AWS CloudFormation templates. The main stack is deployed in a shared networking account which contains the AWS Transit Gateways. This stack deploys a Step Function, four Lambdas plus their associated IAM Roles & finally a CloudWatch event to trigger the Step Function on a schedule. 

The second stack is deployed into the AWS Organizations management account. This stack deploys an IAM role with permissions to four *List* APIs in the organizations service - this role trusts a role from the first stack to perform sts:AssumeRole.

### Step Function Logic

The workflow for the Step Function is detailed below:

![Step Function Workflow](https://github.com/aws-samples/tgw-attachment-tagger/blob/main/docs/step-function-workflow.png)



### Usage Instructions

1. Obtain pre-requisite information

* Account ID for the AWS Organizations management account
* Account ID for the shared networking account which contains the Transit Gateways
* The AWS regions which you wish to process with this solution
* The Ids of any Transit Gateways which you wish to exclude from processing

2. Deploy the main stack (tgw-attachment-tagger-main-stack.yaml) using CloudFormation in the AWS account which contains the Transit Gateways. Populate the stack parameters with the information gathered in the first step. *Note that this stack must be deployed before the Organizations stack, the role is translated to a specific Principal ID as is explained [here](https://docs.amazonaws.cn/en_us/IAM/latest/UserGuide/id_roles_create_for-user.html)*.

3. Deploy the organizations stack (tgw-attachment-tagger-organizations-stack.yaml) using CloudFormation in the AWS Organizations management account.

The solution will run each day at 06:00 UTC. Alternatively you may manually trigger the solution by executing the "tgw-attachment-tagger-state-machine" from the Step Functions console. The Step Function needs no specific input, so any valid JSON may be used.

The solution generates Name tags as shown in the example below:

![screengrab](https://github.com/aws-samples/tgw-attachment-tagger/blob/main/docs/sample-screengrab.png)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

