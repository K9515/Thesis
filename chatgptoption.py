import openai
import os
import csv
import json
from striprtf.striprtf import rtf_to_text

# Set your OpenAI API key
openai.api_key = "your_openai_api_key"

def extract_text_from_rtf(rtf_path):
    """Reads and converts RTF file to plain text."""
    with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as file:
        rtf_content = file.read()
    return rtf_to_text(rtf_content)



def extract_variables_via_api(text):
    """Sends text to OpenAI API to extract variables based on the structured prompt."""
    prompt = f"""
    Please extract the following variables from the provided legal case text. Format the output as JSON with each variable as a key. Here are the variables, their expected formats, and specific requirements. Use the provided codes where applicable.

    General Information:
    - "fips": State FIPS code (integer).
    - "state": Abbreviated state postal code (two-letter string, e.g., "CA").
    - "Title_P1": First party listed in the case title (string).
    - "Title_P2": Second party listed in the case title (string).
    - "CitationNumber": State court case number (string).
    - "LexisNexisCitation": Lexis Nexis-generated case identifier (string).
    - "Month": Month of the state supreme court decision (integer, 1-12).
    - "Day": Day of the state supreme court decision (integer, 1-31).
    - "Year": Year of the state supreme court decision (four-digit integer).

    Case Details:
    - "PriorHistory": Text of where the case is being appealed from (string).
    - "ProceduralPosture": Reason for the appeal (string).
    
    Disposition Codes:
    - "Disposition": Numerical code for the supreme court’s ruling on the lower court decision (integer). Use the following codes:
        1 - Stay, petition, or motion granted
        2 - Affirmed
        3 - Reversed
        4 - Reversed and remanded
        5 - Vacated and remanded
        6 - Affirmed and reversed (or vacated) in part
        7 - Affirmed and reversed (or vacated) in part and remanded
        8 - Vacated
        9 - Petition denied or appeal dismissed
        10 - Certification to a lower court
        11 - No disposition
        12 - Affirmed and remanded

    Legal Area Codes:
    - "LegalArea": Lexis-Nexis issue area classification found from the first classification under "headnotes" (string, e.g., "Constitutional Law").
    - "LegalAreaCode": Numeric code for the issue area (integer). Use the following codes:
        1 - Administrative Law
        2 - Admiralty Law
        3 - Antitrust and Trade Law
        4 - Banking Law
        5 - Bankruptcy Law
        6 - Business and Corporate Law
        7 - Civil Procedure
        8 - Civil Rights Law
        9 - Commercial Law (UCC)
        10 - Communications Law
        11 - Computer and Internet Law
        12 - Constitutional Law
        13 - Contracts Law
        14 - Copyright Law
        15 - Criminal Law and Procedure
        16 - Education Law
        17 - Energy and Utilities Law
        18 - Environmental Law
        19 - Estates
        20 - Evidence
        21 - Family Law
        22 - Governments
        23 - Healthcare Law
        24 - Immigration Law
        25 - Insurance Law
        26 - International Law
        27 - International Trade Law
        28 - Labor and Employment Law
        29 - Legal Ethics
        30 - Mergers and Acquisitions Law
        31 - Military and Veterans Law
        32 - Patent Law
        33 - Pensions and Benefits Law
        34 - Public Contracts Law
        35 - Public Health and Welfare Law
        36 - Real Property Law
        37 - Securities Law
        38 - Tax Law
        39 - Torts
        40 - Trade Secrets Law
        41 - Trademark Law
        42 - Transportation Law
        43 - Workers’ Compensation and SSDI

    Court Decision Codes:
    - "appellant": Name of the party bringing the appeal (string).
    - "appellee": Name of the opposing party in the appeal (string).
    - "court_decision": Integer indicating whether the decision favors the appellant (1), appellee (2), or is mixed/unknown (3).
    - "outcome_text": Main outcome statement of the case (string).
    
    Majority and Dissent Authors:
    - For *per curiam* opinions, consider all listed justices as majority opinion authors unless otherwise specified.

    Judge Votes and Codes:
    - "J1_Vote": Vote of Judge 1 (integer). Use the following codes:
        0 - Minority Vote
        1 - Majority Vote
        2 - Recused
        3 - Not Participating
    - "J1_Name": Last name of Judge 1 (string, without titles).
    - "J1_Code": Identification code for Judge 1 (integer).
    - "J1_VoteAdjusted": Indicates if Judge 1 voted for the appellant (1), appellee (2), or other/mixed (3).
    - Continue similarly for "J2_Vote", "J2_Name", "J2_Code", "J2_VoteAdjusted", up to "J11_Name".

    Majority vs. Minority Breakdown:
    - "majority_vs_minority": Provide the vote split as "5-4" (or similar) indicating the number of justices in majority and minority.

    Text:
    {text}

    Please return these variables exactly as specified in JSON format.
    """
    
    response = openai.Completion.create(
        model="gpt-4",
        prompt=prompt,
        max_tokens=1000
    )
    return response.choices[0].text.strip()

def process_rtf_file_with_api(file_path):
    """Processes a single RTF file by extracting text and sending it to the API for variable extraction."""
    text = extract_text_from_rtf(file_path)
    extracted_data = extract_variables_via_api(text)
    
    # Parse JSON from response text
    extracted_dict = json.loads(extracted_data)
    
    return extracted_dict
def process_state_folder(state_folder_path, state_code):
    """Processes all RTF files in a state folder and writes the extracted data to a state-specific CSV file."""
    results = []
    rtf_files = [f for f in os.listdir(state_folder_path) if f.lower().endswith('.rtf')]
    print(f"Processing state folder for {state_code}: Found {len(rtf_files)} RTF files.")

    for filename in rtf_files:
        file_path = os.path.join(state_folder_path, filename)
        try:
            result = process_rtf_file_with_api(file_path)
            results.append(result)
            print(f"Successfully processed file: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

        # Write results to a state-specific CSV file
    if results:
        state_output_file = f"output_{state_code}.csv"
        keys = results[0].keys()
        with open(state_output_file, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print(f"Results for {state_code} saved to {state_output_file}")
    
    return results  # Return results to also add to the combined CSV
def process_all_states(base_folder):
    """Processes each state folder and creates both individual state CSVs and a combined CSV for all states."""
    combined_results = []
    
    for state_code in os.listdir(base_folder):
        state_folder_path = os.path.join(base_folder, state_code)
        if os.path.isdir(state_folder_path) and len(state_code) == 2:  # Ensure it's a two-letter state folder
            print(f"Starting processing for state: {state_code}")
            state_results = process_state_folder(state_folder_path, state_code)
            combined_results.extend(state_results)  # Add state results to the combined list

    # Write combined results to a single CSV file
    if combined_results:
        combined_output_file = "combined_output_all_states.csv"
        keys = combined_results[0].keys()
        with open(combined_output_file, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(combined_results)
        print(f"Combined results saved to {combined_output_file}")
    else:
        print("No data was processed for the combined CSV.")

if __name__ == "__main__":
    base_folder = '/path/to/States'  # Replace with the path to your "States" folder
    process_all_states(base_folder)
