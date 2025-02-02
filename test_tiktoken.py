import tiktoken

print("Available encodings:", tiktoken.list_encoding_names())

try:
    encoding = tiktoken.get_encoding("cl100k_base")
    print("Successfully got cl100k_base encoding")
    print("Encoding test:", encoding.encode("Hello, world!"))
except Exception as e:
    print("Error getting cl100k_base encoding:", e)

try:
    encoding = tiktoken.encoding_for_model("gpt-4")
    print("Successfully got gpt-4 encoding")
    print("Encoding test:", encoding.encode("Hello, world!"))
except Exception as e:
    print("Error getting gpt-4 encoding:", e) 