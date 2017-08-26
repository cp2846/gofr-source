"""
-------------------------------------------------------------
                    ACTION CONTROLLER
For user actions such as moving or deleting files/folders.
-------------------------------------------------------------

"""


from models import db, Folder, User, File
from flask import redirect, url_for, flash, request
from helper_functions import get_user

def actions():
    return_id = request.form.get('folder-id')
    return_folder = Folder.query.filter_by(id=return_id).first()
    selected_folders = request.form.getlist('folder')
    selected_files = request.form.getlist('file')
    failed_files = []
    
    # handle deletions
    if request.form['delete']:
        for folder_id in selected_folders:
            folder = Folder.query.filter_by(id=folder_id).first()
            # validation check - want to make sure that supplied folder actually exists and belongs to the user
            if not folder or not folder.user == get_user():
                flash("Cannot delete folder " + folder_id + ": invalid folder ID", "error")
            else:
                folder.delete()

        for file_id in selected_files:
            file = File.query.filter_by(id=file_id).first()
            if not file or not file.folder.user == get_user():
                failed_files.append(file)
            else:
                file.delete()
        
        if failed_files:
            flash("Cannot delete files " + " ".join([ f.id for f in failed_files ]) + ": invalid file ID", "error")
    if return_id:
        return redirect(url_for('folder', id=return_id))
    else:
        return redirect(url_for('user'))
        
    