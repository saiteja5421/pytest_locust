#AWS Session Manager Quickstart Guide

AWS library provides option to authenticate with AWS account by two ways: configuration by profile files and with using code parameters. 

###1. Configuration by profiles - credentials and config files

Create new folder `.aws` in home directory. Expected path to this file should look like below:
* MacOS and Linux: `~/.aws`
* Windows: `%USERPROFILE%\.aws`

**Set up profiles by creating new files within newly created directory.**
* **Credentials:**
    
1. Create `credentials` text file (without any extension).
2. Set up the default values for session, e.g.
```
[default]
aws_access_key_id = YOUR_AWS_ACCESS_KEY_ID
aws_secret_access_key = YOUR_AWS_SECRET_ACCESS_KEY
```

* **Region:**

1. Create  `config` text file (without any extension).
2. Set up the default values for session, e.g.
```
[default]
region = eu-west-2
```

For first time configuration you can also use [AWS CLI](https://aws.amazon.com/cli/).

###2. Configuration by code

`AWSSessionManager` class allows you to configure your session for AWS usage, by default 
it is using `default` credentials which set up process is indicated above.

You can create instance of `AWSSessionManager` providing AWS Access Key ID and AWS Secret Access Key.
```python
from library.aws.aws_session_manager import AWSSessionManager

session = AWSSessionManager(region_name="eu-west-2", aws_access_key_id="AWS_ACCESS_KEY_ID",
                 aws_secret_access_key="AWS_SECRET_ACCESS_KEY")
```

###3. Access to AWS session

To all manager classes it is required to pass session, e.g.

```python
from library.aws.aws_session_manager import AWSSessionManager
from library.aws.ec2_manager import EC2Manager

# For default settings based on .aws configuration
session_manager = AWSSessionManager(region_name="eu-west-2")
ec2_manager = EC2Manager(aws_session_manager=session_manager)


# For credential base approach
session = AWSSessionManager(region_name="eu-west-2", aws_access_key_id="AWS_ACCESS_KEY_ID",
                 aws_secret_access_key="AWS_SECRET_ACCESS_KEY")
ec2_manager = EC2Manager(aws_session_manager=session_manager)
```