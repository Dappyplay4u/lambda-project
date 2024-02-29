import boto3
import csv
import urllib
import logging
from datetime import datetime, timedelta
import json
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define the connections
s3_client = boto3.client('s3')
ec2 = boto3.resource('ec2')
cw = boto3.client('cloudwatch')
ses = boto3.client('ses')

def send_s3_object_daily(bucket, key, sender_email, recipient_email, email_subject):
    # Get object content
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        object_content = response['Body'].read().decode('utf-8')
    except ClientError as e:
        logger.error("Error getting object content from S3: {}".format(e))
        return
    
    # Compose email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = email_subject
    msg.attach(MIMEText(object_content, 'plain'))

    # Send email
    try:
        ses.send_raw_email(
            Source=sender_email,
            Destinations=[recipient_email],
            RawMessage={'Data': msg.as_string()}
        )
        logger.info("Daily report email sent successfully.")
    except ClientError as e:
        logger.error("Error sending daily report email: {}".format(e))

def lambda_handler(event, context):
    try:
        # Retrieve running EC2 instances and their status
        instance_data = []
        for instance in ec2.instances.all():
            instance_data.append({
                'InstanceId': instance.id,
                'InstanceName': instance.tags[0]['Value'] if instance.tags else '',
                'Status': instance.state['Name']
            })

        # Format current date and time
        current_datetime = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')

        # Write instance data to CSV
        csv_filename = f'/tmp/running_instances_{current_datetime}.csv'
        with open(csv_filename, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=['InstanceId', 'InstanceName', 'Status'])
            writer.writeheader()
            writer.writerows(instance_data)

        # Upload CSV file to S3
        s3_csv_key = f'status/running_instances_{current_datetime}.csv'
        s3_client.upload_file(csv_filename, 'hollandtunnel', s3_csv_key)

        # Retrieve EC2 metrics from CloudWatch
        all_metrics_data = {}
        for instance in ec2.instances.all():
            instance_id = instance.id
            instance_name = instance.tags[0]['Value'] if instance.tags else ''
            logger.info("Retrieving metrics for EC2 instance: {}".format(instance_id))
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)  # 5 minutes ago
            response = cw.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': 'cpu_utilization',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/EC2',
                                'MetricName': 'CPUUtilization',
                                'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]
                            },
                            'Period': 300,  # 5 minutes
                            'Stat': 'Average',
                        },
                        'ReturnData': True
                    }
                ],
                StartTime=start_time,
                EndTime=end_time
            )
            metric_data = response['MetricDataResults'][0]['Values']
            all_metrics_data[instance_id] = {
                'InstanceName': instance_name,
                'Metrics': metric_data
            }

        # Store all metrics in a JSON file
        json_filename = f'/tmp/all_ec2_metrics_{current_datetime}.json'
        with open(json_filename, 'w') as json_file:
            json.dump(all_metrics_data, json_file)

        # Upload JSON file to S3
        s3_json_key = f'metrics/all_ec2_metrics_{current_datetime}.json'
        s3_client.upload_file(json_filename, 'hollandtunnel', s3_json_key)

        logger.info("All EC2 metrics stored in JSON file: s3://hollandtunnel/{}".format(s3_json_key))

        # Send daily email with object content
        sender_email = 'jegede.oladapo@ymail.com'
        recipient_email = 'jegede.oladapo02@gmail.com'
        email_subject = 'Daily Report:'
        send_s3_object_daily('hollandtunnel', s3_csv_key, sender_email, recipient_email, email_subject)
        send_s3_object_daily('hollandtunnel', s3_json_key, sender_email, recipient_email, email_subject)

    except Exception as e:
        logger.error("An error occurred: {}".format(e))
        raise e
