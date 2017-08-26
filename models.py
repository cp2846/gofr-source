
"""
-------------------------------------------------------------
                        MODELS
Declaration of database models to be used in the software.
-------------------------------------------------------------
"""

from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import secure_filename
import os
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from PIL import Image, ImageOps
from datetime import datetime
from math import ceil
from sqlalchemy import desc
import helper_functions


app = Flask(__name__, static_url_path='/resources')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
UPLOAD_FOLDER = 'files/'
THUMBNAIL_FOLDER = 'thumbs/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER
app.config['MAX_FREE_STORAGE'] = 2000000000
site_path = 'SITE PATH GOES HERE'
db = SQLAlchemy(app)

# migration manager
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

class User(db.Model):
 
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(30), unique=True)
    pw_hash = db.Column(db.String(300))
    date = db.Column(db.DateTime)
    auth_token = db.Column(db.String(35))
    folders = db.relationship('Folder', 
                               backref='user', 
                               lazy='dynamic')
    is_admin = db.Column(db.Boolean())
    used_storage = db.Column(db.Integer())
    
    def __init__(self, username, password, is_admin=False):
        
        # username: str
        # password: str
        
        self.username = username
        self.set_password(password)
        self.pageviews = 0
        self.date = datetime.utcnow()
        self.is_admin = is_admin
        self.used_storage = 0
        
    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)
        
    def add_folder(self, name):
        new_folder = Folder(name, self.id)
        db.session.add(new_folder)
        db.session.commit()
    
    def number_of_files(self):
        return File.query.filter(File.folder_id.in_([folder.id for folder in self.folders])).count()
        
    def number_of_folders(self):
        return self.folders.count()
    
    def get_root_folders(self, page=1, results_per_page=25):
        return Folder.query.filter_by(user=self).filter_by(parent=None).offset((page - 1) * results_per_page).limit(results_per_page).all()
        
    def get_auth_token(self):
        if 'auth_token' in session and 'username' in session:
            return session['auth_token']
            
    def get_used_storage_str(self):
        return helper_functions.format_bytes(self.used_storage)
        
    def space_available(self, size):
        return self.is_admin or app.config['MAX_FREE_STORAGE'] - self.used_storage > size
    

class Folder(db.Model):

    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(128))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    date = db.Column(db.DateTime)
    private = db.Column(db.Boolean)
    password_protected = db.Column(db.Boolean)
    files = db.relationship('File', 
            backref='folder', lazy='dynamic')
    pw_hash = db.Column(db.String(300))        
    parent_id = db.Column(db.Integer(), db.ForeignKey('folder.id'), index=True)     
    parent = db.relationship(lambda: Folder, remote_side=id, backref='children')
    extends_permissions = db.Column(db.Boolean)
    
    
    def __init__(self, name, user_id, private=True, password=None, password_protected=False, extends_permissions=None):
        # name: str
        # user_id: int
        self.id = self.generate_id()
        self.name = name
        self.user_id = user_id
        self.date = datetime.utcnow()
        self.private = private
        self.parent_id = None
        self.set_password(password)
        self.password_protected = password_protected
        self.extends_permissions = extends_permissions
        
    
    def generate_id(self):  
        # return: str
        id = helper_functions.generate_random_string(9)

        # check if the ID already being used (to avoid collisions)
        existing_folder = Folder.query.filter_by(id=id).first()        
        if existing_folder:
            return self.generate_id()  
        return id
        
    def set_password(self, password):
        if password:
            self.pw_hash = generate_password_hash(password)
        else:
            self.pw_hash = None
            
    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)
        
    def add_file(self, file):
        # file: File
        self.files.append(file)
        db.session.commit()
        
    def delete(self):
        for child in self.children:
            child.delete()
        for file in self.files:
            file.delete()
        db.session.delete(self)
        db.session.commit()
    
    def set_parent(self, parent):
        if parent != self and not parent.is_child_of(self):
            if self.parent:
                self.parent.children.pop(self)
            
            self.parent_id = parent.id
            self.parent = Folder.query.filter_by(id=self.parent_id).first()
            self.parent.children.append(self)
            db.session.commit()
            

    def is_child_of(self, folder):
        """
            Returns true if self is a child of folder 
        """
        parent_folder = self.parent
        while parent_folder:
            if parent_folder == folder:
                return True
            parent_folder = parent_folder.parent
            
        return False
        

    def search(self, term, user=None, recursive=True):
        
        """
            
            term: str
            user: User
            recursive: bool

            Performs a depth-first search for files and folders that match the given search term, 
            returns a list of File results.
        
            TODO: Replace with a more efficient query (this is just a prototype feature 
            and isn't super scalable as-is...)
            
        """
        results = []
        
        def traverse(folder):
        
            matched_files = File.query.filter_by(folder_id=folder.id).filter(File.name.like('%'+term+'%')).all()
            matched_folders = Folder.query.filter_by(parent_id=folder.id).filter(Folder.name.like('%'+term+'%')).all()
            
            for file in matched_files:
                results.append(file)
            for matched_folder in matched_folders:
                if matched_folder.visible_to(user):
                    results.append(matched_folder)
                
            for child in folder.children:
                if child.visible_to(user):
                    traverse(child)
        
        traverse(self)      
        
        return results
        
   
    def number_of_files_folders(self, user=None):
    
        """
            Returns a list containing 2 integers: [folders, files]
            The first integer is the number of subfolders visible to the user.
            the second is the number of files visible to the user.
        """
    
        results = [0, 0]
        results[1] += File.query.filter_by(folder_id=self.id).count()
        
        def traverse(folder):
            children = [c for c in folder.children if c.visible_to(user)]
            for child in children:
                results[0] += 1
                results[1] += File.query.filter_by(folder_id=child.id).count()
                traverse(child)
                
        traverse(self)
        
        return results

    
    def get_path(self):
    
        """ 
            return: List
        """
        
        path = [self]
        parent_folder = self.parent
        
        while parent_folder:
            path.append(parent_folder)
            parent_folder = parent_folder.parent
        
        return path[::-1]
        
    
    def get_contents(self, offset=None, limit=None, sort="date", recursive=False, search=None, user=None, selected_file=None):
    
        """
        
            method for querying folders 
            returns a hashmap/dictionary object containing:
            {
                "content": paginated results page
                "prev": the previous file
                "next": the next file
                "total_pages": the total number of pages of results
                "total_files": the file count
                "current_index": index of the selected file (or 0)
                "next_on_same_page?": True if next file is on the current page
                "prev_on_same_page?": True is previous file is on the current page
            }
            
            Optional parameters:
            
            limit: int        
            offset: int
            sort: string ("date", "type" or "name")
            search: string - terms to be searched
            recursive: boolean - searches all subfolders recursively if set to True
            selected_file: File - if specified, will find the previous/next file objects in the list (for template purposes)
            
            example usage:
            
                folder = Folder.query.filter_by(id=id).first() 
                results = folder.get_contents(page * per_page, per_page, search="foo", user=get_user())
                this_page = results["content"]
            
        """
        
        if search:
            search = search.lower()
            all = self.search(search, user=user, recursive=recursive)

        else:
            all = []
            subfolders = [child for child in self.children if child.visible_to(user)]
            files = File.query.filter_by(folder=self).all()
            all = subfolders + files 
            
        if not offset:
            offset = 0
            
        if not limit:
            limit = len(all)
        
        if sort == "type":
            folders = [f for f in all if f.get_type() == "Folder"]
            files = [f for f in all if not f.get_type() == "Folder"]
            
            all = folders + sorted(files, key=lambda x: x.extension)

        elif sort == "name":
            all = sorted(all, key=lambda x: x.name.lower())

        else:
            all = sorted(all, key=lambda x: x.date, reverse=True)
        
        if offset > len(all):
            offset = len(all) - limit
            
        content = all[offset:offset + limit]
        
        def get_prev_next(selected_file):
        
            # selected_file: File
            # returns: dict(index: int, prev: File, next: File)
            
            res = {
                    "index": 0,
                    "prev": None,
                    "next": None,
                }
            file_list = [f for f in all if not f.get_type() == "Folder"]
            for i, file in enumerate(file_list):
                if file == selected_file:
                    res["index"] = i + 1
                    if i > 0:
                        res["prev"] = file_list[i - 1]
                    if i < len(file_list) - 1: 
                        res["next"] = file_list[i + 1]
            return res
        prev_next_dict = get_prev_next(selected_file)
        current_index, prev, next = prev_next_dict["index"], prev_next_dict["prev"], prev_next_dict["next"]
        
        
        return {
            "content": content,
            "prev": prev,
            "next": next,
            "total_pages": int(ceil(len(all) / float(limit))),
            "total_files": len([f for f in all if not f.get_type() == "Folder"]),
            "current_index": current_index,
            "next_on_same_page?": next in content,
            "prev_on_same_page?": prev in content,
        }

    def get_type(self):
        return "Folder"
        
    def visible_to(self, user):
	if user and user.is_admin:
            return True
        if self.password_protected and self.id in session and session[self.id] == self.pw_hash:
            return True
        
        return self.user == user or (not self.private and not self.password_protected)
    
    def has_password(self):
        return self.pw_hash != None
        
    def update(self):
        for folder in self.get_path():
            folder.date = datetime.utcnow()
        db.session.commit()
        
        
class File(db.Model):

    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(128))
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'))
    extension = db.Column(db.String(10))
    path = db.Column(db.String())
    thumb_path = db.Column(db.String())
    date = db.Column(db.DateTime)
    type = db.Column(db.String)
    size = db.Column(db.Integer)
    md5 = db.Column(db.String(32))
    full_name = db.Column(db.String)
    
    def __init__(self, name, folder_id):
    
        # name: str
        # folder_id: str
    
        self.id = self.generate_id()
        self.name = secure_filename(name)
        self.extension = self.get_extension()
        self.folder_id = folder_id
        self.full_name = self.id + "_" + self.name
        self.path = os.path.join(app.config['UPLOAD_FOLDER'], self.full_name)
        self.date = datetime.utcnow()
        self.thumb_path = None
        self.md5 = None
        self.type = self.get_type()
        self.size = 0
        
        
    def set_thumbnail(self):
        type_paths = {
            "Video" : os.path.join(app.config['THUMBNAIL_FOLDER'], "video.png"),
            "Audio" : os.path.join(app.config['THUMBNAIL_FOLDER'], "audio.png"),
            "Chiptune" : os.path.join(app.config['THUMBNAIL_FOLDER'], "module.png"),
            "Archive" : os.path.join(app.config['THUMBNAIL_FOLDER'], "archive.png"),
            "Photoshop" : os.path.join(app.config['THUMBNAIL_FOLDER'], "psd.png"),
            "SAI" : os.path.join(app.config['THUMBNAIL_FOLDER'], "sai.png"),
            "Other" : os.path.join(app.config['THUMBNAIL_FOLDER'], "other.png"),
        }
    
        if self.get_type() == "Image":
            # open the image and generate a 250x250 thumbnail
            img = Image.open(site_path+self.path).convert('RGB')
            thumb = ImageOps.fit(img, (250,250), Image.BICUBIC)
            self.thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], self.id + "_" + self.name)
            thumb.save(site_path+self.thumb_path, quality=100)
        else:
            self.thumb_path = type_paths[self.get_type()]

    
    def get_extension(self):
        # return: str
        return self.name.split('.')[-1].lower()
    
    
    def generate_id(self):
        # return: str
        id = helper_functions.generate_random_string(9)
        existing_file = File.query.filter_by(id=id).first()
        if existing_file:
            return self.generate_id()
        return id

    def get_type(self):
        extension = self.extension
        types = {
            "Video" : ["webm", "wmv", "avi", "mov"],
            "Audio" : ["mp3", "wav"],
            "Chiptune" : ["mod", "xm", "it"],
            "Archive" : ["zip", "tar", "rar"],
            "Photoshop" : ["psd"],
            "Image" : ["gif", "jpg", "jpeg", "png", "bmp"],
            "SAI" : ["sai"]
        }
        for type in types:
            if extension in types[type]:
                return type
        return "Other"
        
    def delete(self):
        path = self.path
        thumb_path = self.thumb_path
        type = self.type
        self.folder.user.used_storage -= self.size
        db.session.delete(self)
        db.session.commit()
        # delete the data from the server if no other File points to it
        if not File.query.filter_by(path=path).count() > 0:
            try:
                os.remove(path)
                if type == "Image":
                    os.remove(site_path+thumb_path)
            except:
                pass

    def get_size_str(self):
        return helper_functions.format_bytes(self.size)
        
    def set_size(self):
        
        self.size = os.path.getsize(site_path+self.path)
        self.folder.user.used_storage += self.size
        db.session.commit()
        
    def visible_to(self, user):
        # return: bool
        if self.folder.extends_permissions:
            return self.folder.visible_to(user)
        return True
        
    def set_md5(self):
        from hashlib import md5
        md5_gen = md5()
        with open(site_path+self.path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_gen.update(chunk)
        self.md5 = md5_gen.hexdigest()
        db.session.commit()
        
    def check_duplicates(self):
        
        """
            Checks if the file already exists on the server. If it does,
            simply have the file point to the old path, and delete the duplicate 
            (to save server space).
        """
        existing_file = File.query.filter_by(md5=self.md5).order_by(File.date).first()
        if existing_file and existing_file != self:
            os.remove(site_path+self.path)
            if self.get_type() == "Image":
                os.remove(site_path+self.thumb_path)
            self.path = existing_file.path
            self.full_name = existing_file.full_name
            self.thumb_path = existing_file.thumb_path
            db.session.commit()

    
if __name__ == '__main__':
    manager.run()
