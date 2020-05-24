from operator import add

from flask import Flask, render_template, request
import pandas as pd
import numpy as np
import requests
import http.client
import io
import os
import logging
import sys
import json as JSON

url = "https://natchstocks.s3.amazonaws.com/AAPL.csv"
s = requests.get(url).content
mov_time = 50


app = Flask(__name__)

def doRender(tname, values={}):
	if not os.path.isfile( os.path.join(os.getcwd(), 'templates/'+tname) ): #No such file
		return render_template('index.html')
	return render_template(tname, **values)

# @app.route("/table")
# def home_func():
# 	MyNameIs = "AAPL"
# 	# mov_time = 50
# 	data = pd.read_csv(io.StringIO(s.decode('utf-8')))
# 	df = pd.DataFrame(data)
# 	MoveAvg = []
# 	for i in range(0, df.shape[0]):
# 		if (i >= mov_time):
# 			Total = 0;
# 			for	j in range(mov_time,-1,-1):
# 				Total = Total + df.iloc[i - j, 4]
# 			MoveAvg.append(Total/mov_time)
# 		# print(Total/20, file=sys.stderr)
# 	return render_template("home.html", Name = MyNameIs, MoveAvg = MoveAvg, mov_time = mov_time)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def mainPage(path):
	return doRender(path)

# Defines a POST supporting calculate route
@app.route('/calculate', methods=['POST'])
def calculateHandler():
	if request.method == 'POST':
		l = request.form.get('labour')
		c = request.form.get('conservative')

		if l == '' or c == '':
			return doRender('index.html',
					{'note': 'Please specify a number for each group!'})
		else:
			total = float(l) + float(c)
			lP = int(float(l)/total*100)
			cP = int(float(c)/total*100)
			return doRender('chart.html', {'data': str(lP) + ',' + str(cP)})
	return 'Should not ever get here'

@app.route('/random', methods=['POST'])
def RandomHandler():
        import http.client
        if request.method == 'POST':
                mov_time = request.form.get('key1')
                c = http.client.HTTPSConnection("qfbqvub8ad.execute-api.us-east-1.amazonaws.com")
                json= '{ "key1": "'+mov_time+'"}'
                c.request("POST", "/default/myTestFunction", json)
                response = c.getresponse()
                data = response.read()
                return doRender( 'index.html',{'note': data} )

@app.route('/AAPL', methods=['POST'])
def AAPLHandler():
	# mov_time = 50
	if request.method == 'POST':
		mov_time = request.form.get('key1')
		MyNameIs = request.form.get('stocks_name')
		c = http.client.HTTPSConnection("sjdrpxdtq6.execute-api.us-east-1.amazonaws.com")
		json = '{ "mov_time_window":"' + mov_time + '" , "stock_name":"'+MyNameIs+'"}'
		c.request("POST", "/default/movCalculation", json)
		response = c.getresponse()
		str_data = response.read()
		data = JSON.loads(str_data)
		data =  JSON.loads(data)
		Signal = data["signal"]
		vals = [Signal[i][1] for i in range(len(Signal))]
		signal_name = [Signal[i][0] for i in range(len(Signal))]
		signal_price = [Signal[i][2] for i in range(len(Signal))]

		s = request.form.get('s')
		period = request.form.get('period')
		R = int(request.form.get('R'))
		sub_s = int(int(s)/R)
		var_c = [http.client.HTTPSConnection("1q7b50scs0.execute-api.us-east-1.amazonaws.com") for i in range (0,R)]
		var_c.append(http.client.HTTPSConnection("1q7b50scs0.execute-api.us-east-1.amazonaws.com"))
		var_dict = { "S": sub_s, "var_period": period,"stock_name": MyNameIs,"pos": vals,"signal_name":signal_name}
		var_json = JSON.dumps(var_dict)

		for r in range (0,R):
			var_c[r].request("POST", "/default/varCalculation", var_json)

		var_list = []
		for r in range (0,R):
			res = (var_c[r].getresponse())
			var_str_data = res.read()
			var_data = JSON.loads(var_str_data)
			var_data = JSON.loads(var_data)
			if(len(var_list)== 0):
				var_list = (var_data['var95'])
			else:
				var_list = list(map(add,var_list,var_data['var95']))

		avg_var = [i/R for i in var_list]
		profit_loss = []
		for i in range (0,len(vals)):
			if(avg_var[i-1] > 0):
				if( signal_name[i] == "Sell" ):
					profit_loss.append((signal_price[i] - signal_price[i-1])*1000)
				if( signal_name[i] == "Buy" ):
					profit_loss.append((signal_price[i-1] - signal_price[i])*1000)

			else:
				profit_loss.append(0)

		return doRender('AAPL.html', {'note': vals,'Name':MyNameIs, 'MoveAvg':data['mov'], 'mov_time':mov_time, 'VAR': avg_var,
									  'signal_price':signal_price,'signal_name':signal_name,'profit_loss': profit_loss})
		# return doRender('AAPL.html', {'note': vals,'Name':MyNameIs, 'MoveAvg':data['mov'], 'mov_time':mov_time, 'VAR': var_str_data[1],'signal_price':signal_price})

app.run(threaded=True)

if __name__ == '__main__':
    # Entry point for running on the local machine
    # On GAE, endpoints (e.g. /) would be called.
    # Called as: gunicorn -b :$PORT index:app,
    # host is localhost; port is 8080; this file is index (.py)
    app.run(host='127.0.0.1', port=8080, threaded=True)