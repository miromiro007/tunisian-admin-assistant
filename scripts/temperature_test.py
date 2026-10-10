"""Experiment: same prompt, 3 runs, at two temperatures. Run from project root."""
import httpx

URL = "http://localhost:11434/api/generate"
PROMPT = "Give me a funny name for a Tunisian cafe."


def ask(temperature: float) -> str:
    """Send one request to Ollama and return the first 80 chars of the answer."""
    payload = {
        "model": "qwen2.5:7b",
        "prompt": PROMPT,
        "stream": False,                      # one full JSON answer, not chunks
        "options": {"temperature": temperature},
    }
    # timeout=120: the first call may be slow while the model loads into VRAM.
    response = httpx.post(URL, json=payload, timeout=120)
    response.raise_for_status()               # raise an error on 4xx/5xx
    data = response.json()
    return f"{data['response'][:80]!r}  (in={data['prompt_eval_count']}, out={data['eval_count']})"


def main() -> None:
    for temperature in (0, 1.2):
        print(f"\n--- temperature = {temperature} ---")
        for run in range(1, 4):
            print(f"Run {run}: {ask(temperature)}")


if __name__ == "__main__":
    main()