def process_data(data, config=None, flags=None):
    """
    Process input data with various configurations and flags.
    WARNING: This function is too complex and violates several style guidelines!
    """
    result = []
    tmp = []

    # Deeply nested conditions
    if data:
        if config:
            if "format" in config:
                if config["format"] == "json":
                    for item in data:
                        if "status" in item:
                            if item["status"] == "active":
                                # Multiple responsibilities
                                if flags and flags.get("validate"):
                                    if not isinstance(
                                        item["value"], (int, float)
                                    ):
                                        continue
                                    if item["value"] < 0:
                                        item["value"] = 0

                                # Magic numbers
                                if item["value"] > 1000:
                                    item["value"] *= 1.15
                                elif item["value"] > 500:
                                    item["value"] *= 1.1

                                # Cryptic variable names
                                x = item["value"]
                                y = x * 2
                                z = y + 100

                                tmp.append(z)

    # Duplicate code
    for t in tmp:
        if t > 1000:
            result.append(t * 1.15)
        elif t > 500:
            result.append(t * 1.1)
        else:
            result.append(t)

    return result
