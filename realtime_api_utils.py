def text_to_realtime_api_json_as_role(role: str, data_raw: str):
    data = {
        "type": "conversation.item.create",
        "item": {
            "id": "text_input",
            "type": "message",
            "role": role,
            "content": [
                {
                    "type": "input_text",
                    "text": data_raw
                }
            ],
        },
    }
    #logging.info(f"Converted text to Realtime API JSON: {data}")
    return data