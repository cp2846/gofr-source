"""
-------------------------------------------------------------
                        AUTH CONTROLLER
For authentication-related routines, such as user registration,
              login, file/folder passwords, etc.
-------------------------------------------------------------
"""


from models import *
from flask import redirect, url_for, flash, request, abort, render_template
from helper_functions import get_user, valid_username, generate_random_string
from sqlalchemy import desc, func


def register():

    errors = []
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        existing_user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        
        if not valid_username(username):
            errors.append("Invalid username: must contain only alphanumeric characters and be less than or equal to 20 characters in length")
        
        if existing_user:
            errors.append("Username is already taken")
            
        if password != password_confirm:
            errors.append("Passwords do not match")

        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        
        if len(errors) > 0:
            for error in errors:
                flash(error, 'error')
            return redirect('register')
            
        
        else:
            new_user = User(username, password)
            new_folder = Folder("Default", new_user.id)
            new_user.folders.append(new_folder)
            db.session.add(new_user, new_folder)
            db.session.commit()

            session['username'] = request.form['username']
            session['auth_token'] = helper_functions.generate_random_string(30)
            

            return redirect(url_for('user'))
            

    if get_user():
        return redirect(url_for('user'))

    return render_template('register.html')  

def login():
    if request.method == 'POST':
    
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()

        if user and user.check_password(password):
         
            # create session
            session['username'] = request.form['username']
            session['auth_token'] = helper_functions.generate_random_string(30)
            
            
            return redirect(url_for('user'))
        else:
            flash('Invalid login credentials.', 'error')
            
    
    if get_user():
        return redirect(url_for('user'))  
    return render_template('login.html')

def logout():
    user = get_user()
    session.pop('username', None)
    return redirect(url_for('index'))


def folder_authenticate(id):
    
    folder = Folder.query.filter_by(id=id).first_or_404()
    
    if folder.visible_to(get_user()):
        return redirect(url_for('folder', id=folder.id))
    
    if not folder.password_protected:
        abort(404)
    
    if request.method == "POST": 
        password = request.form['password']
       
        if folder.check_password(password): 
            session[folder.id] = folder.pw_hash
            return redirect(url_for('folder', id=folder.id))
        
        else:
            flash('Incorrect password.', 'error')
  
    return render_template('folder_authenticate.html', folder=folder)
    
def file_authenticate(id):

    file = File.query.filter_by(id=id).first_or_404()
    
    if file.visible_to(get_user()):
        return redirect(url_for('uploaded_file_short', id=file.id))
        
    if not file.folder.password_protected:
        abort(404)
        
    if request.method == "POST":
        password = request.form['password']
        
        if file.folder.check_password(password):
            session[file.folder.id] = file.folder.pw_hash
            return redirect(url_for('uploaded_file_short', id=file.id))
        
        else:
            flash('Incorrect password.', 'error')
            
    return render_template('folder_authenticate.html')
    
    
