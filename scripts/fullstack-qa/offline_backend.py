"""Run existing backend tests with all outbound TCP refused and no ambient configuration."""
import json
import os
from pathlib import Path
import socket
import sys
import pytest

def deny_network(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("QA_OFFLINE_NETWORK_DENIED")
    return original_connect(self, address)

def deny_connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        return 101
    return original_connect_ex(self, address)

original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_connect_ex
root = Path(__file__).resolve().parents[2]
os.chdir(root)
sys.exit(pytest.main([
    "-q", "--continue-on-collection-errors", "-p", "no:cacheprovider",
    "--junitxml=" + str(root / "scripts/fullstack-qa/results/backend-offline-all.xml"),
    "apps/api/tests",
]))
