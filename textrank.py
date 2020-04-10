import itertools
import networkx as nx
import nltk
import os
import numpy as np


def setup_environment():
    """Download required resources."""
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    print('Completed resource downloads.')

def filter_for_tags(tagged, tags=['NN', 'NNS', 'JJ', 'NNP', 'NNPS']):
    """
    Apply syntactic filters based on POS tags.
    https://pythonprogramming.net/natural-language-toolkit-nltk-part-speech-tagging/
    """
    return [item[0] for item in tagged if item[1] in tags]

def sort_top(scores, ratio=0.33):
    """
    Get items with highest score
    args:
        ratio: float (0,1], fraction of items to choose
    returns:
        list of items
    """
    results = sorted(scores, key=scores.get,reverse=True)
    return results[:int(ratio * len(results))]

def get_word_list(sentence, skipwords=[], plural_to_singular={}):
    """
    Tokenizes string and converts words from plural to singular
    args:
        sentence: string
        skipwords: words to skip
        plural_to_singular: dict of (plural, singular) items
    returns:
        list of words
    """
    word_tokens = []
    for w in nltk.word_tokenize(sentence):
        if len(w) > 1 and w not in skipwords:
            if w in plural_to_singular.keys():
                word_tokens.append(plural_to_singular[w])
            else:
                word_tokens.append(w)
    tagged = nltk.pos_tag(word_tokens)
    word_list = filter_for_tags(tagged)
    return word_list

def build_graph(sentences, skipwords=[], plural_to_singular={}, compound_words=[]):
    """
    args: 
        sentences: list of strings
        skipwords: words to skip
        plural_to_singular: dict of (plural, singular) items
        compound_words: list of tuples to replace consecutive words if found
    returns: 
        directed weighted graph
    """
    unique_word_set = set([])
    edges = {}
    max_compound_len = max([len(x) for x in compound_words] + [1,])
    # print(max_compound_len)

    for s in sentences:
        # tokenize the text using nltk
        word_tokens = get_word_list(s, skipwords, plural_to_singular)
        
        word_list = []
        i = 0
        while i < len(word_tokens):
            l = max_compound_len
            while l > 1:
                if i <= len(word_tokens) - l and \
                        tuple(word_tokens[i:i+l]) in compound_words:
                    word_list.append(' '.join(word_tokens[i:i+l]))
                    i += l
                    break
                l -= 1

            if l == 1:
                word_list.append(word_tokens[i])
                i += 1
        
        word_list.sort()
        print(word_list)

        for word in word_list:
            if word not in unique_word_set:
                unique_word_set.add(word)

        for pair in itertools.combinations(word_list, 2):
            if pair in edges.keys():
                edges[pair] += 1
            else:
                edges[pair] = 1

    gr = nx.Graph()  # initialize an undirected graph
    gr.add_nodes_from(unique_word_set)

    for key, weight in edges.items():
        gr.add_edge(key[0], key[1], weight=weight)

    return gr.to_directed()

def get_scores(sentences, skipwords=[], plural_to_singular={}, compound_words=[]):
    """
    Computes scores based on PageRank algorithm
    args:
        sentences: list of strings
        skipwords: words to skip
        plural_to_singular: dict of (plural, singular) items
        compound_words: list of tuples to replace consecutive words if found
    returns:
        dict of (term, score) items
    """
    gr = build_graph(sentences, skipwords, plural_to_singular, compound_words)
    calculated_page_rank = nx.pagerank(gr, weight='weight')
    return calculated_page_rank

def get_phrase_scores(textlist, keywords, k=2):
    """
    Finds valid phrases (groups of consecutive keywords) of length k
    args:
        textlist: tokenized list of words
        keywords: valid keywords
        k: phrase length
    returns:
        list of tuples
        phrase freq: (phrase tuple, freq)
        keyword freq: (keyword, freq)
    """
    phrase_set = set([])
    phrase_freq = {}
    keyword_freq = {}

    i = k-1
    while i < len(textlist):
        consecutive = tuple(textlist[i-k+1:i+1])
        if all([word in keywords for word in consecutive]):
            phrase_set.add(consecutive)
            if consecutive in phrase_freq.keys():
                phrase_freq[consecutive] += 1
            else:
                phrase_freq[consecutive] = 1
        i += 1
        
    keyword_freq = {}
    for word in textlist:
        if word in keywords:
            if word in keyword_freq.keys():
                keyword_freq[word] += 1
            else:
                keyword_freq[word] = 1

    # Get phrase scores
    phrases = list(phrase_set)
    phrase_scores = {}
    for p in phrases:
        score = np.prod([phrase_freq[p] / keyword_freq[w] for w in p])
        # Normalize score
        phrase_scores[p] = np.power(score, 1/len(p))
                
    return phrase_scores

def extract_top_terms(text, common_words=[], plural_to_singular={}):
    """
    Finds the top terms. This can be either single words or bigrams.
    Top keywords are first found using PageRank. Then we find the top bigrams that
    comprise of keywords. 
    
    Finally we re-run PageRank and replace consecutive words with bigrams
    when applicable.

    args:
        text: string
        common_words: list of common words
        plural_to_singular: dict of (plural, singular) items
    returns:
        list of strings
    """
    stopwords = nltk.corpus.stopwords.words('english')

    sentences = nltk.sent_tokenize(text)
    skipwords = stopwords+common_words
    # Keywords are unigrams
    keyword_scores = get_scores(sentences, skipwords, plural_to_singular)
    print('Keywords found:' , len(keyword_scores.keys()))
    top_keywords = sort_top(keyword_scores, ratio=0.25)
    # print(top_keywords)

    # Get phrases (n-grams where n > 1, n=2 in this case)
    textlist = nltk.word_tokenize(text)

    bigram_scores = get_phrase_scores(textlist, top_keywords, k=2)
    print('Bigrams found:' , len(bigram_scores.keys()))
    top_bigrams = sort_top(bigram_scores, ratio=1)
    print([(w, bigram_scores[w]) for w in top_bigrams])

    trigram_scores = get_phrase_scores(textlist, top_keywords, k=3)
    print('Trigrams found:' , len(trigram_scores.keys()))
    top_trigrams = sort_top(trigram_scores, ratio=1)
    # print(top_trigrams)

    # Terms can be either keywords or phrases
    term_scores = get_scores(sentences, skipwords, plural_to_singular, top_bigrams+top_trigrams)
    top_terms = sort_top(term_scores)

    return top_terms
    