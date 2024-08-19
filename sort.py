import json
import re
import cProfile

# Load the list of words from the JSON file
with open('DirtyWords.json', 'r', encoding='utf-8') as file:
    data = json.load(file)
    dirty_words = {record['word'].lower() for record in data['RECORDS']}

def preprocess_text(text):
    """
    Preprocess the text by removing punctuation and converting to lowercase.
    This ensures that we only deal with words, not special characters.
    """
    return re.findall(r'\b\w+\b', text.lower())

def contains_dirty_words(text):
    """
    Check if the input text contains any words from the dirty words list.
    
    :param text: The text to check.
    :param dirty_words: A set of words considered inappropriate.
    :return: A list of found inappropriate words, if any.
    """
    words_in_text = set(preprocess_text(text))
    found_words = words_in_text.intersection(dirty_words)
    return found_words


