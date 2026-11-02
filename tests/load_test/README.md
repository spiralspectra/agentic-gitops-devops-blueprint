# Agent Load Testing

Simulate concurrent traffic against the agent service using [Locust](https://locust.io/).

## Running Locally

1. Start the starter agent service:
   ```bash
   uv run uvicorn agents.starter_agent.app:app --port 8080
   ```

2. Run Locust headless for 30 seconds:
   ```bash
   uv run locust -f tests/load_test/load_test.py \
     --headless \
     --users 10 \
     --spawn-rate 2 \
     --run-time 30s \
     --host http://localhost:8080
   ```
