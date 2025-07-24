# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 12:34:26 2025

@author: olivi
"""

############################
# Documents loader         #
#                          #
# Last update : 2025/07/02 #
############################

def load_documents(files):
    """loads a list of files

    Args:
        files (list): a list of names of virtual files (UploadedFile)

    Returns:
        dictionary: of the form key:value with key the name of the file and value the text into this file
    """
    corpus = {}
    for file in files:
        corpus[file.name] = file.read().decode('utf-8')
    return corpus