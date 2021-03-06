import requests
import os
import time
import json
import shutil
import sys

# The Perfecto Continuous Quality Lab you work with
CQL_NAME = os.environ['LAB']

# The reporting Server address depends on the location of the lab. Please refer to the documentation at
# http://developers.perfectomobile.com/display/PD/Reporting#Reporting-ReportingserverAccessingthereports
# to find your relevant address
# For example the following is used for US:
REPORTING_SERVER_URL = 'https://' + CQL_NAME + '.app.perfectomobile.com'

# See http://developers.perfectomobile.com/display/PD/Using+the+Reporting+Public+API on how to obtain an Offline Token
# In this case the offline token is stored as a env variable
OFFLINE_TOKEN = os.environ['OFFLINE_TOKEN']

CQL_SERVER_URL = 'https://' + CQL_NAME + '.perfectomobile.com'


def retrieve_tests_executions():
    """
    Retrieve a list of test executions within the last month
    :return: JSON object contains the executions
    """
    api_url = REPORTING_SERVER_URL + '/export/api/v1/test-executions'

    # Optional parameters to be passed with our http request, In this example:
    # retrieve test executions of the past month (result may contain tests of multiple driver executions)
    current_time_millis = lambda: int(round(time.time() * 1000))
    payload = {
        'startExecutionTime[0]': current_time_millis() - (30 * 24 * 60 * 60 * 1000),
        'endExecutionTime[0]': current_time_millis(),
    }

    # creates http get request with the url, given parameters (payload) and header (for authentication)
    r = requests.get(api_url, params=payload, headers={'PERFECTO_AUTHORIZATION': OFFLINE_TOKEN})

    return r.content


def retrieve_test_commands(test_id):
    """
    retrieve commands of test with a given test id
    :param test_id: a test id
    :return: a JSON object contains the commands of the test with a given test id
    """
    api_url = REPORTING_SERVER_URL + "/export/api/v1/test-executions/" + test_id + "/commands"
    print "api_url " + api_url
    r = requests.get(api_url, headers={'PERFECTO_AUTHORIZATION': OFFLINE_TOKEN})
    return r.content


def download_execution_summary_report(driver_execution_id):
    """
    download execution report summary (pdf format)
    :param driver_execution_id: execution id
    """
    api_url = REPORTING_SERVER_URL + '/export/api/v1/test-executions/pdf'
    payload = {
        'externalId[0]': driver_execution_id
    }
    r = requests.get(api_url, params=payload, headers={'PERFECTO_AUTHORIZATION': OFFLINE_TOKEN}, stream=True)
    download_file_attachment(r, driver_execution_id + '.pdf')


def download_test_report(test_id):
    """
    download test report summary (pdf format)
    :param test_id: test id
    """
    api_url = REPORTING_SERVER_URL + "/export/api/v2/test-executions/pdf/task/"
    print "download_test_report api_url :" + api_url
    print "check if pdf is ready"
    task_status = ""
    count = 0;
    while task_status != "COMPLETE": #check if pdf is readt
        task = requests.post(api_url, headers={'PERFECTO_AUTHORIZATION': OFFLINE_TOKEN},
                             params={'testExecutionId': test_id}, stream=True).text
        task_data = json.loads(task)
        task_status = task_data['status']
        count = count + 1
        print "status is:" + task_status
        time.sleep(5)
        if count > 60: #exit if not ready after 5 minutes
            print "error: Didn't get a pdf after 5 minutes"
            sys.exit(1)

    api_url = task_data['url']
    r = requests.get(api_url, headers={'PERFECTO_AUTHORIZATION': OFFLINE_TOKEN}, stream=True)
    download_file_attachment(r, test_id + '.pdf')


def download_video(test_execution):
    """
    downloads a video for given test execution
    :param test_execution: execution JSON object
    """
    videos = test_execution['videos']
    if len(videos) > 0:
        video = videos[0]
        download_url = video['downloadUrl']  # retrieve the video download url
        video_format = '.' + video['format']  # set the video format
        test_id = test_execution['id']
        r = requests.get(download_url, stream=True)
        download_file_attachment(r, test_id + video_format)
    else:
        print('No videos were found for the given test execution...')


def download_attachments(test_execution):
    """
    downloads attachments for a given test execution
    :param test_execution: test execution JSON object
    """
    artifacts = test_execution['artifacts']
    if len(artifacts) > 0:
        for arti in artifacts:
            type = arti['type']
            if type == 'DEVICE_LOGS':
                test_id = test_execution['id']
                path = arti['path']
                r = requests.get(path, stream=True)
                download_file_attachment(r, test_id + '.zip')
    else:
        print('No artifacts found for the given test_execution')


def download_file_attachment(r, filename):
    """
    Downloads attachment as pdf file from request object
    :param r: request to handle
    :param filename: name for the pdf file
    """
    if r.status_code == 200:
        with open(filename, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
    else:
        raise Exception('Request status code is not valid: ' + str(r.status_code))


if __name__ == '__main__':
    # Retrieve a list of the test executions in your lab (as a json)
    executions = retrieve_tests_executions()

    # Loads JSON string into JSON object
    executions = json.loads(executions)
    #print executions
    resources = executions['resources']
    if len(resources) == 0:
        print('there are no test executions for that period of time')
    else:
        test_execution = resources[1]  # retrieve a test execution
        driver_execution_id = test_execution['externalId']  # retrieve the execution id
        test_id = test_execution['id']  # retrieve a single test id

        # retrieve the test commands
        test_commands = retrieve_test_commands(test_id)

        # download execution report in pdf format
        download_execution_summary_report(driver_execution_id)

        # downloads the test report in pdf format
        download_test_report(test_id)

        # downloads video
        download_video(test_execution)

        # Download attachments such as device logs, vitals or network files (relevant for Mobile tests only)
        download_attachments(test_execution)
