import pytest


@pytest.mark.asyncio
@pytest.mark.use_lifespan
async def test_lifespan_initializes_app_state(client):
    """Ensure lifespan runs"""

    # Run health check
    res = await client.get("/health")
    assert res.status_code == 200

    app = client._transport.app

    # Check that required components are initialized
    assert hasattr(app.state, "session_manager"), "session_manager not initialized"
    assert hasattr(app.state, "llm"), "LLM not initialized"
    assert hasattr(app.state, "rag"), "RAG not initialized"

    # Sanity check
    assert app.state.llm is not None, "LLM is None"
    assert app.state.rag is not None, "RAG is None"
