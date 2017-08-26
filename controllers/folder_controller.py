"""
-------------------------------------------------------------
                    FOLDER CONTROLLER
For general routines such as displaying folders, searching them, 
                changing folder settings, etc.
-------------------------------------------------------------
"""
from flask_sqlalchemy import SQLAlchemy
from models import *
from flask import redirect, url_for, flash, request, abort, render_template
from helper_functions import get_user, valid_file

site_path = ''
def folder_add(id=None):
    user = get_user()
    folder = Folder.query.filter_by(id=id).first()
    password_protected = False
    private = False
    extends_permissions = False
    
    if id and not folder:
        abort(404)
    if folder and not folder.user == user:
        abort(404)
        
    if request.method == "POST":
        name = request.form['folder-name'].strip()
        password = request.form['folder-password']

        privacy = int(request.form['privacy']) if int(request.form['privacy']) in [1,2,3] else 1
        
        if not name:
            flash('Name field cannot be blank.', 'error')
            return render_template('folder_add.html', folder=folder, user=user)
    
        if privacy == 1:
            private = True
        if privacy == 2: 
          
            if not len(password) > 0:
                flash('Password cannot be blank.', 'error')
                return render_template('folder_add.html', folder=folder, user=user)
                
            password_protected = True
            
        if request.form.get('extends-permissions'):
            extends_permissions = True

        new_folder = Folder(name, user.id, private=private, password=password, 
                            password_protected=password_protected, 
                            extends_permissions=extends_permissions)
        db.session.add(new_folder)
        if folder:
            new_folder.set_parent(folder)
        db.session.commit()
        
        return redirect(url_for('folder', id=new_folder.id))
    return render_template('folder_add.html', user=user, folder=folder)
        
def show_folder(id):

    user = get_user()
    folder = Folder.query.filter_by(id=id).first()
    file_id = request.args.get("file_id")
    
    # redirect user if supplied id is invalid
    if not folder:
        flash("Invalid folder id.", "error")
        return redirect(url_for('login'))
        
    if folder.password_protected and not folder.visible_to(user):
       return redirect(url_for('folder_authenticate', id=folder.id))
       
    # show access denied page if folder is private
    if not folder.visible_to(user):
        abort(404)
    
    if request.method == "POST":
        if not folder.user == user:
            abort(401)
        auth_token = request.form['auth-token']
        if not auth_token == user.get_auth_token():
            abort(401)
            
        new_files = []

        files = request.files.getlist('file[]')
        
        if len(files) > 60:
            flash("Too many files. Maximum 60 per upload", "error")
            return redirect(url_for('folder'))
            
        if not files[0]:
            flash("No files selected.", "error")
            return redirect(url_for('folder', id=folder.id))
        
        failed_files = {
                        "invalid": [],
                        "duplicate": [],
                        "insufficient_space": [],
                       }
                       
        for file in files:
            if file and valid_file(file.filename):
                # add new submission to the database
                new_file = File(file.filename, folder.id)
                file.save(site_path+new_file.path)
                new_file.set_thumbnail()
                db.session.add(new_file)
                db.session.commit()
                new_file.set_size()
                new_file.set_md5()
                new_file.check_duplicates()
                
                if File.query.filter_by(folder_id=folder.id).filter_by(md5=new_file.md5).count() > 1:
                    failed_files["duplicate"].append(file.filename)
                    new_file.delete()
                elif not user.space_available(new_file.size):
                    failed_files["insufficient_space"].append(file.filename)
                    new_file.delete()
                else:
                    new_files.append(new_file)
                    folder.update()
                    
            else:
                failed_files["invalid"].append(file.filename)
            
        if failed_files["invalid"]:
            flash("Could not upload the following files (invalid type): " + \
                    ", ".join([ f for f in failed_files["invalid"] ]) , "error")
            
        if failed_files["duplicate"]:
            flash("Files already exist in folder: " + ", ".join([ f for f in failed_files["duplicate"] ]), "warning")
            
        if failed_files["insufficient_space"]:
            flash("Could not upload files (insufficient storage space): " + ", ".join([ f for f in failed_files["insufficient_space"] ]), "warning")
            
        redirect_id = new_files[-1].id if new_files else None
        return redirect(url_for('folder', id=folder.id, file_id=redirect_id))
   
    
    elif request.args.get("search"):
        search = request.args.get("search").lower()
        recursive = True
    else:
        search = None
        recursive = False
    
    # get/sanitize the page number
    page = request.args.get("page")
    
    try:
        page = max(1, int(page))
    except:
        page = 1
    
    if file_id:
        file = File.query.filter_by(id=file_id).first()
    else:
        file = None
    
    if file_id and (not file or not file.folder.visible_to(user)):
        flash("Invalid file ID", 'error')
    sort = request.args.get("sort")
    if not sort or not sort.lower() in ["date", "name", "type"]:
        sort = "date"
    num_files_folders = folder.number_of_files_folders(user=user)
    per_page = 25
    results = folder.get_contents((page - 1) * per_page, per_page, sort=sort, search=search, 
                                    selected_file=file, recursive=recursive, user=user)
    page = min(results["total_pages"], page)
   
    return render_template("folder.html", folder=folder, user=user, file=file, 
                            num_files_folders=num_files_folders, page=page, sort=sort, 
                            per_page=per_page, search=search, results=results)
    
    
def folder_settings(id):
    
    user = get_user()
    folder = Folder.query.filter_by(id=id).first_or_404()
    if not folder.user == user:
        abort(400)
    
    if request.method == "POST":
        name = request.form['folder-name'].strip()
        password = request.form['folder-password']
        privacy = int(request.form['privacy']) if int(request.form['privacy']) in [1,2,3] else 1
        
        if not name:
            flash('Name field cannot be blank.', 'error')
            return render_template('folder_settings.html', folder=folder, user=user)
    
        if privacy == 1:
            private = True
        else:
            private = False
        if privacy == 2: 
            password_protected = True
        else:
            password_protected = False
            
        if request.form.get('extends-permissions'):
            extends_permissions = True
        else:
            extends_permissions = False
        
        if len(password) > 0:
            folder.set_password(password)
        
        if password_protected:
            if not folder.has_password():
                flash('Folder does not have a password.', 'error')
                return render_template('folder_settings.html', folder=folder, user=user)
            
        folder.password_protected = password_protected
        folder.extends_permissions = extends_permissions
        folder.private = private
        folder.name = name
        
                
        db.session.commit()
        flash('Successfully updated folder.', 'success')
        return redirect(url_for('folder', id=id))
    return render_template('folder_settings.html', folder=folder, user=user)  
    
def show_all_folders():
    user = get_user()
    return render_template("user.html", user=user)
    
