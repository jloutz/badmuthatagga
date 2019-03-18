############################################  NOTE  ########################################################
#
#           Creates NER training data in Spacy format from JSON downloaded from Dataturks.
#
#           Outputs the Spacy training data which can be used for Spacy training.
#
############################################################################################################
import json
import logging

def load_dataturks_resumes(path="C:/Projects/badmuddatagga/test_data/Entity Recognition in Resumes.json"):
    with open(path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
    datalist = []
    for line in lines:
        data = json.loads(line)
        datalist.append(data)
    return datalist


def convert_dataturks_to_spacy(dataturks_JSON_FilePath):
    try:
        training_data = []
        lines=[]
        with open(dataturks_JSON_FilePath, 'r',encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            data = json.loads(line)
            text = data['content']
            entities = []
            if data['annotation'] is None:
                continue
            for annotation in data['annotation']:
                #only a single point in text annotation.
                point = annotation['points'][0]
                labels = annotation['label']
                # handle both list of labels or a single label.
                if not isinstance(labels, list):
                    labels = [labels]

                for label in labels:
                    #dataturks indices are both inclusive [start, end] but spacy is not [start, end)
                    entities.append((point['start'], point['end'] + 1 ,label))


            training_data.append((text, {"entities" : entities}))

        return training_data
    except Exception as e:
        logging.exception("Unable to process " + dataturks_JSON_FilePath + "\n" + "error = " + str(e))
        return None