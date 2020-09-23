from flask import Flask, render_template, request, make_response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

import os
import random
import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "users.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file

db = SQLAlchemy(app)
data = {}
respons = requests.get("https://api.covid19api.com/summary").json()
countries = {}

class User(db.Model):
	userFullName = db.Column(db.String(255), nullable=False)
	userName = db.Column(db.String(50), unique=True, nullable=False, primary_key = True)
	userPassword = db.Column(db.String(1025), nullable=False)

	def __repr__(self):
		return "<Full Name: {}>".format(self.userFullName) + "\n<userName: {}".format(self.userName)

	def find_by_username(username):
		return User.query.filter_by(userName = username).first()	

@app.route("/")
def home(setCookie = False, userName = ""):
	getResponse()
	return render_template("index.html")

@app.route("/statistics")
def statistics():
	for i in respons['Countries']:
		countries[i['CountryCode']] = i['Country']
	return render_template("statistics.html", res = respons, global_img_url = 'global.png', countries = respons['Countries'])

@app.route("/statistics/<country_name>/<country_code>", methods=['POST', 'GET'])
@app.route("/statistics/<country_name>/<country_code>/<past_days>", methods=['POST', 'GET'])
def statistics_code(country_name, country_code, past_days = 30):
	userloggedin = request.cookies.get('userloggedin')
	LoggedInKey = request.cookies.get('LoggedInUser')

	if request.method == "GET":
		if userloggedin and LoggedInKey:
			if check_password_hash(request.cookies.get('LoggedInUser'), request.cookies.get('userloggedin') + "UsRL08g3d" + "V3R1fie4"):
				RemoveData()
				count, img_urls = PlotTimeline(country_code, past_days)
				return render_template("statisticscountry.html", country_name=country_name, country_code=country_code, past_days=past_days, country_data = count, img_urls = img_urls)				
			else:
				return redirect(url_for("statistics", res = respons, global_img_url = 'global.png', countries = respons['Countries']))	
		else:
			return redirect(url_for("statistics", res = respons, global_img_url = 'global.png', countries = respons['Countries']))
	elif request.method == "POST":
		RemoveData()
		past_days = request.form['past_day']
		count, img_urls = PlotTimeline(country_code, past_days)
		return render_template("statisticscountry.html", country_name=country_name, country_code=country_code, past_days=past_days, country_data = count, img_urls=img_urls)				

@app.route("/signup", methods=['POST', 'GET'])
def signup():
	if request.method == "POST":
		userpass = generate_password_hash(request.form["userpassword"])
		
		user = User(userFullName = request.form["fullname"], userName = request.form["username"], userPassword = userpass)
		try:
			db.session.add(user)
		except Exception as e:
			print(e)

		db.session.commit()

		res = make_response(redirect("/login", code=302))
		res.set_cookie('ReqLogin', 'yes', max_age = 3)
		return res
	elif request.method == "GET":
		return render_template("signup.html")

@app.route('/login', methods = ['POST', 'GET'])
def login():
	if request.method == "POST":
		username = request.form['username']
		userpass = request.form['userpassword']

		user = User.find_by_username(username)

		if user and check_password_hash(user.userPassword, userpass):
			res = make_response(redirect("/"))
			res.set_cookie('userloggedin', username, max_age = 60*10)
			res.set_cookie('LoggedInUser', generate_password_hash(username + "UsRL08g3d" + "V3R1fie4"), max_age = 60*10)
			return res		
		else:
			return render_template("login.html", Message = "Wrong")

	elif request.method == "GET":
		userLogged = request.cookies.get('userloggedin')
		message = request.cookies.get('ReqLogin')
		if userLogged:
			return make_response(redirect("/"))
		else:
			return render_template("login.html", Message = message)

@app.route('/logout')
def logout():
	res = make_response(redirect("/"))
	res.set_cookie('userloggedin', '', max_age=0)
	return res

#Helper Functions
def getResponse():
	if not respons:
		RemoveData()
		global_ = []
		global_cases = []
		for i in respons['Global']:
			global_.append(i)
			global_cases.append(int(respons['Global'][i]) / 100000)

		fig = plt.figure(figsize = (10, 5)) 
		plt.barh(global_, global_cases)
		plt.title("Global Stats (in thousands)")
		for index, value in enumerate(global_cases):
			plt.text(value, index, str(value))
		plt.savefig('static/global.png',dpi=1000)

def RemoveData():
	for r,d,f in os.walk('static/'):
		for file in f:
			if ".png" in file and "global" not in file:
				print(file)
				os.remove('static/'+file)

def getCountryData(country_code):
	count = [0 for i in range(5)]
	if country_code not in data.keys():
		respons = requests.get("https://thevirustracker.com/free-api?countryTimeline="+country_code).json()
		data[country_code] = []
		for i in respons['timelineitems'][0]:
			if i != "stat":
				data[country_code].append([i, respons['timelineitems'][0][i]['new_daily_cases'], respons['timelineitems'][0][i]['new_daily_deaths'], respons['timelineitems'][0][i]['total_cases'], respons['timelineitems'][0][i]['total_recoveries'], respons['timelineitems'][0][i]['total_deaths']])
				count[0] += respons['timelineitems'][0][i]['new_daily_cases']
				count[1] += respons['timelineitems'][0][i]['new_daily_deaths']
				count[2] += respons['timelineitems'][0][i]['total_cases']
				count[3] += respons['timelineitems'][0][i]['total_recoveries']
				count[4] += respons['timelineitems'][0][i]['total_deaths']
		return count
	else:
		for i in data[country_code]:
			count[0] += i[0]
			count[1] += i[1]
			count[2] += i[2]
			count[3] += i[3]
			count[4] += i[4]
		return count

def PlotTimeline(country_code, past_days = 30):	
	count = getCountryData(country_code)
	past_days = int(past_days)
	df = pd.DataFrame(data[country_code], columns=['date', 'newCases', 'newDeaths', 'totalCases', 'totalRecoveries', 'totalDeaths'])
	
	randname = list(map(str, random.sample(range(10, 10202), 5)))

	fig = plt.figure(figsize = (10, 5))
	plt.plot_date(df['date'].tail(past_days), df['newCases'].tail(past_days), linestyle='solid')
	plt.gcf().autofmt_xdate()
	plt.title('New Cases Past ' + str(past_days) + " Days")
	plt.savefig("static/"+ str(randname[0]) +country_code+'.png', dpi=1000)

	#New Deaths
	fig = plt.figure(figsize = (10, 5))
	plt.plot_date(df['date'].tail(past_days), df['newDeaths'].tail(past_days), linestyle='solid')
	plt.gcf().autofmt_xdate()
	plt.title('Death Rate Past ' + str(past_days) + " Days")
	plt.savefig('static/'+str(randname[1])+country_code+'.png', dpi=1000)

	#Total Cases
	fig = plt.figure(figsize = (10, 5))
	plt.plot_date(df['date'].tail(past_days), df['totalCases'].tail(past_days), linestyle='solid')
	plt.gcf().autofmt_xdate()
	plt.title('Total Cases Past ' + str(past_days) + " Days")
	plt.savefig('static/'+str(randname[2])+country_code+'.png', dpi=1000)

	#Total Recoveries
	fig = plt.figure(figsize = (10, 5))
	plt.plot_date(df['date'].tail(past_days), df['totalRecoveries'].tail(past_days), linestyle='solid')
	plt.gcf().autofmt_xdate()
	plt.title('Total Recoveries Past ' + str(past_days) + " Days")
	plt.savefig('static/'+str(randname[3])+country_code+'.png', dpi=1000)

	#Total Deaths
	fig = plt.figure(figsize = (10, 5))
	plt.plot_date(df['date'].tail(past_days), df['totalDeaths'].tail(past_days), linestyle='solid')
	plt.gcf().autofmt_xdate()
	plt.title('Total Deaths Past ' + str(past_days) + " Days")
	plt.savefig('static/'+str(randname[4])+country_code+'.png', dpi=1000)

	return count, randname

if __name__ == "__main__":
    app.run(debug=True)