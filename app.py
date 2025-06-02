import os
import flask
from flask import render_template, request
from flask import jsonify
import pandas as pd
import pickle
from sklearn.linear_model import LogisticRegression
import requests, json
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask import render_template, request, jsonify, session
from flask_session import Session
from keras.models import Sequential, load_model
from keras.layers import Dense
import numpy as np
from keras.models import load_model
from keras.preprocessing import image
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
import shutil

app = flask.Flask(__name__, template_folder='Templates')
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#code for connection
app.config['MYSQL_HOST'] = 'localhost'#hostname
app.config['MYSQL_USER'] = 'root'#username
app.config['MYSQL_PASSWORD'] = ''#password
app.config['MYSQL_DB'] = 'skincancer'#database name

mysql = MySQL(app)
@app.route('/')

@app.route('/main', methods=['GET', 'POST'])
def main():
    if flask.request.method == 'GET':
        if 'userid' in session:
            return(flask.render_template('diagnosis.html'))
        else:
            return(flask.render_template('index.html'))
        

@app.route('/info', methods=['GET', 'POST'])
def info():
    if flask.request.method == 'GET':
        return(flask.render_template('info.html'))

@app.route('/historypage', methods=['GET', 'POST'])
def historypage():
    if flask.request.method == 'GET':
        return(flask.render_template('historypage.html'))

@app.route('/aboutus', methods=['GET', 'POST'])
def aboutus():
    if flask.request.method == 'GET':
        return(flask.render_template('aboutus.html'))

@app.route('/services', methods=['GET', 'POST'])
def services():
    if flask.request.method == 'GET':
        return(flask.render_template('services.html'))
    
@app.route('/contactus', methods=['GET', 'POST'])
def contactus():
    if flask.request.method == 'GET':
        return(flask.render_template('contactus.html'))
    
    
#Prediction
model = load_model('skin_cancer_network.h5')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST':
        phone           = request.form['signphone']
        password        = request.form['signpassword']
        
        con = mysql.connect
        con.autocommit(True)
        cursor = con.cursor(MySQLdb.cursors.DictCursor)
        qry = 'SELECT * FROM patient_detail WHERE phone="'+phone+'" AND password="'+password+'"'
        result = cursor.execute(qry)
        result = cursor.fetchone()
        if result:
            msg = "1"
            session["userid"]   = result["patient_id"]
            session["username"]   = result["patient_name"]
            session["usermail"]   = result["email"]
        else:
           msg = "0"
    return msg

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if flask.request.method == 'GET':
        session.pop('userid', None)
        session.pop('username', None)
        session.pop('usermail', None)
        
        return(flask.render_template('index.html'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if flask.request.method == 'POST':
        patientname  = request.form['regusername']
        phone        = request.form['regphone']
        email        = request.form['regemail']
        address      = request.form['regaddress']
        age          = request.form['regage']
        gender       = request.form['reggender']
        password     = request.form['regpassword']
        
        con = mysql.connect
        con.autocommit(True)
        cursor = con.cursor(MySQLdb.cursors.DictCursor)
        
        qry = 'SELECT * FROM patient_detail WHERE phone="'+phone+'" AND password="'+password+'"'
        result = cursor.execute(qry)
        result = cursor.fetchone()
        if result:
            msg = '2'
        else:
            cursor.execute('INSERT INTO patient_detail VALUES (NULL, % s, % s, % s, % s, % s, % s, % s, NULL)', (patientname, phone, email, address, age, gender, password, ))
            mysql.connect.commit()
            msg = '1'
        
        return msg

# Function to preprocess the imagle
def preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

# Function to make predictions
def predict(image_path):
    img = preprocess_image(image_path)
    prediction = model.predict(img)
    return prediction

@app.route('/detect', methods=['GET', 'POST'])
def detect():
    if flask.request.method == 'GET':
        return(flask.render_template('diagnosis.html'))
    if flask.request.method == 'POST':
       filename = request.form['filename']
      
       input_path  = './static/input/'+filename
       
       prediction = predict(input_path)
       predicted_class_index = np.argmax(prediction)
       class_labels = ['Benign', 'Malignant']
       predicted_class = class_labels[predicted_class_index]
    
       print("Predicted class:", predicted_class)
       
       con = mysql.connect
       con.autocommit(True)
       cursor = con.cursor(MySQLdb.cursors.DictCursor)
       
       userid = session.get('userid')
       qry = 'SELECT * FROM patient_detail WHERE patient_id="'+str(userid)+'"'
       cursor.execute(qry)
       userdata = cursor.fetchone()
       
       history = 'INSERT INTO history(userid, sample, prediction) VALUES("'+str(userid)+'","'+str(filename)+'","'+str(predicted_class)+'")'
       cursor.execute(history)
       mysql.connect.commit()
       
       output_path = './static/useruploads/'+filename
       shutil.copy(input_path, output_path)
       
    toReturn = {"filename": filename, "prediction":predicted_class, "userdetail":userdata} 
    sendmail(filename, predicted_class, session)
    return jsonify(toReturn)

@app.route('/getrecords', methods=['GET', 'POST'])
def getrecords():        
    if flask.request.method == 'POST':
        userid = session.get("userid")
        con = mysql.connect
        con.autocommit(True)
        cursor = con.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM history WHERE userid="'+str(userid)+'"')
        result = cursor.fetchall();
    return jsonify(result)

@app.route('/printuserdata', methods=['GET', 'POST'])
def printuserdata():        
    if flask.request.method == 'POST':
        
        refid = request.form['refid']
        userid = session.get("userid")
        
        con = mysql.connect
        con.autocommit(True)
        cursor = con.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM history WHERE refid="'+str(refid)+'"')
        history = cursor.fetchone()
        
        cursor.execute('SELECT * FROM patient_detail WHERE patient_id="'+str(userid)+'"')
        userdetail = cursor.fetchone()
        
        result = {"history":history, "userdetail":userdetail}
    return jsonify(result)

@app.route('/reportmail', methods=['GET', 'POST'])
def reportmail():        
    if flask.request.method == 'POST':
        
        refid = request.form['refid']
        userid = session.get("userid")
        
        con = mysql.connect
        con.autocommit(True)
        cursor = con.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM history WHERE refid="'+str(refid)+'"')
        history = cursor.fetchone()
    
        sendmail(history["sample"], history["prediction"], session)
    return jsonify("mailsend")

def sendmail(filename, prediction, session):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login("canvapro.lushanth@gmail.com", "llmf smdr bcuy xeaj")
    #canvapro.lushanth@gmail.com
    # Email details
    sender_email_id = "canvapro.lushanth@gmail.com"
    receiver = session.get('usermail')
    name = session.get('username')
    recipient_email = receiver
    
    subject = "Skin Guard - Skin cancer diagnosis report"
    result = 'Skin cancer not found' if prediction == 'Benign' else 'Skin cancer found'
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Message content
    body = f"Dear {name},\n\nYou are receiving this mail from skin guard AI based skin care diagnosis site.\nA The given image sample has {result} and it was tested on : {current_datetime}.\n\nWith regards,\nTeam Skinguard"
    
    # Create a MIMEMultipart object
    msg = MIMEMultipart()
    msg['From'] = sender_email_id
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # Attach image
    imgpath = 'Static/input/' + filename
    with open(imgpath, 'rb') as image_file:
        image_data = image_file.read()
        image = MIMEImage(image_data, name='cancersample.jpg')
        msg.attach(image)
    
    # Attach text
    text = MIMEText(body, 'plain')
    msg.attach(text)

    # Send the email
    s.sendmail(sender_email_id, recipient_email, msg.as_string())
    s.quit()
    
if __name__ == '__main__':
    app.run(debug=True)