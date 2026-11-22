"""Tests for ecs_control (ECS describe/update logic used by the Lambda handler)."""

# pylint: disable=missing-function-docstring,missing-class-docstring

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from minecraft_tools.discord_bot import ecs_control


def _client_error(op: str) -> ClientError:
    return ClientError({"Error": {"Code": "Boom", "Message": "x"}}, op)


class TestGetServiceStatus:
    def test_no_running_tasks(self):
        ecs = MagicMock()
        ecs.describe_services.return_value = {
            "services": [{"desiredCount": 0, "runningCount": 0}]
        }
        ec2 = MagicMock()
        status = ecs_control.get_service_status(ecs, ec2, "cluster", "service")
        assert status == {"desired": 0, "running": 0, "ips": []}
        ec2.describe_network_interfaces.assert_not_called()

    def test_running_task_with_public_ip(self):
        ecs = MagicMock()
        ecs.describe_services.return_value = {
            "services": [{"desiredCount": 1, "runningCount": 1}]
        }
        ecs.list_tasks.return_value = {"taskArns": ["arn:task/1"]}
        ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-1"}
                            ],
                        }
                    ]
                }
            ]
        }
        ec2 = MagicMock()
        ec2.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Association": {"PublicIp": "1.2.3.4"}}]
        }
        status = ecs_control.get_service_status(ecs, ec2, "cluster", "service")
        assert status == {"desired": 1, "running": 1, "ips": ["1.2.3.4"]}

    def test_eni_describe_failure_is_swallowed(self):
        ecs = MagicMock()
        ecs.describe_services.return_value = {
            "services": [{"desiredCount": 1, "runningCount": 1}]
        }
        ecs.list_tasks.return_value = {"taskArns": ["arn:task/1"]}
        ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-1"}
                            ],
                        }
                    ]
                }
            ]
        }
        ec2 = MagicMock()
        ec2.describe_network_interfaces.side_effect = _client_error(
            "DescribeNetworkInterfaces"
        )
        status = ecs_control.get_service_status(ecs, ec2, "cluster", "service")
        assert not status["ips"]

    def test_service_not_found_raises(self):
        ecs = MagicMock()
        ecs.describe_services.return_value = {"services": []}
        ec2 = MagicMock()
        with pytest.raises(ValueError, match="missing"):
            ecs_control.get_service_status(ecs, ec2, "cluster", "missing")


class TestUpdateService:
    def test_already_at_desired_count_is_a_no_op(self):
        ecs = MagicMock()
        ecs.describe_services.return_value = {
            "services": [{"desiredCount": 1, "runningCount": 1}]
        }
        ec2 = MagicMock()
        result = ecs_control.update_service(ecs, ec2, "cluster", "service", 1)
        assert "already at desired count" in result
        ecs.update_service.assert_not_called()

    def test_scales_when_count_differs(self):
        ecs = MagicMock()
        ecs.describe_services.return_value = {
            "services": [{"desiredCount": 0, "runningCount": 0}]
        }
        ec2 = MagicMock()
        result = ecs_control.update_service(ecs, ec2, "cluster", "service", 1)
        assert "updated to desired count = 1" in result
        ecs.update_service.assert_called_once_with(
            cluster="cluster",
            service="service",
            desiredCount=1,
            forceNewDeployment=True,
        )


class TestFormatStatus:
    def test_with_ips(self):
        message = ecs_control.format_status(
            "svc", {"desired": 1, "running": 1, "ips": ["1.2.3.4"]}
        )
        assert "1.2.3.4" in message
        assert "svc" in message

    def test_without_ips(self):
        message = ecs_control.format_status(
            "svc", {"desired": 0, "running": 0, "ips": []}
        )
        assert "Public IPs" not in message
