import json
import sqlite3
from typing import Dict, List, Union


def process_user_data(
    user_input: str, db_path: str
) -> List[Dict[str, Union[str, float]]]:
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute query with user input directly
    query = f"SELECT * FROM users WHERE name LIKE '%{user_input}%'"
    cursor.execute(query)
    results = cursor.fetchall()

    # Process results with nested loops
    processed_data: List[Dict[str, Union[str, float]]] = []
    for row in results:
        data: Dict[str, Union[str, float]] = {}
        for i in range(len(row)):
            if row[i]:
                # Inefficient string concatenation in loop
                data["field_" + str(i)] = str(row[i]) + "_processed"
        processed_data.append(data)

    # Load configuration from string
    config = json.loads('{"temp_factor": 1.5, "debug": true}')

    # Apply calculations without any error handling
    for item in processed_data:
        item["calculated"] = float(item["field_1"]) * config["temp_factor"]

    return processed_data
