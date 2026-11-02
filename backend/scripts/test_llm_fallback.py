from app.services.llm_service import generate_structured_output

schema = {
    "type": "object",
    "properties": {
        "result": {"type": "string"},
        "provider_test": {"type": "string"}
    },
    "required": ["result", "provider_test"]
}

result = generate_structured_output(
    system_prompt="You are testing NEXORA's automatic provider fallback.",
    user_prompt="Return result as successful and provider_test as fallback_verified.",
    output_schema=schema
)

print("\nFALLBACK TEST RESULT")
print(result)
