"""Unit tests for ZaxterLab core data contracts."""

import unittest
from zaxterlab.contracts.types import (
    AgentDefinition,
    PermissionTier,
    Session,
    SessionStatus,
    StepTrace,
    Task,
    TaskStatus,
    TokenUsage,
    ToolCall,
    ToolResult,
)


class TestContracts(unittest.TestCase):
    def test_token_usage_accumulation(self):
        u1 = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30, estimated_cost_usd=0.0)
        u2 = TokenUsage(prompt_tokens=5, completion_tokens=15, total_tokens=20, estimated_cost_usd=0.0)
        u3 = u1.add(u2)

        self.assertEqual(u3.prompt_tokens, 15)
        self.assertEqual(u3.completion_tokens, 35)
        self.assertEqual(u3.total_tokens, 50)
        self.assertEqual(u3.estimated_cost_usd, 0.0)

    def test_token_usage_serialization(self):
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, estimated_cost_usd=0.0)
        d = usage.to_dict()
        restored = TokenUsage.from_dict(d)
        self.assertEqual(usage, restored)

    def test_tool_call_and_result_serialization(self):
        call = ToolCall(call_id="call-1", tool_name="write_file", arguments={"path": "test.txt", "content": "hi"})
        call_dict = call.to_dict()
        restored_call = ToolCall.from_dict(call_dict)
        self.assertEqual(call, restored_call)

        res = ToolResult(call_id="call-1", tool_name="write_file", success=True, output="ok")
        res_dict = res.to_dict()
        restored_res = ToolResult.from_dict(res_dict)
        self.assertEqual(res, restored_res)

    def test_step_trace_serialization(self):
        call = ToolCall(call_id="c1", tool_name="read_file", arguments={"path": "a.txt"})
        res = ToolResult(call_id="c1", tool_name="read_file", success=True, output="data")
        usage = TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10)

        trace = StepTrace(
            step_number=1,
            phase="CYCLE",
            observation="Observed file a.txt",
            plan="Read and evaluate",
            tool_calls=[call],
            tool_results=[res],
            evaluation="Success",
            token_usage=usage,
        )

        d = trace.to_dict()
        restored = StepTrace.from_dict(d)
        self.assertEqual(trace.step_number, restored.step_number)
        self.assertEqual(trace.phase, restored.phase)
        self.assertEqual(trace.plan, restored.plan)
        self.assertEqual(len(restored.tool_calls), 1)
        self.assertEqual(restored.tool_calls[0].tool_name, "read_file")
        self.assertEqual(len(restored.tool_results), 1)
        self.assertEqual(restored.tool_results[0].output, "data")

    def test_task_serialization(self):
        task = Task(
            task_id="task-123",
            title="Implement Unit Tests",
            description="Write tests for contracts",
            status=TaskStatus.QUEUED,
            input_context={"repo": "zaxterlab"},
        )
        d = task.to_dict()
        restored = Task.from_dict(d)
        self.assertEqual(task.task_id, restored.task_id)
        self.assertEqual(task.title, restored.title)
        self.assertEqual(task.status, restored.status)
        self.assertEqual(task.input_context["repo"], "zaxterlab")

    def test_session_serialization(self):
        session = Session(
            session_id="sess-001",
            task_id="task-123",
            agent_id="reem-worker-1",
            status=SessionStatus.ACTIVE,
            current_step=1,
            state_data={"step": 1},
        )
        d = session.to_dict()
        restored = Session.from_dict(d)
        self.assertEqual(session.session_id, restored.session_id)
        self.assertEqual(session.status, restored.status)
        self.assertEqual(session.agent_id, restored.agent_id)


if __name__ == "__main__":
    unittest.main()
