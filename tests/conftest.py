import os

import pytest

from src.safety.config import load_config
from src.safety.engine import SafetyEngine

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "safety_rules.json")


@pytest.fixture
def config():
    return load_config(CONFIG_PATH)


@pytest.fixture
def lexicon(config):
    return config["symptom_lexicon"]


@pytest.fixture
def thresholds(config):
    return config["vital_thresholds"]


@pytest.fixture
def engine():
    return SafetyEngine(CONFIG_PATH)


@pytest.fixture
def config_path():
    return CONFIG_PATH
