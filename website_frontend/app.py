
from random import randint
from flask import Flask, render_template, request, redirect

app = Flask(__name__)


@app.route('/')
def menu_page():
    #The main menu
     return render_template('index.html')



@app.route('/login')
def login_page():
    # the login page for admins to log into admin page
    return render_template('login.html')


@app.route('/order')
def order_page():
    # The page where customers and mario can place orders
    
    return render_template('order.html')




@app.route('/wrong_login')
def wrong_logon_page():
    return render_template('wrong.html')


@app.route('/admin')
# the page for mario and luigi
def admin_page():
    return render_template('admin.html')


       





    
    

    
