***Introduction***:

This guide provides step-by-step instructions to set up a daily report that lists all running EC2 instances ID in your AWS account stores it in a CSV file and generate health report on all instances and stores that report in an S3 bucket. The report will be emailed out every day automatically.

***Pre-requisites***:

AWS account with appropriate permissions to create IAM users, roles, Lambda functions, S3 buckets, SES configurations, CloudWatch events, and SNS topics.
Basic knowledge of AWS services.
Terraform installed on your local machine (optional but recommended).
Steps:

***Create IAM User***:

Create an IAM user with the necessary permissions to perform the required tasks. Assign the following policies to the user:
AmazonSESFullAccess
CloudWatchFullAccess
AmazonS3FullAccess
AmazonSNSFullAccess


***Create Lambda Function for Health Check***:

Write a Python script (genstore.py) to generate the EC2 instances status report and store it in an S3 bucket.
Create a Lambda function named HealthCheck.
Attach the genstore.py script to the Lambda function.
Test the Lambda function with a sample JSON file (test.json) containing mock data.

***Configure SES for Email Sending***:

Write a Python script (sesattach.py) to send emails using SES.
Configure SES with the appropriate settings and verify the email addresses that will be used to send the reports.
Set up CloudWatch Scheduled Event:

***Add a trigger to the Lambda function using an Amazon CloudWatch scheduled event***.
Schedule the event to trigger the Lambda function daily at the desired time.
Set up SNS Topic for Notifications:

***Create an SNS topic to receive notifications for success and failure of the job***.
Configure the Lambda function to send notifications to this SNS topic.

***Provision EC2 Instances with Terraform***: optional

Use Terraform to write infrastructure as code (IAC) to provision EC2 instances for automation and control.
Define the required resources such as instance type, security groups, key pair, etc., in the Terraform configuration files.

***Testing and Validation***:

Test the entire setup by triggering the Lambda function manually or waiting for the scheduled event to trigger.
Verify that the EC2 instances status report is generated, stored in the S3 bucket, and emailed out successfully.
Ensure that notifications are sent to the SNS topic for both successful and failed executions.
