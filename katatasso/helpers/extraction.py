#!/usr/bin/env python3
import os
import sqlite3
import sys
from collections import Counter

import emailyzer
import juicer
import pandas as pd

from katatasso.helpers.const import CLF_DICT_NUM, CLF_TRAININGDATA_PATH, DBFILE
from katatasso.helpers.logger import rootLogger as logger
from katatasso.helpers.utils import progress_bar, save_vectorizer, load_vectorizer

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
except ModuleNotFoundError:
    logger.critical(f'Module scikit-learn not found. Please install before proceeding.')
    sys.exit(2)


def get_all_tags():
    try:
        conn = sqlite3.connect(DBFILE)
        c = conn.cursor()
        c.execute('SELECT filename, tag FROM tags')
        res = c.fetchall()
        return res
    except Exception as e:
        logger.critical(f'Unable to fetch tags from database.')
        logger.error(e)
        sys.exit(2)


# Get the file paths
def get_file_paths():
    logger.debug(f'Retrieving files from {CLF_TRAININGDATA_PATH}..')
    files = os.listdir(CLF_TRAININGDATA_PATH)
    logger.debug(f'     Found {len(files)} files in dir')
    file_paths = [CLF_TRAININGDATA_PATH + filename for filename in files if filename.endswith('.msg') or filename.endswith('.eml')]
    logger.debug(f'     Found {len(file_paths)} MSG/EML files in dir')
    logger.debug(f'         MSG: {len([filename for filename in file_paths if filename.endswith(".msg")])} || EML: {len([filename for filename in file_paths if filename.endswith(".eml")])}')
    return file_paths


# Create a data set for the classification
def make_dataset(dictionary):
    features = []
    labels = []
    tags = get_all_tags()
    if tags:
        logger.debug(f'Creating dataset from {len(tags)} files')
        for filename, tag in progress_bar(tags):
            data = []
            filepath = CLF_TRAININGDATA_PATH + filename
            email = emailyzer.from_file(filepath)
            content = email.html_as_text
            words = juicer.process_text(content, ner=False)
            for entry in dictionary:
                data.append(words.count(entry[0]))
            features.append(data)
            labels.append(tag)
        
    return features, labels


# Make a dictionary of the most frequent words
def make_dictionary():
    tags = get_all_tags()
    words = []
    logger.debug('Creating dictionary..')
    for filename, tag in progress_bar(tags):
        filepath = CLF_TRAININGDATA_PATH + filename
        email = emailyzer.from_file(filepath)
        words += email.html_as_text.split()

    # Remove non-alphanumeric values
    words = [word for word in words if word.isalpha()]

    # Get the count of each word
    dictionary = Counter(words)

    return dictionary.most_common(CLF_DICT_NUM)


def create_dataframe():
    labels = []
    contents = []
    tags = get_all_tags()
    if tags:
        for filename, tag in progress_bar(tags):
            filepath = CLF_TRAININGDATA_PATH + filename
            # Preprocessing
            email = emailyzer.from_file(filepath)
            content = email.html_as_text
            # Lemmatize, remove stopwords
            words = juicer.process_text(content, ner=False)
            text = ' '.join(words)
            contents.append(text)
            labels.append(tag)
        df = pd.DataFrame(list(zip(labels, contents)), columns = ['label', 'message'])

        return df


def process_dataframe(df):
    df['message'] = df.message.map(lambda val: val.lower())
    df['message'] = df.message.str.replace('[^\w\s]', '')

    # Count occurrences
    vectorizer = CountVectorizer()
    counts = vectorizer.fit_transform(df['message'])
    save_vectorizer(vectorizer)
    # Term Frequency Inverse Document Frequency
    transformer = TfidfTransformer().fit(counts)
    counts = transformer.transform(counts)

    return counts, df


def get_tfidf_counts(input):
    words = juicer.process_text(input, ner=False)
    text = ' '.join(words)
    text = text.lower()
    text = text.replace('[^\w\s]', '')

    vectorizer = load_vectorizer()
    counts = vectorizer.transform([text])

    # Term Frequency Inverse Document Frequency
    transformer = TfidfTransformer().fit(counts)
    counts = transformer.transform(counts)
    return counts

def normalize(x_train, x_test):
    scaler = StandardScaler()
    scaler.fit(x_train)

    x_train = scaler.transform(x_train)
    x_test = scaler.transform(x_test)

    return x_train, x_test
