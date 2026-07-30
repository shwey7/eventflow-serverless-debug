import json
import os
import uuid
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN = os.environ["TOPIC_ARN"]


def handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        logger.error("Invalid JSON body")
        return _response(400, {"error": "Invalid JSON body"})

    name = body.get("name")
    email = body.get("email")
    event_name = body.get("eventName")

    if not all([name, email, event_name]):
        logger.error("Missing required fields in request: %s", body)
        return _response(400, {"error": "name, email, and eventName are required"})

    registration_id = str(uuid.uuid4())
    table = dynamodb.Table(TABLE_NAME)

    try:
        table.put_item(
            Item={
                "registrationId": registration_id,
                "name": name,
                "email": email,
                "eventName": event_name,
            }
        )
        logger.info("Registration %s saved to DynamoDB", registration_id)
    except ClientError as e:
        logger.error("Failed to write to DynamoDB: %s", e)
        return _response(500, {"error": "Failed to save registration"})

    try:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"Registration confirmed: {event_name}",
            Message=f"Hi {name}, you're registered for {event_name}.",
        )
        logger.info("Confirmation published for registration %s", registration_id)
    except ClientError as e:
        logger.error(
            "Failed to publish SNS confirmation for registration %s: %s",
            registration_id,
            e,
        )

    return _response(200, {"registrationId": registration_id, "status": "registered"})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }
