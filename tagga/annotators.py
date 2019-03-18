import random
from pathlib import Path

import spacy
from spacy.util import minibatch, compounding


class SpacyAnnotator():
    def __init__(self,model=None,labels=()):
        self.is_blank = False
        # load spaCy model
        if model is not None:
            self.nlp = spacy.load(model)
            print("Loaded existing model: ",model)
        else:
            self.nlp = spacy.blank("en")  # create blank Language class
            self.is_blank=True
            ner = self.nlp.create_pipe("ner")
            self.nlp.add_pipe(ner, last=True)
            print("Created blank 'en' model")

        ner = self.nlp.get_pipe("ner")
        for label in labels:
            ner.add_label(label)

    def train(self,X,n_iter):
        # get names of other pipes to disable them during training
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
        with self.nlp.disable_pipes(*other_pipes):
            # only train NER
            # reset and initialize the weights randomly – but only if we're
            # training a new model
            if self.is_blank:
                self.nlp.vocab.vectors.name = 'spacy_pretrained_vectors'
                self.nlp.begin_training()
            for itn in range(n_iter):
                random.shuffle(X)
                losses = {}
                # batch up the examples using spaCy's minibatch
                batches = minibatch(X, size=compounding(4.0, 32.0, 1.001))
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.nlp.update(
                        texts,  # batch of texts
                        annotations,  # batch of annotations
                        drop=0.5,  # dropout - make it harder to memorise data
                        losses=losses,
                    )
                print("Losses", losses)

    def test(self,X):
        import numpy as np
        # test on test data
        scores = list()
        for doc in X:
            spacy_doc = self.nlp(doc[0])
            true = [(ent.text, ent.label_) for ent in spacy_doc.ents]
            print("FOUND: ",true)
            actual = []
            for x in doc[1]["entities"]:
                actual_entity = (doc[0][x[0]:x[1]],x[2])
                actual.append(actual_entity)
            print("ACTUAL:",actual)
            score = len([x for x in actual if x in true])/len(true)
            print("Acuracy: ",score)
            scores.append(score)
        print("Final Score: ",np.mean(scores))

    def eval(self,X):
        # eval a list of texts
        for doc in X:
            spacy_doc = self.nlp(doc)
            print("Entities", [(ent.text, ent.label_) for ent in spacy_doc.ents])
            #print("Tokens", [(t.text, t.ent_type_, t.ent_iob) for t in spacy_doc])


    def persist(self, output_dir):
        # save model to output directory
        if output_dir is not None:
            output_dir = Path(output_dir)
            if not output_dir.exists():
                output_dir.mkdir()
            self.nlp.to_disk(output_dir)
            print("Saved model to", output_dir)

    def load(self,path):
        # test the saved model
        print("Loading from", path)
        self.nlp = spacy.load(path)


def spacy_test_data():
    import test_data.dataturks_to_spacy as dtconv
    docs = dtconv.convert_dataturks_to_spacy("C:\Projects/badmuddatagga/test_data\Entity Recognition in Resumes.json")
    def convert(x):
        return (x[0],x[1],x[2].upper().replace(" ","_"))
    labels = set()
    for doc in docs:
        new_entities = []
        for entity in doc[1]['entities']:
            new_ent = convert(entity)
            new_entities.append(new_ent)
            labels.add(new_ent[2])
        doc[1]["entities"]=new_entities
    return docs,labels



def spacy_ner_test():
    import random
    spacy_resumes,labels = spacy_test_data()

    random.shuffle(spacy_resumes)
    train_data=spacy_resumes[:200]
    annotator = SpacyAnnotator(labels=labels)
    annotator.train(train_data,5)

    test_data = spacy_resumes[::-1][:20]
    annotator.test(test_data)

spacy_ner_test()