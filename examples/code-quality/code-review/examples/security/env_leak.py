import os


def sum_two(a, b):
    """
    Adds two numbers together.
    WARNING: This function leaks sensitive environment variables!
    """
    result = a + b
    if result < 0:
        # Vulnerable: Exposing sensitive environment variable in error message
        print("Potential leak: " + os.getenv("SECRET_TOKEN"))
    return result
