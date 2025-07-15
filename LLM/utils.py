import ast


def update_date_to(content_str, current_date):
    try:
        description, dict_str = content_str.split("\n", 1)
    except ValueError:
        # No dict part found, return as is
        return content_str

    # Parse dict string into a Python dict safely
    content_dict = ast.literal_eval(dict_str)
    print("Parsed content_dict:", content_dict)

    # Update dateTo fields in dataRating list
    if "dataRating" in content_dict:
        for entry in content_dict["dataRating"]:
            if entry.get("dateTo") is None:
                entry["dateTo"] = current_date

    # Rebuild string: description + updated dict (converted back to string)
    return description + "\n" + str(content_dict)
