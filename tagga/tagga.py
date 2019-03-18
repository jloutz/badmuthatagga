import datetime
import tkinter as tk
import tkinter.font as tkfont
from tkinter.filedialog import askopenfilename, asksaveasfilename
import json
import jsonpickle
import uuid
import os
import re


class TaggaDoc:
    def __init__(self, doc: dict, textkey: str = "text"):
        if textkey not in doc:
            raise Exception("Doc must be dict with text key ", textkey)
        self.text = "\r\n".join([l.strip() for l in doc[textkey].splitlines() if l.strip()])
        ## dict of tuples of form (start,stop,name)
        if "entities" in doc:
            self.entities = doc["entities"]
        else:
            self.entities = dict()
        if "id" in doc:
            self.id = doc["id"]
        else:
            self.id = uuid.uuid4()

    def add_entity_annotaton(self, start: int, end: int, name: str):
        key = self.make_key(start, end, name)
        text = self.text[start:end]
        annot = (start, end, name, text)
        self.entities[key] = annot
        print("Added ", str(annot))

    def remove_entity_annotation(self, start: int, end: int, name: str):
        key = self.make_key(start, end, name)
        del self.entities[key]

    @classmethod
    def make_key(cls, start: int, end: int, name: str):
        return str(start) + "_" + str(end) + "_" + name


class TaggaConf:
    def __init__(self):
        ## config
        self.json_text_key = "content"
        self.tagga_home = os.path.join("C:\\Anwendungen", "badmuthatagga")
        self.tag_config = {"SKILL": dict(foreground='green', borderwidth=2, relief=tk.RIDGE),
                           "activity": dict(foreground='blue', background='gray')}


class TaggaProject:

    def __init__(self, json=None, tagga_conf=TaggaConf()):
        self.tagga_conf = tagga_conf
        ## creation timestamp
        self.ts = str(datetime.datetime.now()).split(".")[0].replace(" ", "_").replace(":", "_")
        if json is not None:
            ## new project from json
            self.tagga_docs = [TaggaDoc(doc, textkey=self.tagga_conf.json_text_key) for doc in json]
        else:
            ## new project
            self.tagga_docs = list()
        self.tagga_conf = tagga_conf
        self.autotagga = AutoTagga()

    @classmethod
    def _load(cls, path):
        with open(path) as f:
            project_raw_json = f.read()
        proj = jsonpickle.decode(project_raw_json)
        return proj

    def save(self, path=None):
        if path is None:
            path = os.path.join(self.tagga_conf.tagga_home, "tagga_project-" + self.ts + ".tagga")
        project_json = jsonpickle.dumps(self)
        with open(path, 'w+') as f:
            f.write(project_json)
        print("Wrote project to ", path)
        return path


class AutoTagga:
    def __init__(self):
        ## set of tuples of form (<entityvalue>,<entityname>) e.g. ("Teamplayer","SKILL")
        self.vocab = set()

    def add_to_vocab(self, entity_val, entity_type):
        self.vocab.add((entity_val, entity_type))

    def remove_from_vocab(self, entity_val, entity_type):
        ## TODO check this global removing behavior!
        ## for now, removing once from one doc removes from entire vocab
        ## until it is added again - this can mess stuff up
        ## TODO perhaps doc-level blacklist?
        self.vocab.remove((entity_val, entity_type))

    def autotag(self, doc: TaggaDoc):
        new_entities = list()
        for entry in list(self.vocab):
            matched_entities = [(m.start(), m.end(), entry[1], m.group(0)) for m in re.finditer(entry[0], doc.text)]
            new_entities.extend([(ent[0], ent[1], ent[2]) for ent in matched_entities if
                            not TaggaDoc.make_key(ent[0], ent[1], ent[2]) in doc.entities])
        print("Autotagger added {} new entities from vocab".format(len(new_entities)))
        for ent in new_entities:
            doc.add_entity_annotaton(ent[0], ent[1], ent[2])



class Tagga(tk.Tk):
    def __init__(self, config=TaggaConf()):
        tk.Tk.__init__(self)
        self.title("Bad Mutha Tagga")

        self.tagga_config = config
        os.makedirs(self.tagga_config.tagga_home, exist_ok=True)
        self.active_project:TaggaProject = None
        self.active_project_path = None

        ## Toolbar
        self.toolbar = tk.Frame(self)
        self.toolbar.pack(side="top", fill="x")

        menubar = tk.Menu(self.toolbar)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Import JSON", command=self.import_json)
        filemenu.add_command(label="Export Annotations", command=None)

        projmenu = tk.Menu(menubar, tearoff=0)
        projmenu.add_command(label="Load Tagga Project (Ctrl-l)", command=self.load_tagga_project, accelerator="Ctrl+L")
        projmenu.add_command(label="Save Tagga Project (Ctrl-s)", command=self.save_tagga_project, accelerator="Ctrl+S")
        projmenu.add_command(label="Save Tagga Project As (Ctrl-a)", command=self.save_tagga_project_as,
                             accelerator="Ctrl+A")

        menubar.add_cascade(label="Import/Export", menu=filemenu)
        menubar.add_cascade(label="Project", menu=projmenu)
        self.config(menu=menubar)

        ## Button bar
 #       buttonbar = tk.Frame(self,bd=1,relief="sunken",background="white",padx=20)
#        img = tk.Image(file="C:\Projects/badmuddatagga/tagga/resources\ml_train.png")
  #      train_button = tk.Button(buttonbar,text="Train",image=img,command=self.train_ml_annotator)
   #     train_button.pack(side="right")
    #    buttonbar.pack(fill="x")

        ## Main part of the GUI
        main_pane = tk.PanedWindow(self)
        main_pane.pack(fill=tk.BOTH, expand=1)
        # I'll use a frame to contain the widget and
        # scrollbar; it looks a little nicer that way...
        text_frame = tk.Frame(borderwidth=1, relief="sunken")
        self.text = tk.Text(wrap="word", background="white",
                            borderwidth=0, highlightthickness=0)
        asb = tk.Scrollbar(orient="vertical", borderwidth=1,
                           command=self.text.yview)
        self.text.configure(yscrollcommand=asb.set)
        asb.pack(in_=text_frame, side="right", fill="y", expand=False)
        self.text.pack(in_=text_frame, side="left", fill="both", expand=True)

        self.document_listbox = tk.Listbox(exportselection=False)
        self.document_listbox.bind('<<ListboxSelect>>', self.on_content_select)

        self.text.configure(yscrollcommand=asb.set)
        asb.pack(in_=text_frame, side="right", fill="y", expand=False)

        main_pane.add(self.document_listbox)
        main_pane.add(text_frame)
        main_pane.pack()

        self.bind_all("<Control-s>", self.save_tagga_project)
        self.bind_all("<Control-a>", self.save_tagga_project_as)
        self.bind_all("<Control-l>", self.load_tagga_project)

        # tagga tags
        self.tagga_tags = self.tagga_config.tag_config
        for name, conf in self.tagga_tags.items():
            self.text.tag_configure(name, **conf)

        # set up a binding to tag selected text.
        self.text.bind("<Control-Shift-:>", self.tag_add)
        self.text.bind("<Control-Shift-_>", self.tag_remove)

    def train_ml_annotator(self,event):
        print("training...")

    def tag_add(self, event):
        ## handles tag event from gui
        start = int(self.text.count(1.0, tk.SEL_FIRST)[0])
        end = int(self.text.count(1.0, tk.SEL_LAST)[0])
        print("Start: {}, End: {}".format(start, end))
        # add tag to doc backing object
        self.current_doc.add_entity_annotaton(start, end, "SKILL")
        # add tag to autotagger vocab
        text = self.text.selection_get()
        self.active_project.autotagga.add_to_vocab(text,"SKILL")
        #visualize
        self._tag_add(start, end)

    def _tag_add(self, start, end, name="SKILL"):
        ## visualizes the tag in text area
        print("{} {} {}".format(start, end, name))
        index1 = "1.0+" + str(start) + "c"
        index2 = "1.0+" + str(end) + "c"
        self.text.tag_add(name, index1, index2)

    def tag_remove(self, event):
        print(event)
        start = int(self.text.count(1.0, tk.SEL_FIRST)[0])
        end = int(self.text.count(1.0, tk.SEL_LAST)[0])
        # remove tag from doc backing object
        self.current_doc.remove_entity_annotation(start, end, "SKILL")
        # remove from autotag vocab
        text = self.text.selection_get()
        self.active_project.autotagga.remove_from_vocab(text, "SKILL")
        self.text.tag_remove("SKILL", tk.SEL_FIRST, tk.SEL_LAST)

    def autotag(self,doc):
        self.active_project.autotagga.autotag(doc)

    def on_content_select(self, event):
        print(str(self.document_listbox.curselection()))
        if not self.document_listbox.curselection():
            return
        index = int(self.document_listbox.curselection()[0])
        print("selected index: ", index)
        self.current_doc: TaggaDoc = self.active_project.tagga_docs[index]
        ## Autotag! (this makes it a bad mutha tagga
        self.autotag(self.current_doc)
        ## update text in main window
        self.text.delete(1.0, tk.END)
        self.text.insert(1.0, self.current_doc.text)
        ## visualize tags in window
        for key in self.current_doc.entities:
            ent = self.current_doc.entities[key]
            print(str(ent))
            self._tag_add(ent[0], ent[1], ent[2])

    def load_tagga_project(self, event=None):
        fname = askopenfilename(filetypes=[("Tagga Project", "*.tagga")])
        self.active_project = TaggaProject._load(fname)
        self.active_project_path = fname
        self.init_content_panel()

    def save_tagga_project(self, event=None):
        return self.active_project.save(self.active_project_path)

    def save_tagga_project_as(self, event=None):
        fname = asksaveasfilename(filetypes=[("Tagga Project", "*.tagga")])
        self.active_project_path = self.active_project.save(path=fname)

    def import_json(self):
        fname = askopenfilename(filetypes=[("JSON Files", "*.json")])
        if fname:
            with open(fname) as f:
                docs = json.load(f)
            if not isinstance(docs, list):
                raise Exception("bad json.. bad!")
            if len(docs) == 0:
                raise Exception("no docs to load..")
            ## save active project if exists
            if self.active_project is not None:
                self.active_project.save(self.active_project_path)
            ## create new project with json docs and save right away
            self.active_project = TaggaProject(json=docs, tagga_conf=self.tagga_config)
            self.active_project_path = self.active_project.save()
            self.init_content_panel()

    def init_content_panel(self):
        # self.content_list_panel.delete(0,tk.END)
        children = self.document_listbox.winfo_children()
        for c in children:
            c.delete()
        for doc in self.active_project.tagga_docs:
            self.document_listbox.insert(tk.END, doc.text.split()[:3])


if __name__ == "__main__":
    app = Tagga()
    app.mainloop()
