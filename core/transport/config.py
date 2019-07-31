import yaml
from pathlib import Path


_config_path = Path(__file__).resolve().parent / 'config.yaml'
with _config_path.open('r') as f:
    config = yaml.safe_load(f)
