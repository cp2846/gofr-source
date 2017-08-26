"""
-------------------------------------------------------------
                    USER CONTROLLER
          For routines involving user settings.
-------------------------------------------------------------
"""


from models import *
from flask import redirect, url_for, flash, request, render_template
from helper_functions import get_user

def account_settings():
    user = get_user()
    error = False
    if request.method == "POST":
        current_password = request.form['current-password']
        new_password = request.form['new-password']
        password_confirm = request.form['password-confirm']
        
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            error = True
        if not new_password == password_confirm:
            flash('New passwords do not match.', 'error')
            error = True
        if not new_password or not password_confirm:
            flash('Fields cannot be left blank.', 'error')
            error = True
        elif not len(new_password) >= 6:
            flash('Password must be at least 6 characters.', 'error')
            error = True
        
        if not error:
            user.set_password(new_password)
            db.session.commit()
            flash('Successfully updated account settings.', 'success')
            return redirect(url_for('user'))
            
    return render_template('account_settings.html', user=user)
    
