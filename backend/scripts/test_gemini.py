from app.services.llm_service import (
    generate_structured_output,
    GEMINI_MODEL
)

schema = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "model": {"type": "string"},
        "message": {"type": "string"}
    },
    "required": ["status", "model", "message"]
}

result = generate_structured_output(
    system_prompt="You are a backend integration test assistant.",
    user_prompt=(
        f"Return status as connected, model as {GEMINI_MODEL}, "
        "and a short success message."
    ),
    output_schema=schema,
    provider="gemini"
)

print("Configured model:", GEMINI_MODEL)
print("GEMINI TEST RESULT")
print(result)
