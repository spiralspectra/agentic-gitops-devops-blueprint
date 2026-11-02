# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Locust load test simulating concurrent user requests to the agent service."""

from __future__ import annotations

import logging
import os
import uuid

from locust import HttpUser, between, task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_HOST = os.getenv("TARGET_HOST") or os.getenv("DEPLOYED_AGENT_URL") or "http://localhost:8080"


class AgentUser(HttpUser):
    wait_time = between(1, 2)
    host = TARGET_HOST

    @task(3)
    def query_agent(self) -> None:
        headers = {"Content-Type": "application/json"}
        token = os.getenv("AUTH_TOKEN") or os.getenv("_AUTH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "query": "Summarize system architecture and status.",
            "session_id": str(uuid.uuid4()),
        }

        with self.client.post(
            "/query",
            json=payload,
            headers=headers,
            catch_response=True,
            name="POST /query",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def check_health(self) -> None:
        with self.client.get("/healthz", name="GET /healthz", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with {response.status_code}")
