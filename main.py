"""
-------------------------------------------------------------
                    MAIN ROUTES
    Declaration of the available routes in the application.
If you run this file directly, it will start up a Flask server
                 for debugging purposes.
-------------------------------------------------------------
"""

from flask import Flask
from flask import render_template
from flask import url_for, redirect, flash, send_from_directory, abort, request
from flask_sqlalchemy import SQLAlchemy
from models import db
from models import *
from functools import wraps
from controllers import action_controller, auth_controller, folder_controller, user_controller
from helper_functions import get_user

db.init_app(app)

app.secret_key = "[YOUR SECRET KEY HERE]"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not helper_functions.get_user():
            flash('Not logged in.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
    
    
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = helper_functions.get_user()
        if not user or not user.is_admin:
            abort(404)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/actions', methods=['GET', 'POST'])
@login_required
def actions():
    return action_controller.actions()
    
# home page
@app.route('/')
def index():
    if get_user():
        return redirect(url_for('user'))
    return render_template('index.html')

@app.route('/f/add', methods=['GET', 'POST'])        
@app.route('/f/<id>/add', methods=['GET','POST'])
@login_required
def folder_add(id=None):
    return folder_controller.folder_add(id)
    
# show folder route
@app.route('/f/<id>', methods=['GET', 'POST'])
def folder(id):
    return folder_controller.show_folder(id)

@app.route('/f/<id>/auth', methods=['GET','POST'])
def folder_authenticate(id):
    return auth_controller.folder_authenticate(id)

# user is redirected to this page if file is password-protected
@app.route('/i/<id>/auth', methods=['GET','POST'])
def file_authenticate(id):
    return auth_controller.file_authenticate(id)
    
# serve files from /files and /thumbs directories
@app.route('/files/<filename>')
def uploaded_file(filename):
    file = File.query.filter_by(path=filename).first_or_404()
    if file.visible_to(get_user()):
        return send_from_directory(app.config['UPLOAD_FOLDER'], file.full_name)
    abort(404)
    
# alternate route for short URLs
@app.route('/i/<id>')
def uploaded_file_short(id):
    
    id = id.split('.')[0]
    file = File.query.filter_by(id=id).first_or_404()
    
    if file.visible_to(get_user()):
        
        # log file download
        helper_functions.log_data(user_id=get_user().id if get_user() else None, 
                                  ip=request.remote_addr, type=3,
                                  folder_id=file.folder.id, file_id=file.id)

        return send_from_directory(app.config['UPLOAD_FOLDER'], file.full_name)
        
        
    elif file.folder.password_protected:
        return redirect(url_for('file_authenticate', id=id))
        
    abort(404)
        
    

@app.route('/thumbs/<filename>')
def thumbnail_static(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)
    
@app.route('/t/<id>')
def thumbnail(id):

    id = id.split('.')[0]
    file = File.query.filter_by(id=id).first_or_404()
    
    if file.visible_to(get_user()):
        return send_from_directory(app.config['THUMBNAIL_FOLDER'], ''.join(file.thumb_path.split("/")[1::]))

    abort(404)
    
# user profile page
@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    return folder_controller.show_all_folders()


@app.route('/logout')
def logout():
    return auth_controller.logout()
    
@app.route('/login', methods=['GET','POST'])
def login():
    return auth_controller.login()

@app.route('/register', methods=['GET', 'POST'])
def register():
    return auth_controller.register()
        
@app.route('/settings', methods=['GET', 'POST'])       
@login_required
def account_settings():
    return user_controller.account_settings()
        

@app.route('/folder/<id>/settings', methods=['GET', 'POST'])
@login_required
def folder_settings(id):
    return folder_controller.folder_settings(id)

    


if __name__ == '__main__':
    app.run(debug=True)
