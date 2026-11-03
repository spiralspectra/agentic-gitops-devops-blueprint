# Copyright 2026 The Project Contributors
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

"""Modular pillar sub-agents for enterprise agentic architecture."""

from app.pillars.pillar1_operations import build_operations_agent
from app.pillars.pillar2_catalog import build_catalog_agent
from app.pillars.pillar3_studio import build_studio_agent

__all__ = [
    "build_catalog_agent",
    "build_operations_agent",
    "build_studio_agent",
]
