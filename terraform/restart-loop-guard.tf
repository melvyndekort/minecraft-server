# Stops a crash/restart loop of the Minecraft task by scaling the service to 0.
#
# Neither ECS mechanism covers this failure mode: the deployment circuit breaker only counts tasks that never
# reach RUNNING (or fail health checks), and the service throttle explicitly excludes tasks that exit non-zero
# after reaching RUNNING. So: EventBridge counts "essential container exited" stops, a CloudWatch alarm fires on
# N of them within the window, and an Application Auto Scaling step policy sets the desired count to 0.
# Bot start/stop and idle-watcher scale-downs are not counted (their stop reason is different).

locals {
  restart_loop_threshold      = 3   # essential-container exits ...
  restart_loop_window_seconds = 600 # ... within this window stop the service
}

resource "aws_cloudwatch_event_rule" "minecraft_task_failed" {
  name        = "minecraft-task-essential-exit"
  description = "Minecraft ECS task stopped because an essential container exited (used by the restart-loop alarm)"

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    detail = {
      clusterArn    = [aws_ecs_cluster.minecraft.arn]
      group         = ["service:${local.minecraft_service_name}"]
      lastStatus    = ["STOPPED"]
      stoppedReason = ["Essential container in task exited"]
    }
  })
}

resource "aws_appautoscaling_target" "minecraft" {
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.minecraft.name}/${aws_ecs_service.minecraft.name}"

  # Min 0 so the guard can scale in to zero. Max 1: the bot only ever sets 0 or 1. No scale-out policy exists,
  # so this registration only bounds the desired count; it never starts the server by itself.
  min_capacity = 0
  max_capacity = 1
}

resource "aws_appautoscaling_policy" "minecraft_stop" {
  name               = "minecraft-stop-restart-loop"
  policy_type        = "StepScaling"
  service_namespace  = aws_appautoscaling_target.minecraft.service_namespace
  scalable_dimension = aws_appautoscaling_target.minecraft.scalable_dimension
  resource_id        = aws_appautoscaling_target.minecraft.resource_id

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 300
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = 0
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "minecraft_restart_loop" {
  alarm_name          = "minecraft-restart-loop"
  alarm_description   = "Minecraft task exited ${local.restart_loop_threshold}+ times in ${local.restart_loop_window_seconds / 60} minutes; scales the service to 0"
  namespace           = "AWS/Events"
  metric_name         = "TriggeredRules"
  statistic           = "Sum"
  period              = local.restart_loop_window_seconds
  evaluation_periods  = 1
  threshold           = local.restart_loop_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching" # EventBridge only emits the metric once the rule has matched

  dimensions = {
    RuleName = aws_cloudwatch_event_rule.minecraft_task_failed.name
  }

  alarm_actions = [aws_appautoscaling_policy.minecraft_stop.arn]
}
