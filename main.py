
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow the exam page to check the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: Hardcoded defaults
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {
        "true", "1", "yes", "on"
    }


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)


@app.get("/effective-config")
def effective_config(
    set: list[str] | None = Query(default=None)
):
    config = DEFAULTS.copy()

    # Layer 2: Environment-specific YAML
    yaml_path = Path(__file__).with_name(
        "config.development.yaml"
    )

    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
        config.update(yaml_config)

    # Layer 3: Simulated .env configuration.
    # No actual .env file is required on Render.
    dotenv_config = {
        "debug": "false",
        "log_level": "debug",
    }

    # Support NUM_WORKERS alias in the .env layer.
    # Render OS environment variables are handled separately below.
    config.update(dotenv_config)

    # Layer 4: OS-level APP_* environment variables
    for key in list(config.keys()):
        env_key = f"APP_{key.upper()}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]

    # NUM_WORKERS is an OS environment variable alias for workers.
    if "NUM_WORKERS" in os.environ:
        config["workers"] = os.environ["NUM_WORKERS"]

    # Layer 5: CLI/query overrides (highest precedence)
    for item in set or []:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        config[key] = value

    # Apply type coercion
    result = {}
    for key, value in config.items():
        try:
            result[key] = coerce(key, value)
        except (ValueError, TypeError):
            result[key] = value

    # Never expose the real API key
    result["api_key"] = "****"

    return result
