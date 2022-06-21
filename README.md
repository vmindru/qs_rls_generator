# RLS generator for QuickSight

## About QS RLS generator 
Generate RLS csv file for QuickSight based on AWS Organizational Units.

[About QuickSight RLS](https://docs.aws.amazon.com/quicksight/latest/user/restrict-access-to-a-data-set-using-row-level-security.html)

[About AWS Organizational Unit ](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html)


## Getting Started 

Code can be executed locally or as Lambda. [AWS Credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) are managed standard way.
To run the lambda define following `ENV_VARS` with following DEFAULTS if ENV_VAR is not set. 

[Using AWS Lambda environment variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)


`BUCKET_NAME` env var is mandatory. 
`ROOT_OU` env var is mandatory. 

```
OWNER_TAG = 'cudos_users'
BUCKET_NAME = 'NO DEFAULT'
TMP_RLS_FILE = '/tmp/cudos_rls.csv'
ROOT_OU = os_environ['ROOT_OU'] if 'ROOT_OU' in os_environ else exit("Missing ROOT_OU env var, please define ROOT_OU in ENV vars")
```
## Defining TAGS

1) Tags at root OU level, Give full access to all data and overwrite any other rules for user at other levels.
2) Tags at OU level will be Inherited TAG to all children accounts.
2) Tags at Account level will be generated rules for Account level.


## Output 

Output is writen to `TMP_RLS_FILE` location and uploaded to `BUCKET_NAME`.


## Example Output 

Note first 3 entry are giving full access to vmindru@megacorp, vmindru_has_it_all, and Admin/vmindru-Isengard.

```
UserName,account_id
vmindru@megacorp.corp,
vmindru_has_it_all, 
Admin/vmindru-Isengard, 
cross_ou_user,"0140000000,7200000,74700000,853000000"
foo_inherit,74700000000
student1,"853000000,126000000"
student2,"853678200000,126600000"
other@company_foo.com,"363700000,1675000000"
other@company.com,"36370000000,16750000000"
vmindru@amazon.com,363000000000
```



## Create Lambda

### Create a new Lambda in same region with your QS Dashboards 

1) Create new Lambda
2) Select Python 3.6

### Configure Lambda

1)  Create and assign new Execution Role LambdaS3Org Role 
2)  Create and Add 2 Permission Policies to above LambdaS3Org Role

`LambdaOrgS3ListTags`

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "organizations:ListAccounts",
                "organizations:ListTagsForResource"
            ],
            "Resource": "*"
        }
    ]
}
```

`AWSLambdaS3ExecutionRole`

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::vmindru-cudos-fr/cudos_rls.csv"
        }
    ]
}
```

### Add ENV Variables 

Go to function settings and add ENV VARS 

`BUCKET_NAME` - Bucket where to upload RLS file 
`ROOT_OU`  -  ID of your root OU






