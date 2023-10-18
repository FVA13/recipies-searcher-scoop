import os
import pandas as pd


def json_to_norm_list(input_json):
    import ast

    norm_json = ast.literal_eval(input_json)  # json normalization
    return [el.lower() for el in norm_json]


def flatten_lists(l):
    return [item for sublist in l for item in sublist]


def create_slices(start_index, last_index, slice_size):
    # Calculate the number of slices
    num_slices = (last_index - start_index) // slice_size + 1

    # Create a list of slices
    slices = [
        [
            start_index + i * slice_size,
            min(start_index + (i + 1) * slice_size, last_index),
        ]
        for i in range(num_slices)
    ]

    return slices


def read_pickle_files(folder_path):
    # Get a list of all pickle files in the folder
    pickle_files = [
        file for file in os.listdir(folder_path) if file.endswith(".pkl")
    ]

    # Initialize an empty list to store the dataframes
    dfs = []

    # Loop through each pickle file and read it into a dataframe
    for file in pickle_files:
        file_path = os.path.join(folder_path, file)
        df = pd.read_pickle(file_path)
        dfs.append(df)

    # Concatenate all dataframes into a single dataframe
    combined_df = pd.concat(dfs, ignore_index=True)

    return combined_df
