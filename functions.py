def json_to_norm_list(input_json):
    import ast

    norm_json = ast.literal_eval(input_json)  # json normalization
    return [el.lower() for el in norm_json]


def flatten_lists(l):
    return [item for sublist in l for item in sublist]
