# AWS toolkit usage

Aws tool kit is a **python** based standalone interactive CLI utility that allows to create and delete of EC2 instances/EBS volume in different regions as batch jobs in AWS console.

## Prerequisites:

1. AWS account with client credential access to create and delete assets.
2. At least one key-pair, VPC, subnet, and security group available in the AWS console prior running the toolkit.

## Setup

Utility is found under Medusa/utils directory.

Set following environmental variables for the utility to pickup the client credentials:

export AWS_KEY_ID=\<your aws account key id\>
export AWS_SECRET_KEY=\<your aws account secret key\>

Note: you need to supply the ID  and SECRET if not set in the environmental variables.

## Run
To run simply execute the utility with ./, options are interactive and self-explanatory.

./awstoolkit


[root@cxo-lin-096 dist]# .awstoolkit

AWS login

1 ap-south-1
2 eu-west-1
3 eu-west-2
4 us-east-1
5 us-east-2
6 us-west-1
7 us-west-2
q Quit

Select region: 1

ToolKit Menu

(1) --> Create EC2 instances
(2) --> Create EBS volumes
(3) --> Execute jobs
(4) --> Delete all assets
(5) --> Choose a different region
(q) --> to quit

Enter your choice:

Use option 1 to create EC2 instances in the region that was selected in the first menu. This will create a job, you can create n number of jobs and choose option 3 to execute the jobs. Make sure the session is not terminated or closed otherwise the script will be terminated.

Refer to the confluence link more information and video recordings.

https://confluence.eng.nimblestorage.com/display/~ruben.kumar@hpe.com/AWS+Toolkit+recordings