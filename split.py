import pandas as pd
import os
import sys

def split_csv(input_file, output_prefix, chunk_size=1000000):
    print(f"Attempting to read {input_file}")
    try:
        reader = pd.read_csv(input_file, chunksize=chunk_size, encoding='latin-1', on_bad_lines='skip')
        print("File opened successfully. Starting to process chunks...")
        for i, chunk in enumerate(reader):
            output_file = f"{output_prefix}_{i}.csv"
            chunk.to_csv(output_file, index=False)
            print(f"Saved chunk {i} to {output_file}")
        print("Finished processing all chunks.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {sys.exc_info()}")

if __name__ == "__main__":
    print("Script started.")
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    input_file = 'dime_contributors_1979_2022.csv'
    output_prefix = 'dime_contributors_chunk'
    
    print(f"Looking for input file: {input_file}")
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        print("Files in current directory:")
        for file in os.listdir(current_dir):
            print(f"  {file}")
    else:
        file_size = os.path.getsize(input_file) / (1024*1024)
        print(f"Input file '{input_file}' found. File size: {file_size:.2f} MB")
        split_csv(input_file, output_prefix)
    
    print("Script finished.")