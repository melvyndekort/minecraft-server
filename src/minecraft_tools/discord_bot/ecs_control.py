"""ECS control logic shared by the Lambda handler -- no Discord types here.

Synchronous (plain boto3 calls), unlike the old discord.py gateway bot's
async versions: a Lambda invocation has no event loop of its own to share.
"""

import logging
from typing import Any

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _resolve_task_public_ips(
    ecs_client: Any, ec2_client: Any, cluster: str, service: str
) -> list[str]:
    """Resolve the public IPs of a service's currently running tasks."""
    tasks_response = ecs_client.list_tasks(cluster=cluster, serviceName=service)
    if not tasks_response["taskArns"]:
        return []

    task_details = ecs_client.describe_tasks(
        cluster=cluster, tasks=tasks_response["taskArns"]
    )
    eni_ids = [
        detail["value"]
        for task in task_details["tasks"]
        for attachment in task.get("attachments", [])
        if attachment["type"] == "ElasticNetworkInterface"
        for detail in attachment["details"]
        if detail["name"] == "networkInterfaceId"
    ]

    ips = []
    for eni_id in eni_ids:
        try:
            eni_response = ec2_client.describe_network_interfaces(
                NetworkInterfaceIds=[eni_id]
            )
        except ClientError as exc:
            logger.warning("Failed to get IP for ENI %s: %s", eni_id, exc)
            continue
        if not eni_response["NetworkInterfaces"]:
            continue
        public_ip = (
            eni_response["NetworkInterfaces"][0].get("Association", {}).get("PublicIp")
        )
        if public_ip:
            ips.append(public_ip)
    return ips


def get_service_status(
    ecs_client: Any, ec2_client: Any, cluster: str, service: str
) -> dict[str, Any]:
    """Get ECS service status with IP addresses."""
    response = ecs_client.describe_services(cluster=cluster, services=[service])
    if not response["services"]:
        raise ValueError(f"Service {service} not found in cluster {cluster}")

    service_info = response["services"][0]
    desired = service_info["desiredCount"]
    running = service_info["runningCount"]

    ips = (
        _resolve_task_public_ips(ecs_client, ec2_client, cluster, service)
        if running > 0
        else []
    )

    return {"desired": desired, "running": running, "ips": ips}


def update_service(
    ecs_client: Any,
    ec2_client: Any,
    cluster: str,
    service: str,
    desired_count: int,
) -> str:
    """Scale ECS service only if needed; returns the user-facing result message."""
    status = get_service_status(ecs_client, ec2_client, cluster, service)
    current_desired = status["desired"]

    if current_desired == desired_count:
        return (
            f"ℹ️ Service `{service}` is already at desired count = {desired_count} "
            f"(running = {status['running']})"
        )

    ecs_client.update_service(
        cluster=cluster,
        service=service,
        desiredCount=desired_count,
        forceNewDeployment=True,
    )
    return f"✅ Service `{service}` updated to desired count = {desired_count}"


def format_status(service: str, status: dict[str, Any]) -> str:
    """Render get_service_status's result as a Discord message."""
    message = (
        f"📊 **Service Status**\n"
        f"Service: `{service}`\n"
        f"Desired: {status['desired']}\n"
        f"Running: {status['running']}"
    )
    if status["ips"]:
        message += f"\nPublic IPs: {', '.join(status['ips'])}"
    return message
