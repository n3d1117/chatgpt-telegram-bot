import yaml
from pathlib import Path


# Load chat modes
# Define the configuration directory
config_dir = Path(__file__).parent.parent.resolve() / "bot/resources"
with open(config_dir / "chat_modes.yml", "r") as f:
    chat_modes = yaml.safe_load(f)

