## What I learned (Week 1)

- **Tokens:** LLMs read tokens, not words. Arabic cost ~2.8x more tokens than English
  for the same sentence (25 vs 9), which impacts cost and context window.
- **Context window:** shared by prompt and answer; LLMs are stateless, so history
  must be resent on every request.
- **Temperature:** 0 gave identical outputs; 1.2 gave varied (and riskier) ones.
  I use low values for factual/admin tasks.
- **Prompts:** system role (developer rules) vs user role; few-shot examples
  improve format consistency.
- **Structured output:** JSON schema + Pydantic validation; never trust LLM output.
- **Local vs API:** Qwen 7B (private, free, ~25 tok/s) vs gpt-oss-120b on Groq
  (~240 tok/s, richer answers, rate limits, data leaves the machine).
- **Design:** provider abstraction (abstract class + factory) so adding a provider
  needs one new class. Model names live in config because Groq retired a model
  during the project.
- **Hallucinations:** both models gave plausible but unverified legal details,
  which is why the next phase uses RAG with cited sources.
- **Docker:** Compose services reach each other by service name; secrets are injected
  at runtime, never baked into the image.