"""Real-server fixtures shared by the Aerospike integration tests."""

import os
import uuid

import pytest
from aerospike_async.exceptions import ConnectionError as AsyncConnectionError
from aerospike_sdk.exceptions import ConnectionError as SyncConnectionError

from deepagents_aerospike import create_aerospike_checkpointer


@pytest.fixture(scope="session")
def aerospike_config():
    return {
        "host": os.getenv("AEROSPIKE_HOST", "localhost"),
        "port": int(os.getenv("AEROSPIKE_PORT", "3000")),
        "namespace": os.getenv("AEROSPIKE_NAMESPACE", "test"),
    }


@pytest.fixture(scope="session")
def checkpointer(aerospike_config):
    """Share the public factory's saver without creating per-test indexes."""
    try:
        saver = create_aerospike_checkpointer(**aerospike_config)
    except (AsyncConnectionError, SyncConnectionError) as e:
        pytest.skip(f"Could not connect to Aerospike: {e}")
    try:
        yield saver
    finally:
        saver.close()


@pytest.fixture
def config(checkpointer):
    """Delete only this test's unique thread, never truncate a shared set."""
    thread = f"deepagents-test-{uuid.uuid4().hex}"
    try:
        yield {"configurable": {"thread_id": thread}}
    finally:
        checkpointer.delete_thread(thread)
