import boto3
import csv
import urllib
import logging
from datetime import datetime, timedelta
import json
import uuid
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define the connections
s3_client = boto3.client('s3')
ec2 = boto3.resource('ec2')
cw = boto3.client('cloudwatch')

def lambda_handler(event, context):
    try:
        # Retrieve running EC2 instances
        filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
        instances = ec2.instances.filter(Filters=filters)
        instance_ids = [instance.id for instance in instances]

        # Format current date and time
        current_datetime = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')

        # Download file from S3
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        local_filename = f'/tmp/instanceid_{current_datetime}.csv'

        try:
            s3_client.download_file(bucket, key, local_filename)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.error("Object not found: {}/{}".format(bucket, key))
                # Handle the missing object error
            else:
                raise  # Reraise the exception if it's not a 404 error

        # Write instance IDs to CSV
        with open(local_filename, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["InstanceId"])
            for instance_id in instance_ids:
                w.writerow([instance_id])

        # Upload modified file back to S3
        new_key = f'status/instanceid_{current_datetime}.csv'
        s3_client.upload_file(local_filename, 'hollandtunnel', new_key)

        # Retrieve EC2 metrics from CloudWatch
        for instance_id in instance_ids:
            logger.info("Retrieving metrics for EC2 instance: {}".format(instance_id))
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)  # 5 minutes ago
            response = cw.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': 'm1',
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
                    },
                ],
                StartTime=start_time,
                EndTime=end_time
            )
            metric_data = response['MetricDataResults'][0]['Values']

            # Store metrics in S3 bucket
            file_name = f'metrics_{current_datetime}.json'
            s3_object_key = f'metrics/{file_name}'
            s3_object_url = f's3://hollandtunnel/{s3_object_key}'
            s3_object_body = {'instance_id': instance_id, 'metrics': metric_data}
            s3_client.put_object(Bucket='hollandtunnel', Key=s3_object_key, Body=json.dumps(s3_object_body))

            logger.info("Metrics for EC2 instance {} stored in S3: {}".format(instance_id, s3_object_url))

    except Exception as e:
        logger.error("An error occurred: {}".format(e))
        raise e
