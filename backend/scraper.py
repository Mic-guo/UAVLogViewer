import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, List, Set
from collections import defaultdict

def scrape_log_messages() -> tuple[Dict, Dict[str, List[str]]]:
    """
    Scrape log messages from ArduPilot documentation.
    Returns a tuple of:
    1. Dictionary of message definitions
    2. Dictionary mapping field names to message types that contain them
    """
    url = "https://ardupilot.org/plane/docs/logmessages.html"
    
    # Fetch the webpage with proper encoding
    response = requests.get(url)
    response.encoding = 'utf-8'
    response.raise_for_status()
    
    # Parse HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Dictionary to store message definitions
    message_definitions = {}
    
    # Dictionary to store reverse lookup (field name -> message types)
    field_to_messages = defaultdict(list)
    
    # Find the main section containing all log messages
    main_section = soup.find('section', id='onboard-message-log-messages')
    if not main_section:
        raise Exception("Could not find the main log messages section")
    
    # Find all subsections within the main section
    sections = main_section.find_all('section')
    
    for section in sections:
        section_id = section.get('id')
        if not section_id:
            continue
            
        # Get section title (h2)
        title = section.find('h2')
        if not title:
            continue
            
        # Get description (first p after h2)
        description = title.find_next('p')
        description_text = description.text if description else ""
        
        # Find the table
        table = section.find('table')
        if not table:
            continue
            
        # Get all rows from tbody
        tbody = table.find('tbody')
        if not tbody:
            continue
            
        rows = tbody.find_all('tr')
        
        # Dictionary to store fields for this message type
        fields = {}
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                # Clean and decode special characters
                field_name = cells[0].get_text(strip=True).lower()
                unit = cells[1].get_text(strip=True)
                field_description = cells[2].get_text(strip=True)
                
                # Add to fields dictionary
                fields[field_name] = {
                    "unit": unit,
                    "description": field_description
                }
                
                # Add to reverse lookup
                field_to_messages[field_name].append(section_id)
        
        # Store message type data
        message_definitions[section_id] = {
            "description": description_text,
            "fields": fields
        }
    
    # Convert defaultdict to regular dict for JSON serialization
    field_to_messages = dict(field_to_messages)
    
    return message_definitions, field_to_messages

def save_to_json(data: Dict, filename: str):
    """Save the scraped data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    try:
        # Scrape the data
        message_definitions, field_to_messages = scrape_log_messages()
        
        # Save message definitions
        save_to_json(message_definitions, 'message_definitions.json')
        
        # Save reverse lookup table
        save_to_json(field_to_messages, 'field_to_messages.json')
        
        print(f"Successfully scraped {len(message_definitions)} message types")
        print(f"Found {len(field_to_messages)} unique fields")
        
        # Print first message type to verify
        if message_definitions:
            first_type = next(iter(message_definitions))
            print(f"\nFirst message type: {first_type}")
            print(f"Description: {message_definitions[first_type]['description']}")
            print(f"Number of fields: {len(message_definitions[first_type]['fields'])}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
