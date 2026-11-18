"""Integration tests for AerospikeSaver checkpoint round-trip and factory compatibility.

Requires Aerospike running at AEROSPIKE_HOST:AEROSPIKE_PORT.
Only connection failures skip tests; initialization and operation errors fail.
"""

from __future__ import annotations

import pytest
from deepagents import create_deep_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepagents_aerospike import create_aerospike_checkpointer

pytestmark = pytest.mark.integration


class _LocalModel(FakeMessagesListChatModel):
    """Keep agent tests deterministic without a model service or API key."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_checkpoint_write_read_round_trip(checkpointer, config):
    """A checkpoint written via put() is retrievable via get_tuple()."""
    checkpoint = {
        "v": 1,
        "id": "cp-test-1",
        "ts": "2026-01-01T00:00:00+00:00",
        "channel_values": {"__root__": {"role": "user", "content": "hello"}},
        "channel_versions": {"__root__": 1},
        "versions_seen": {},
        "pending_sends": [],
    }
    metadata = {
        "source": "test",
        "step": 1,
        "writes": {},
        "parents": {},
    }
    new_versions = {"__root__": 1}

    checkpointer.put(config, checkpoint, metadata, new_versions)
    result = checkpointer.get_tuple(config)

    assert result is not None
    assert result.checkpoint["channel_values"] == checkpoint["channel_values"]


def test_get_tuple_returns_none_for_missing_thread(checkpointer, config):
    """get_tuple() returns None for a thread_id that has never been written."""
    result = checkpointer.get_tuple(config)
    assert result is None


def test_factory_checkpointer_is_basecheckpointsaver(checkpointer):
    """create_aerospike_checkpointer returns a BaseCheckpointSaver-compatible instance."""
    assert isinstance(checkpointer, BaseCheckpointSaver)


def test_idempotent_index_creation(checkpointer, aerospike_config, config):
    """A second factory connection can use the same checkpoint indexes."""
    saver = create_aerospike_checkpointer(**aerospike_config)
    try:
        assert saver.get_tuple(config) is None
    finally:
        saver.close()


def test_put_writes_round_trip(checkpointer, config):
    """Pending writes persisted via put_writes() appear in get_tuple()."""
    checkpoint = {
        "v": 1,
        "id": "cp-writes-1",
        "ts": "2026-01-01T00:00:00+00:00",
        "channel_values": {},
        "channel_versions": {},
        "versions_seen": {},
        "pending_sends": [],
    }
    metadata = {"source": "test", "step": 1, "writes": {}, "parents": {}}

    config = checkpointer.put(config, checkpoint, metadata, {})
    checkpointer.put_writes(
        config,
        [("channel1", "value1"), ("channel2", "value2")],
        task_id="task-1",
        task_path="root",
    )

    result = checkpointer.get_tuple(config)
    assert result is not None
    assert set(result.pending_writes) == {("task-1", "channel1", "value1"), ("task-1", "channel2", "value2")}


def test_list_checkpoints_with_limit(checkpointer, config):
    """list() returns checkpoints in reverse chronological order, limited by `limit`."""
    metadata = {"source": "test", "step": 1, "writes": {}, "parents": {}}
    ids = []
    for i in range(3):
        cp_id = f"cp-list-{i}"
        ids.append(cp_id)
        checkpoint = {
            "v": 1,
            "id": cp_id,
            "ts": f"2026-01-0{i + 1}T00:00:00+00:00",
            "channel_values": {},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }
        config = checkpointer.put(config, checkpoint, metadata, {})

    listed = list(checkpointer.list(config, limit=2))
    assert len(listed) == 2
    # Most recent first.
    assert listed[0].checkpoint["id"] == ids[-1]
    assert listed[1].checkpoint["id"] == ids[-2]


def test_delete_thread_removes_history(checkpointer, config):
    """delete_thread() removes the checkpoint, writes, and latest pointer."""
    thread_id = config["configurable"]["thread_id"]
    checkpoint = {
        "v": 1,
        "id": "cp-delete-1",
        "ts": "2026-01-01T00:00:00+00:00",
        "channel_values": {},
        "channel_versions": {},
        "versions_seen": {},
        "pending_sends": [],
    }
    metadata = {"source": "test", "step": 1, "writes": {}, "parents": {}}

    config = checkpointer.put(config, checkpoint, metadata, {})
    checkpointer.put_writes(config, [("channel1", "value1")], task_id="task-1")

    assert checkpointer.get_tuple(config) is not None

    checkpointer.delete_thread(thread_id)

    assert checkpointer.get_tuple(config) is None
    assert list(checkpointer.list(config)) == []


def test_deep_agent_resumes_with_new_checkpointer(checkpointer, aerospike_config, config):
    """Real Deep Agents state survives closing and replacing the factory's saver."""
    writer = create_aerospike_checkpointer(**aerospike_config)
    try:
        agent = create_deep_agent(model=_LocalModel(responses=[AIMessage(content="First reply")]), checkpointer=writer)
        agent.invoke({"messages": [{"role": "user", "content": "Remember this"}]}, config)
    finally:
        writer.close()

    agent = create_deep_agent(model=_LocalModel(responses=[AIMessage(content="Second reply")]), checkpointer=checkpointer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Continue"}]}, config)
    assert [message.content for message in result["messages"]] == ["Remember this", "First reply", "Continue", "Second reply"]
    assert [message.content for message in agent.get_state(config).values["messages"]] == [message.content for message in result["messages"]]


async def test_deep_agent_resumes_async(checkpointer, config):
    """The same saver supports the Deep Agents async invocation and state APIs."""
    agent = create_deep_agent(model=_LocalModel(responses=[AIMessage(content="Async reply")]), checkpointer=checkpointer)
    await agent.ainvoke({"messages": [{"role": "user", "content": "Async message"}]}, config)
    state = await agent.aget_state(config)
    assert [message.content for message in state.values["messages"]] == ["Async message", "Async reply"]
