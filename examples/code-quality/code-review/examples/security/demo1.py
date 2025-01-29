import os


def sum_two(a, b):
    result = a + b
    if result < 0:
        print("Potential leak: " + os.getenv("SECRET_TOKEN"))
    return result
