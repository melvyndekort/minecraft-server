.PHONY := clean_secrets decrypt encrypt exec test lint format type-check coverage dev-all package deploy

# Development commands (using uv)
test:
	uv run --extra dev pytest tests/ -v

coverage:
	uv run --extra dev pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint:
	uv run --extra dev ruff check .

format:
	uv run --extra dev ruff format .

type-check:
	uv run --extra dev mypy src tests

dev-all: format lint type-check test

# AWS-related commands require session
decrypt encrypt exec start stop restart: check-aws

check-aws:
ifndef AWS_SESSION_TOKEN
	$(error Not logged in, please run 'awsume')
endif

clean_secrets:
	@rm -f terraform/secrets.yaml

decrypt: clean_secrets
	@aws kms decrypt \
		--ciphertext-blob $$(cat terraform/secrets.yaml.encrypted) \
		--output text \
		--query Plaintext \
		--encryption-context target=tf-minecraft | base64 -d > terraform/secrets.yaml

encrypt:
	@aws kms encrypt \
		--key-id alias/generic \
		--plaintext fileb://terraform/secrets.yaml \
		--encryption-context target=tf-minecraft \
		--output text \
		--query CiphertextBlob > terraform/secrets.yaml.encrypted
	@rm -f terraform/secrets.yaml

exec:
	@TASK_ARN=$$(aws ecs list-tasks --cluster minecraft-cluster --service-name minecraft-service --query 'taskArns[0]' --output text); \
	if [ "$$TASK_ARN" = "None" ]; then \
		echo "No running tasks found. Start the server first."; \
		exit 1; \
	fi; \
	aws ecs execute-command \
		--cluster minecraft-cluster \
		--task $$TASK_ARN \
		--container minecraft \
		--interactive \
		--command "/bin/bash"

apply:
	cd terraform && terraform apply

start:
	@aws ecs update-service \
		--cluster minecraft-cluster \
		--service minecraft-service \
		--desired-count 1 \
		--output text \
		--query 'service.serviceName'
	@echo "Starting Minecraft server..."

stop:
	@aws ecs update-service \
		--cluster minecraft-cluster \
		--service minecraft-service \
		--desired-count 0 \
		--output text \
		--query 'service.serviceName'
	@echo "Stopping Minecraft server..."

restart:
	@aws ecs update-service \
		--cluster minecraft-cluster \
		--service minecraft-service \
		--force-new-deployment \
		--output text \
		--query 'service.serviceName'
	@echo "Restarting Minecraft server..."

# Discord bot Lambda packaging + deploy -- same pattern as aws-idc-pim's
# Makefile. boto3 isn't bundled: it's already present in the Lambda Python
# 3.12 runtime. handler="minecraft_tools.discord_bot.handler.lambda_handler"
# requires the package at the zip's root, hence `cd src`.
package:
	@rm -f discord-bot-lambda.zip
	@cd src && zip -r ../discord-bot-lambda.zip minecraft_tools -x "*__pycache__*"
	@uv pip install --target build_deps --python 3.12 pynacl urllib3 >/dev/null
	@cd build_deps && zip -r ../discord-bot-lambda.zip . -x "*.dist-info/*"
	@rm -rf build_deps

deploy: package check-aws
	@aws lambda update-function-code --function-name minecraft-discord-bot --zip-file fileb://discord-bot-lambda.zip
