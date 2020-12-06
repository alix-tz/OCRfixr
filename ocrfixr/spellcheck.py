"""Main module."""
import re
import string
from pandas import DataFrame
from nltk.tokenize import WhitespaceTokenizer
from transformers import pipeline
from spellchecker import SpellChecker


spell = SpellChecker()
#spell_cs = SpellChecker(case_sensitive = True)
# Set BERT to look for the 15 most likely words in position of the misspelled word
unmasker = pipeline('fill-mask', model='bert-base-uncased', topk=15)


class spellcheck:                       
    def __init__(self, text, return_fixes = "F"):
        self.text = text
        self.return_fixes = return_fixes
        
### DEFINE ALL HELPER FUNCTIONS
# ------------------------------------------------------
# Find all mispelled words in a passage.
 

    def _LIST_MISREADS(self):
        tokens = WhitespaceTokenizer().tokenize(self.text)
        # First, drop hyphenated words, and those broken across lines
        regex = re.compile('.*-.*')
        no_hyphens = [x for x in tokens if not regex.match(x)]
        # Also, drop all items with leading caps (ie. proper nouns)
        regex = re.compile('[^A-Z][a-z0-9]{1,}')
        no_caps = [x for x in no_hyphens if regex.match(x)]
        # then, remove punct from each remaining token (such as trailing commas, periods, quotations ('' & ""), but KEEPING contractions). 
        no_punctuation = [l.strip(string.punctuation) for l in no_caps]
        #no_punctuation = [l.translate(str.maketrans('', '', string.punctuation)) for l in no_caps]
        okay_items = no_punctuation
        # test1 for tokenizer: "'I'm not sure', Adam said. 'I can't see it. The wind-n\ow is half-shut.'" --- should result in no spell.unknowns << CORRECT >>
        # test2 for tokenizer: "Hello, I'm a maile model." --- should result in "maile" being flagged. << CORRECT >>
        misread = spell.unknown(okay_items)
        return(misread)
    # NEED TO: remove "3-in-a-rows" --- these help limit issues where inserts of text in foreign language is present, esp in footnotes
    # TODO - prevent spell.unknown from automatically lowercasing all misspellings (ex: streDgthener), as this prevents the find-replace from working
    
    
    # Return the list of possible spell-check options. These will be used to look for matches against BERT context suggestions
    def __SUGGEST_SPELLCHECK(self, text):
        pyspell_suggest = spell.candidates(text)
        suggested_words = list(pyspell_suggest)
        return(suggested_words)
    
    
    # Suggest a set of the 15 words that best fit given the context of the misread
    def __SUGGEST_BERT(self, text):
        context_suggest = unmasker(text)
        suggested_words = DataFrame(context_suggest).token_str
        return(suggested_words)
    
    
    # Ensure that list items are correctly converted down without the [] 
    def __LIST_TO_STR(self, LIST):
        listToStr = ' '.join(map(str, LIST)) 
        return(listToStr)
    
        
    # Create [MASK] objects for each misspelling in the sentence. If the same word is misspelled multiple times, only [MASK] the first one.
    def __SET_MASK(self, orig_word, replacement, orig_text):
        updated_text = re.sub(str(orig_word), str(replacement), orig_text, count = 1, flags=re.IGNORECASE)
        return(updated_text)
            
    
    # note that multi-replace will replace ALL instances of a mispell, not just the first one (ie. spell-check is NOT instance-specific to each mispell, it is misspell-specific). Therefore, it should be run sentence-by-sentence to limit potential issues.
    def _MULTI_REPLACE(self, fixes):
        # if there are no fixes, just return the original text
        if len(fixes) == 0 :
            return(self.text)
        else:
        # otherwise, replace all dict entries with the approved replacement word
            fixes = dict((re.escape(k), v) for k, v in fixes.items()) 
            pattern = re.compile("|".join(fixes.keys()))
            text_corrected = pattern.sub(lambda m: fixes[re.escape(m.group(0))], self.text)
            return(text_corrected)
    
    
    # Creates a dict of valid replacements for misspellings. If bert and pyspellcheck do not have a match for a given misspelling, it makes no changes to the word.
    def _FIND_REPLACEMENTS(self, misreads, get = "fixes"):
        SC = [] 
        mask = []
        # for each misread, get all spellcheck suggestions from pyspellcheck
        for i in misreads:
            SC.append(self.__SUGGEST_SPELLCHECK(i))
            mask.append(self.__SET_MASK(i,'[MASK]', self.text))
            # for each misread, get all context suggestions from bert
        bert = []
        for b in mask:
            bert.append(self.__SUGGEST_BERT(b))
    
            # then, see if spellcheck & bert overlap
            # if they do, set that value for the find-replace dict
            # if they do not, then keep the original misspelling in the find-replace dict (ie. make no changes to that word)
            
        corr = []
        fixes = []
        x = 0
        while x < len(bert):
            overlap = set(bert[x]) & set(SC[x])
            corr.append(overlap)
            # if there is a single word that is both in context and pyspellcheck - update with that word
            if len(overlap) == 1:
                corr[x] = self.__LIST_TO_STR(corr[x])
            # if no overlapping candidates OR > 1 candidate, keep misread as is
            else:
                corr[x] = ""
            x = x+1
    
        fixes = dict(zip(misreads, corr))
        # Remove all dict entries with "" values (ie. no suggested change)
        for key in list(fixes.keys()):
            if fixes[key] == "":
                del fixes[key]
                
        return(fixes)
    
    
    
    # Final OCR contextual spellchecker
    def replace(self):
        misreads = self._LIST_MISREADS()
        
        # if no misreads, just return the original text
        if len(misreads) == 0:
            return(self.text)
        
        # otherwise, look for candidates for replacement and 
        # Based on user input, either outputs the full corrected text, or simply list the misreads + their fixes (if found)
        else:
            fixes = self._FIND_REPLACEMENTS(misreads)
            if self.return_fixes == "T":
                return(fixes)
            else:
                correction = self._MULTI_REPLACE(fixes)
                return(correction)





#text = "See if you can find the rnistakes 1n this sentence on your first try."
#text = "I am sure yov will f1nd all the rnistakes in this sentence. Also, I have a rpiestion for yov..."

#fix = ocrfixr.spellcheck(text).replace()
#print(fix)


# TODO - check for mashed up words ("anhour" --> "an hour") BEFORE concluding they are misspells -- BERT/Spellcheck really can't handle these well    
# TODO - add sentence tokenization at front end of this function, so that each sentence is evaluated separately (since find-replace is not instance-specific, it is misspell specific..."yov" will be replaced with "you" in all instances found in the text otherwise. Sentence tokenization allows for this decision to be made on a per-instance basis...roughly :) )  
# Note: OCRfixr ignores all words with leading uppercasing, as these are assumed to be proper nouns, which fall outside of the scope of what this approach can accomplish.

       
