import math
from flask import Flask, render_template, request
import pandas as pd
import requests
import http.client
import os
import json as JSON
import queue
import threading
import time
import boto3
import socket
from io import StringIO

import matplotlib.pyplot as plt

mov_time = 50
count = 1000

queue = queue.Queue()

def RoundFraction(x,y):
    return x if x % y == 0 else x + y - x % y

class ThreadUrl(threading.Thread):
    def __init__(self,queue,task_id,max_shots,report_rate,starting_point,service):
        threading.Thread.__init__(self)
        self.queue = queue
        self.task_id = task_id
        self.data = None
        self.max_shot = int(max_shots)
        self.report_rate = int(report_rate)
        self.starting_point = int(starting_point)
        self.service = service

    def run(self):
        # while True:
        count = self.queue.get()
        try:
            print("Service: "+  self.service)
            if self.service == 'Lambda':
                c = http.client.HTTPSConnection("AWS LAMBDA URL")
                json = '{ "S": ' + str(self.max_shot) + ',  "Q": ' + str(self.report_rate) + ',"start": ' + str(
                    self.starting_point) + '}'
                c.request("POST", "/default/FUNCTION", json)
                response = c.getresponse()
                self.data = response.read()

            if self.service == 'EC2':
                DNS = "IPv4 address /FUNCTION?S="+str(self.max_shot) +"&Q="+str(self.report_rate)+"&start="+str(self.starting_point)
                r = requests.post(DNS, verify=False)
                result_data = JSON.loads(r.text)
                data = {'random_list': result_data }
                self.data = JSON.dumps(data)

        except:
            print("Fail to open")

        self.queue.task_done()

def parallel_run(max_shots,report_rate,runs,service):
    threads = []
    # if service == "EC2":
    #     start_EC2()
    diff = 0
    partition = int(max_shots/runs)
    ten_percent =  partition * 0.1
    if (report_rate < ten_percent ):
        diff = int(ten_percent)
        print('diff is 10 per cent :',diff)
    else:
        diff = report_rate
        print('diff is report rate :',diff)

    starting_point = 1
    shots = partition

    for i in range (0,runs):
        if i == 0:
            shots = partition + diff

        elif i == runs-1:
            shots = max_shots

        else:
            shots = shots + partition

        # if i == runs-1:
        #     shots = partition - diff
        print("shots:",RoundFraction(shots,report_rate)," report rate: ",report_rate," starting point: ",RoundFraction(starting_point,report_rate)+1," count", shots-starting_point)

        t = ThreadUrl(queue,i,RoundFraction(shots,report_rate),report_rate,RoundFraction(starting_point,report_rate)+1,service)
        threads.append(t)
        t.setDaemon(True)
        t.start()

        starting_point =  shots + 1


    for x in range(0,runs):
        queue.put(count)

    queue.join()
    ids = [t.task_id for t in threads]
    results = [t.data for t in threads]

    long_result = []
    task_id = []
    for i,result in  enumerate(results):
        str_result_data = JSON.loads(result)
        if service == "Lambda":
            result_data = JSON.loads(str_result_data)
        else:
            result_data = str_result_data
        long_result = long_result + result_data["random_list"]
        for num in range(0,len(result_data["random_list"])):
            task_id.append(ids[i]+1)
        # print("task id: ", ids[i],result_data["random_list"].__len__(), result_data["random_list"])

    estimated_values = []
    Total_shots = []
    In_Circle = []
    for value in long_result:
        Total_shots.append(value[1])
        In_Circle.append(value[0])
        estimated_value = (value[0]/value[1])*4
        estimated_values.append(estimated_value)

    data = {'task_id':task_id,'In_Circle': In_Circle ,'Total_shots' : Total_shots,'estimated_values': estimated_values}
    df = pd.DataFrame(data,columns=['task_id','In_Circle','Total_shots','estimated_values'])

    if service == "EC2":
        stop_EC2()
    return  df

def start_EC2():
    retries = 10
    retry_delay = 10
    retry_count = 0
    region = "REGION"
    Instance = "INSTANCE_ID"
    ec2 = boto3.resource("ec2", region_name=region, aws_access_key_id='ACCESS_KEY',
                         aws_secret_access_key='SECRET_KEY')
    instance = ec2.Instance(id=Instance)
    # instance.stop()
    # instance.wait_until_stopped()

    print("Start Instance")
    instance.start()

    instance.wait_until_running()
    print("instance started")
    while retry_count <= retries:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((instance.public_ip_address, 22))
        if result == 0:
            print("Instance is UP, the IP address is:  ", instance.public_ip_address)
            break
        else:
            print("instance is still down retrying . . . ")
            time.sleep(retry_delay)

def stop_EC2():
    Instance = "INSTANCE_ID"
    region = "REGION"
    ec2 = boto3.resource("ec2", region_name=region, aws_access_key_id='ACCESS_KEY',
                         aws_secret_access_key='SECRET_KEY')

    instance = ec2.Instance(id=Instance)
    #
    print("Stop Instance")
    instance.stop()

app = Flask(__name__)

def doRender(tname, values={}):
    if not os.path.isfile( os.path.join(os.getcwd(), 'templates/'+tname) ): #No such file
        return render_template('index.html')
    return render_template(tname, **values)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def mainPage(path):
    return doRender(path)

@app.route('/piestimation', methods=['POST'])
def PIHandler():
    if request.method == 'POST':

        S = int(request.form.get('key1'))
        Q = int(request.form.get('period'))
        R = int(request.form.get('R'))
        service = request.form.get('service')

        start = time.time()
        df = parallel_run(S,Q,R,service)
        estimated_values = df['estimated_values'].values.tolist()
        In_Circle = df['In_Circle'].values.tolist()
        Total_shots = df['Total_shots'].values.tolist()
        task_id = df['task_id'].values.tolist()

        # print(estimated_values)
        pi_value = math.pi

        FinalValue = (df['In_Circle'].sum()/df['Total_shots'].sum())*4
        ElaspedTime = time.time() - start
        print("Elasped Time: %s", ElaspedTime)

        history = {'ElaspedTime':[ElaspedTime],'S':[S],'Q':[Q],'R':[R],'service':[service],'estimated_value':[FinalValue]}
        his_df = pd.DataFrame(history, columns=['ElaspedTime','S','Q', 'R','service', 'estimated_value'])

        s3 = boto3.resource("s3", region_name="us-east-1", aws_access_key_id='ACCESS KEY',
                            aws_secret_access_key='SECRET KEY')

        obj = s3.Object('pivalueslog', 's3_df.csv')
        body = obj.get()['Body'].read()
        str_body = body.decode("utf-8")
        s3_df = pd.read_csv(StringIO(str_body))

        print(s3_df.iloc[:,1:7])
        #
        s3_df = pd.concat([s3_df.iloc[:,1:7],his_df])

        csv_buffer = StringIO()
        s3_df.to_csv(csv_buffer)
        # his_df.to_csv(csv_buffer)
        s3.Object('pivalueslog', 's3_df.csv').put(Body=csv_buffer.getvalue())


        return doRender('PiEstimation.html', {'note': estimated_values,'task_id':task_id,'In_Circle':In_Circle,'Total_shots':Total_shots,
                                              'pi_value': pi_value,'FinalValue':FinalValue,'S':S,'Q':Q,'R':R,'service':service })
        # return doRender('PiEstimation.html', {'note': vals,'Name':MyNameIs, 'MoveAvg':data['mov'], 'mov_time':mov_time, 'VAR': var_str_data[1],'signal_price':signal_price})

if __name__ == '__main__':
    # Entry point for running on the local machine
    # On GAE, endpoints (e.g. /) would be called.
    # Called as: gunicorn -b :$PORT index:app,
    # host is localhost; port is 8080; this file is index (.py)
    app.run(host='127.0.0.1', port=8080, threaded=True)