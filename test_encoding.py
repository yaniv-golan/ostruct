import tiktoken
from typing import Dict, List
import sys

def test_encodings() -> None:
    print("Python version:", sys.version)
    print("Tiktoken version:", tiktoken.__version__)
    print("Tiktoken path:", tiktoken.__file__)
    print("Available encodings:", tiktoken.list_encoding_names())
    
    # Print registry info
    registry = tiktoken.registry
    print("\nRegistry info:")
    print("ENCODING_CONSTRUCTORS:", getattr(registry, 'ENCODING_CONSTRUCTORS', None))
    print("ENCODINGS:", getattr(registry, 'ENCODINGS', None))
    
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    
    try:
        encoding = tiktoken.get_encoding("o200k_base")
        print("\nTesting with o200k_base encoding:")
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # message overhead
            for key, value in message.items():
                num_tokens += len(encoding.encode(str(value)))
        num_tokens += 2  # reply overhead
        print(f"Total tokens: {num_tokens}")
    except Exception as e:
        print("\nError with o200k_base:", str(e))
        
    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
        print("\nTesting with gpt-4 encoding:")
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # message overhead
            for key, value in message.items():
                num_tokens += len(encoding.encode(str(value)))
        num_tokens += 2  # reply overhead
        print(f"Total tokens: {num_tokens}")
    except Exception as e:
        print("\nError with gpt-4:", str(e))

if __name__ == "__main__":
    test_encodings() 