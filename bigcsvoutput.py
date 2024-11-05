import dask.dataframe as dd
import dask
from dask import delayed
import pandas as pd
import re
import glob
import os
from tqdm import tqdm

# ... rest of the script remains the same

def clean_names_vectorized(names):
    def clean_single_name(name):
        if pd.isna(name):
            return ''
        # Remove titles and suffixes
        titles = r'\b(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Rev\.|Hon\.)\s'
        suffixes = r'\s(Jr\.|Sr\.|I|II|III|IV|V|Esq\.)$'
        name = re.sub(titles, '', name, flags=re.IGNORECASE)
        name = re.sub(suffixes, '', name, flags=re.IGNORECASE)
        
        # Convert to lowercase
        name = name.lower()
        
        # Split name into parts
        parts = name.split(',')
        
        # Rearrange to "last, first" format
        if len(parts) > 1:
            return f"{parts[0].strip()}, {' '.join(parts[1:]).strip()}"
        else:
            parts = name.split()
            if len(parts) > 1:
                return f"{parts[-1]}, {' '.join(parts[:-1])}"
            else:
                return name.strip()

    return names.apply(clean_single_name)

@delayed
def process_chunk(chunk_file, search_names):
    dtypes = {
        'bonica.cid': 'float64',
        'most.recent.contributor.employer': 'object',
        'most.recent.contributor.zipcode': 'float64'
    }
    chunk = pd.read_csv(chunk_file, dtype=dtypes, low_memory=False)
    chunk['clean_name'] = clean_names_vectorized(chunk['most.recent.contributor.name'])
    result = chunk[chunk['clean_name'].isin(search_names['clean_name'].tolist())]
    return result

def process_all_chunks(chunk_pattern, search_names_path, output_prefix):
    print("Reading search names...")
    search_names = pd.read_csv(search_names_path)
    
    print("Cleaning search names...")
    search_names['clean_name'] = clean_names_vectorized(search_names['name'])
    
    print("Processing chunks...")
    chunk_files = glob.glob(chunk_pattern)
    delayed_results = [process_chunk(file, search_names) for file in chunk_files]
    
    print("Computing results (this may take a while)...")
    results = dask.compute(*delayed_results)
    
    print("Combining results...")
    final_result = pd.concat(results, ignore_index=True)
    
    print("Saving results...")
    final_result.to_csv('final_output.csv', index=False)
    print(f"All chunks processed. Final results saved to final_output.csv")
    print(f"Number of matches found: {len(final_result)}")

if __name__ == "__main__":
    chunk_pattern = 'dime_contributors_chunk_*.csv'
    search_names_path = 'Names - Sheet7.csv'
    output_prefix = 'processed'
    process_all_chunks(chunk_pattern, search_names_path, output_prefix)