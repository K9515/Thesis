# Function to extract text from the PDF
import os
import csv
from striprtf.striprtf import rtf_to_text
import re
from datetime import datetime


def extract_text_from_rtf(rtf_path):

    with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as file:
        rtf_content = file.read()
    text = rtf_to_text(rtf_content)
    return text

def extract_case_name(text):
    patterns = [
        r'\d+\.\s*(.*?)\s*v\.\s*(.*?),',
        r'(.*?)\s+v\.\s+(.*?),',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            return f"{match.group(1).strip()} v. {match.group(2).strip()}"
    return ''
def extract_case_citation(text):
    patterns = [
        r'\d+\.\s*.*?\s*v\.\s*.*?,\s*(.*?)(?=\s*\n)',
        r'.*?\s+v\.\s+.*?,\s*(.*?)(?=\s*\n)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ''
def extract_parties(text):
    # Updated regex to avoid capturing "v." or "vs."
    patterns = [
        r'(.*?),\s*Appellant(?:/Cross-Appellee)?,\s*(?:v\.?|vs\.?)\s*(.*?),\s*Appellee(?:/Cross-Appellant)?',
        r'(.*?)\s*(?:v\.?|vs\.?)\s*(.*?),\s*(?:Appellant|Appellee)',
        r'(?:Ex parte\s+)?(.*?);\s*\(In re:?\s*(.*?)\s*v\.?\s*(.*?)\)',
        r'(.*?)\s*(?:v\.?|vs\.?)\s*(.*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                appellant, appellee = groups
            elif len(groups) == 3:
                # Handle the "Ex parte" case
                if 'ex parte' in groups[0].lower():
                    appellant = groups[2]
                    appellee = groups[0]
                else:
                    appellant = groups[1]
                    appellee = groups[2]
            
            # Clean up the parties by stripping whitespace and punctuation
            appellant = appellant.strip().rstrip(',').replace('v.', '').replace('vs.', '').strip()
            appellee = appellee.strip().rstrip(',').replace('v.', '').replace('vs.', '').strip()

            # Handle "State of" cases
            if appellant.lower().startswith('state'):
                appellant = 'State of ' + appellant.split()[-1]
            if appellee.lower().startswith('state'):
                appellee = 'State of ' + appellee.split()[-1]

            return appellant, appellee

    return None, None

def extract_decision_date(text):
    date_patterns = [
        r'(\w+ \d{1,2}, \d{4}),? (?:Heard|Filed|Released|Decided)',
        r'(?:Heard|Filed|Released|Decided) (\w+ \d{1,2}, \d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%B %d, %Y').date()
            except ValueError:
                pass  # If parsing fails, try the next pattern
    
    return None 
def extract_prior_history(text):
    match = re.search(r'Prior History\s*([\s\S]+?)\n\n', text)
    if match:
        return match.group(1).strip()
    else:
        return ''
def extract_area_of_law(text):
    # Modified regex to capture the area of law after "Headnotes" and before the first '>'
    match = re.search(r'Headnotes\s*(.*?)(\s*>|\n)', text)
    if match:
        return match.group(1).strip()  # Return the area of law found before the first '>'
    else:
        return '' 
disposition_mapping = {
    'Stay, petition, or motion granted': 1,
    'Affirmed': 2,
    'Reversed': 3,
    'Reversed and remanded': 4,
    'Vacated and remanded': 5,
    'Affirmed and reversed in part': 6,
    'Affirmed and vacated in part': 7,
    'Affirmed and reversed in part and remanded': 8,
    'Affirmed and vacated in part and remanded': 9,
    'Vacated': 10,
    'Petition denied or appeal dismissed': 11,
    'Certification to a lower court': 12,
    'No disposition': 13,
    'Affirmed and remanded': 14
}
def extract_disposition(text, disposition_mapping):
    outcome_match = re.search(r'outcome\s*\n\s*(.*?)\s*(?:\n|$)', text, re.IGNORECASE | re.DOTALL)
    outcome_text = outcome_match.group(1) if outcome_match else ''
    
    print(f"Debug: Extracted outcome text: {outcome_text}")  # Debug print

    disposition_phrases = [
        (r'affirmed\s+in\s+part,\s+reversed\s+in\s+part,\s+and\s+remanded', 8),
        (r'affirmed\s+and\s+reversed\s+in\s+part\s+and\s+remanded', 8),
        (r'affirmed\s+and\s+vacated\s+in\s+part\s+and\s+remanded', 9),
        (r'affirmed\s+and\s+reversed\s+in\s+part(?!\s+and\s+remanded)', 6),
        (r'affirmed\s+and\s+vacated\s+in\s+part(?!\s+and\s+remanded)', 7),
        (r'reversed\s+and\s+remanded', 4),
        (r'vacated\s+and\s+remanded', 5),
        (r'reversed(?!\s+and)', 3),
        (r'vacated(?!\s+and)', 10),
        (r'affirmed\s+and\s+remanded', 14),
        (r'affirmed', 2),
        (r'stay.*?granted|petition.*?granted|motion.*?granted', 1),
        (r'petition\s+denied|appeal\s+dismissed', 11),
        (r'certification\s+to\s+a\s+lower\s+court', 12),
    ]

    disposition_code = 13  # Default to "No disposition"
    for pattern, code in disposition_phrases:
        if re.search(pattern, outcome_text, re.IGNORECASE):
            disposition_code = code
            break
    
    print(f"Debug: Mapped disposition code: {disposition_code}") 
    # Determine court decision
    if disposition_code in [1, 3, 4, 5]:
        court_decision = 2  # Appellant
    elif disposition_code in [2, 11, 14]:
        court_decision = 1  # Appellee
    elif disposition_code in [6, 7, 8, 9, 10, 12]:
        court_decision = 3  # Mixed/Unknown
    else:
        court_decision = 0  # Unable to determi


    return disposition_code, court_decision, outcome_text

def extract_opinion_concur_dissent_authors(text):
    opinion_author = ''
    concurring_authors = []
    dissent_authors = []

    # Look for the opinion author or PER CURIAM
    opinion_match = re.search(r'Opinion by:?\s*([A-Z]+(?:\s+[A-Z]+)*)', text, re.IGNORECASE)
    if opinion_match:
        opinion_author = opinion_match.group(1).strip()
    elif 'PER CURIAM' in text.upper():
        opinion_author = 'PER CURIAM'

    # Look for "authored the opinion" pattern
    authored_match = re.search(r'([A-Z]+(?:\s+[A-Z]+)*)\s+authored the opinion', text)
    if authored_match:
        opinion_author = authored_match.group(1).strip()

    # Improved regex for Concur by and Dissent by sections
    concur_section = re.findall(r'Concur by:?\s*([A-Z]+(?:\s+[A-Z]+)*)', text, re.IGNORECASE)
    dissent_section = re.findall(r'Dissent by:?\s*([A-Z]+(?:\s+[A-Z]+)*)', text, re.IGNORECASE)

    # Remove any extra spaces, line breaks, or repeated names
    concurring_authors = list(set([author.strip() for author in concur_section if author.strip()]))
    dissent_authors = list(set([author.strip() for author in dissent_section if author.strip()]))

    # Clean up extra new lines or duplicate entries
    concurring_authors = [re.sub(r'\n.*', '', author) for author in concurring_authors]
    dissent_authors = [re.sub(r'\n.*', '', author) for author in dissent_authors]

    # If no explicit opinion author is found, set it to PER CURIAM
    if not opinion_author and not concurring_authors and not dissent_authors:
        opinion_author = 'PER CURIAM'

    return opinion_author, concurring_authors, dissent_authors

# Define the vote mapping
vote_mapping = {
    'Dissent': 1,
    'Concur': 2,
    'Concur in part and Dissent in part': 3,
    'Recuse': 4,
    'Did not participate': 5
}

def extract_justices(text):
    # Look for the "Judges:" section
    judges_section = re.search(r'Judges:(.*?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
    
    if judges_section:
        judges_text = judges_section.group(1)
        
        # Enhanced pattern to match judge names, including more prefixes and suffixes
        judge_pattern = r'(?:(?:VICE\s+)?(?:CHIEF|ASSOCIATE CHIEF)?\s*JUSTICE\s+)?([A-Z]+(?:[-\s][A-ZÑ]+)*|[A-ZÑ]+)(?:,?\s*(?:C\.J\.|J\.))?,?'
        
        # Find all matches
        matches = re.findall(judge_pattern, judges_text)
        
        # Clean up the names, remove duplicates, and filter out unwanted matches
        justices = []
        for name in matches:
            cleaned_name = re.sub(r'\s+', '', name)  # Remove any spaces within names
            cleaned_name = re.sub(r'^(?:VICE)?(?:CHIEF)?(?:ASSOCIATE)?JUSTICE', '', cleaned_name)  # Remove prefixes
            if len(cleaned_name) > 1 and cleaned_name not in justices and cleaned_name != 'JJ':
                justices.append(cleaned_name)
        
        # Combine split names (like MU and ÑIZ)
        combined_justices = []
        skip_next = False
        for i, justice in enumerate(justices):
            if skip_next:
                skip_next = False
                continue
            if i < len(justices) - 1 and len(justice) <= 2 and len(justices[i+1]) <= 3:
                combined_justices.append(justice + justices[i+1])
                skip_next = True
            else:
                combined_justices.append(justice)
        
        # Handle the opinion author separately
        author_match = re.search(r'(?:CHIEF\s+)?JUSTICE\s+(\w+)\s+(\w+)\s+authored', judges_text)
        if author_match:
            author_last_name = author_match.group(2)
            if author_last_name in combined_justices:
                combined_justices.remove(author_last_name)
            combined_justices.insert(0, author_last_name)
        
        return combined_justices
    
    return []
#   def extract_justices(text):
    # Look for the "Judges:" section
    judges_section = re.search(r'Judges:(.*?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
    
    if judges_section:
        judges_text = judges_section.group(1)
        
        judge_pattern = r'(?:(?:CHIEF|ASSOCIATE CHIEF)?\s*JUSTICE\s+)?([A-Z]+(?:[-\s][A-ZÑ]+)*|[A-ZÑ]+)(?:,?\s*(?:C\.J\.|J\.))?,?'
        
        # Find all matches
        matches = re.findall(judge_pattern, judges_text)
        
        # Clean up the names, remove duplicates, and filter out unwanted matches
        justices = []
        for name in matches:
            cleaned_name = re.sub(r'\s+', '', name)  # Remove any spaces within names
            if len(cleaned_name) > 1 and cleaned_name not in justices and cleaned_name != 'JJ':
                justices.append(cleaned_name)
        
        # Combine split names (like MU and ÑIZ)
        combined_justices = []
        skip_next = False
        for i, justice in enumerate(justices):
            if skip_next:
                skip_next = False
                continue
            if i < len(justices) - 1 and len(justice) <= 2 and len(justices[i+1]) <= 3:  # Changed from 2 to 3
                combined_justices.append(justice + justices[i+1])
                skip_next = True
            else:
                combined_justices.append(justice)
        
        return combined_justices
    
    return []


def extract_votes_original(text):
    votes = []
    
    # Extract justices list from the text
    justices_list = extract_justices(text)

    if not justices_list:
        return ''  # Return an empty string if no justices are found

    # Match for the "Judges:" section
    judges_section = re.search(r'Judges:(.*?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
    if judges_section:
        judges_text = judges_section.group(1)
        print(f"Debug - Judges section: {judges_text}")  # Debug print
        
        for justice in justices_list:
            if re.search(rf'{justice},\s*J\.,\s*dissents', judges_text, re.IGNORECASE):
                votes.append(f"{justice}, 1")  # 1 for Dissent
                print(f"Debug - {justice} dissents")  # Debug print
            elif re.search(rf'{justice},\s*J\.,\s*concurs\s+in\s+part\s+and\s+dissents\s+in\s+part', judges_text, re.IGNORECASE):
                votes.append(f"{justice}, 3")  # 3 for Concur in part and Dissent in part
                print(f"Debug - {justice} concurs in part and dissents in part")  # Debug print
            elif re.search(rf'{justice},\s*J\.,\s*recused', judges_text, re.IGNORECASE):
                votes.append(f"{justice}, 4")  # 4 for Recuse
                print(f"Debug - {justice} recused")  # Debug print
            elif re.search(rf'{justice},\s*J\.,\s*did\s+not\s+participate', judges_text, re.IGNORECASE):
                votes.append(f"{justice}, 5")  # 5 for Did not participate
                print(f"Debug - {justice} did not participate")  # Debug print
            elif re.search(rf'{justice}.*?concurs', judges_text, re.IGNORECASE):
                votes.append(f"{justice}, 2")  # 2 for Concur
                print(f"Debug - {justice} concurs")  # Debug print
            else:
                votes.append(f"{justice}, 2")  # Assume concurrence if not specified
                print(f"Debug - {justice} assumed to concur")  # Debug print

    return '; '.join(votes)

def extract_votes_appellant_appellee(text, court_decision, votes_original):
    votes = []
    justices_list = extract_justices(text)

    if not justices_list or not votes_original:
        return ''

    # Parse the votes_original string
    original_votes = dict(vote.strip().split(', ') for vote in votes_original.split(';'))

    # If court_decision is 3 (mixed), all votes should be 3
    if court_decision == 3:
        return '; '.join(f"{justice}, 3" for justice in original_votes.keys())

    majority_vote = 2 if court_decision == 2 else 1  # 2 for Appellee, 1 for Appellant

    for justice, vote in original_votes.items():
        vote = int(vote)
        if vote == 1:  # Dissent
            votes.append(f"{justice}, {3 - majority_vote}")  # Opposite of majority
        elif vote == 2:  # Concur
            votes.append(f"{justice}, {majority_vote}")
        elif vote == 3:  # Concur in part and Dissent in part
            votes.append(f"{justice}, 3")
        elif vote == 4:  # Recuse
            votes.append(f"{justice}, 4")
        elif vote == 5:  # Did not participate
            votes.append(f"{justice}, 5")
        else:
            votes.append(f"{justice}, {majority_vote}")  # Default to majority

    return '; '.join(votes)
#def extract_justice_info(text, court_decision):
    #justices_info = []
    #justices_list = extract_justices(text)
    
    #if not justices_list:
        #return []

    #majority_vote = 2 if court_decision == 1 else 1  # 2 for Appellee, 1 for Appellant

    # Find the majority opinion author
    #match_majority = re.search(r'(?:JUSTICE|CHIEF JUSTICE)\s+(\w+)\s+authored the opinion of the Court, in which\s+(.*?)(?:joined|\.)', text)
    
    #if match_majority:
        #majority_author = match_majority.group(1)
        #joined_justices = [justice.strip().split()[-1] for justice in match_majority.group(2).split(',') if justice.strip()]
        
        # Add majority author
        #justices_info.append({
            #'name': majority_author,
            #'vote': majority_vote,
            #'opinion': 1  # Writer of majority opinion
        #})
        
        # Add justices who joined the majority
        #for justice in joined_justices:
            #justices_info.append({
                #'name': justice,
                #'vote': majority_vote,
                #'opinion': 2  # Joins majority opinion without writing
            #})
    
    # Find concurring and dissenting opinions
    match_concur_dissent = re.findall(r'(?:JUSTICE|CHIEF JUSTICE)\s+(\w+),\s+(concurring|dissenting|concurring in part and dissenting in part)(?:\s+\(([^)]+)\))?', text, re.IGNORECASE)
    
    for justice, opinion_type, joined in match_concur_dissent:
        opinion_type = opinion_type.lower()
        if 'concurring in part and dissenting in part' in opinion_type:
            vote = 3  # Mixed
            opinion = 9  # Concurs in part/dissents in part
        elif 'dissenting' in opinion_type:
            vote = 1 if majority_vote == 2 else 2
            opinion = 6 if not joined else 7  # Writer of dissenting opinion or Joins dissenting opinion
        elif 'concurring' in opinion_type:
            vote = majority_vote
            opinion = 3 if not joined else 4  # Writer of concurring opinion or Joins concurring opinion
        
        justices_info.append({
            'name': justice,
            'vote': vote,
            'opinion': opinion
        })
    
    # Add any remaining justices as joining the majority
    for justice in justices_list:
        if not any(info['name'] == justice for info in justices_info):
            justices_info.append({
                'name': justice,
                'vote': majority_vote,
                'opinion': 2  # Joins majority opinion without writing
            })
    
    return justices_info[:9]  # Limit to maximum 9 justices
def extract_justice_info(text, court_decision, votes_original, votes_appellant_appellee):
    justices_info = []
    justices_list = extract_justices(text)
    
    if not justices_list:
        return []

    # Parse the votes
    original_votes = dict(vote.strip().split(', ') for vote in votes_original.split(';'))
    appellant_appellee_votes = dict(vote.strip().split(', ') for vote in votes_appellant_appellee.split(';'))

    majority_vote = 2 if court_decision == 1 else 1  # 2 for Appellee, 1 for Appellant

    # Check for per curiam opinion
    if re.search(r'\bPER CURIAM\b', text, re.IGNORECASE):
        for justice in justices_list:
            justices_info.append({
                'name': justice,
                'vote': int(appellant_appellee_votes.get(justice, str(majority_vote))),
                'opinion': 5  # Per curiam opinion
            })
        return justices_info[:9]  # Return early for per curiam opinions

    # Find the majority opinion author
    match_majority = re.search(r'(?:JUSTICE|CHIEF JUSTICE)\s+(\w+)\s+authored the opinion of the Court, in which\s+(.*?)(?:joined|\.)', text)
    
    if match_majority:
        majority_author = match_majority.group(1)
        joined_justices = [justice.strip().split()[-1] for justice in match_majority.group(2).split(',') if justice.strip()]
        
        # Add majority author
        justices_info.append({
            'name': majority_author,
            'vote': int(appellant_appellee_votes.get(majority_author, str(majority_vote))),
            'opinion': 1  # Writer of majority opinion
        })
        
        # Add justices who joined the majority
        for justice in joined_justices:
            justices_info.append({
                'name': justice,
                'vote': int(appellant_appellee_votes.get(justice, str(majority_vote))),
                'opinion': 2  # Joins majority opinion without writing
            })
    
    # Find concurring and dissenting opinions
    match_concur_dissent = re.findall(r'(?:JUSTICE|CHIEF JUSTICE)\s+(\w+),\s+(concurring|dissenting|concurring in part and dissenting in part)(?:\s+\(([^)]+)\))?', text, re.IGNORECASE)
    
    for justice, opinion_type, joined in match_concur_dissent:
        opinion_type = opinion_type.lower()
        vote = int(appellant_appellee_votes.get(justice, '3'))  # Default to 3 if not found
        
        if 'concurring in part and dissenting in part' in opinion_type:
            opinion = 9  # Concurs in part/dissents in part
        elif 'dissenting' in opinion_type:
            opinion = 6 if not joined else 7  # Writer of dissenting opinion or Joins dissenting opinion
        elif 'concurring' in opinion_type:
            opinion = 3 if not joined else 4  # Writer of concurring opinion or Joins concurring opinion
        
        justices_info.append({
            'name': justice,
            'vote': vote,
            'opinion': opinion
        })
    
    # Add any remaining justices as joining the majority
    for justice in justices_list:
        if not any(info['name'] == justice for info in justices_info):
            justices_info.append({
                'name': justice,
                'vote': int(appellant_appellee_votes.get(justice, str(majority_vote))),
                'opinion': 2  # Joins majority opinion without writing
            })
    
    return justices_info[:9]  # Limit to maximum 9 justices # Limit to maximum 9 justices

def process_rtf_file(file_path):
    text = extract_text_from_rtf(file_path)
    
    case_name = extract_case_name(text)
    case_citation = extract_case_citation(text)
    appellant, appellee = extract_parties(text)
    decision_date = extract_decision_date(text)
    disposition_code, court_decision, outcome_text = extract_disposition(text, disposition_mapping)
    opinion_author, concurring_authors, dissent_authors = extract_opinion_concur_dissent_authors(text)
    justices = extract_justices(text)
    votes_original = extract_votes_original(text)
    votes_appellant_appellee = extract_votes_appellant_appellee(text, court_decision, votes_original)
    justice_info = extract_justice_info(text, court_decision, votes_original, votes_appellant_appellee)
    
    justice_data = {}
    for i in range(1, 10):
        if i <= len(justice_info):
            justice_data[f"j{i}_name"] = ''  # Placeholder for cross-referencing
            justice_data[f"j{i}_vote"] = justice_info[i-1]['vote']
            justice_data[f"j{i}_opin"] = justice_info[i-1]['opinion']
        else:
            justice_data[f"j{i}_name"] = ''
            justice_data[f"j{i}_vote"] = 88  # Not relevant
            justice_data[f"j{i}_opin"] = 88
    
    law_area = extract_area_of_law(text)
    prior_history = extract_prior_history(text)
    
    return {
        'case_name': case_name,
        'case_citation': case_citation,
        'appellant': appellant,
        'appellee': appellee,
        'decision_date': decision_date,
        'disposition_code': disposition_code,
        'court_decision': court_decision,
        'outcome_text': outcome_text,
        'opinion_author': opinion_author,
        'concurring_authors': concurring_authors,
        'dissent_authors': dissent_authors,
        'justices': justices,
        'votes_original': votes_original,
        'votes_appellant_appellee': votes_appellant_appellee,
        **justice_data,
        'law_area': law_area,
        'prior_history': prior_history
    }
def process_rtf_folder(folder_path, output_csv):
    results = []
    rtf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.rtf')]
    print(f"Found {len(rtf_files)} RTF files.")
    print(f"Starting to process {len(rtf_files)} RTF files...")
    
    for filename in rtf_files:
        file_path = os.path.join(folder_path, filename)
        print(f"Processing file: {filename}")
        try:
            result = process_rtf_file(file_path)
            results.append(result)
            print(f"Successfully processed: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    print(f"Finished processing. Successfully processed {len(results)} out of {len(rtf_files)} files.")

    if results:
        keys = results[0].keys()
        with open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print(f"Results saved to {output_csv}")
    else:
        print("No RTF files were successfully processed.")


if __name__ == "__main__":
    folder_path = '/Users/katedegroote/Thesis/States/AZ'
    output_csv = 'output_results.csv'
    
    print(f"Checking folder: {folder_path}")
    
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
    else:
        print("Folder exists. Checking for RTF files...")
        rtf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.rtf')]
        print(f"Found {len(rtf_files)} RTF files.")
        
        if rtf_files:
            process_rtf_folder(folder_path, output_csv)
        else:
            print("No RTF files were found in the specified folder.")

        print("First 5 RTF files found:")
        for file in rtf_files[:5]:
            print(file)

