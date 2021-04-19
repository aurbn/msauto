#!/usr/bin/env python3.6
import argparse
import re
import subprocess
from datetime import datetime
import calendar
import locale
from pprint import pprint
import httplib2
import apiclient
import requests
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from time import sleep
import os
from ilock import ILock
import threading
from tempfile import NamedTemporaryFile
from shutil import move
import contextlib
import functools


from config import *

PROJECT_HEADER = 'Project_title'
SAMPLE_HEADER = 'Sample_ID'
TYPE_HEADER = 'Proteolysis_protocol'
STATUS_HEADER = 'Status'

POOL_TIME = 1


LETTERS='ABCDEFGHIJKLNMOPQRSTUVWXYZ'
g_service = None

LOCK_IMPORT = 'LOCK_IMPORT'
LOCK_CONVERT = 'LOCK_CONVERT'
LOCK_TANDEM = 'LOCK_TANDEM'
LOCK_MASCOT = 'LOCK_MASCOT'


tandem_stub='''<?xml version="1.0"?>
<bioml>
	<note type="input" label="list path, default parameters">{defaults_path}</note>
	<note type="input" label="list path, taxonomy information">{taxonomy_path}</note>
	<note type="input" label="protein, taxon">{taxon}</note>
	<note type="input" label="spectrum, path">{mgf_file}</note>
	<note type="input" label="output, path">{output_path}</note>
</bioml>
'''

def locked(lockname):
    '''Run function locked system-wide'''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ILock(lockname):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_g_service():
    global g_service

    if g_service:
        return g_service

    locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
    CREDENTIALS_FILE = '/home/urban/git/msauto/key.json'
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                                   ['https://www.googleapis.com/auth/spreadsheets',
                                                                    'https://www.googleapis.com/auth/drive'])
    httpAuth = credentials.authorize(httplib2.Http())
    service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)

    g_service = service
    return service


def get_current_table(uploaded=True):
    service = get_g_service()
    range_name = 'List!A:G'
    table = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=range_name).execute()
    colnames = table['values'][0]
    colnames = list(map(lambda s: s.replace(' ', '_'), colnames))
    d = pd.DataFrame( table['values'][1:], columns=colnames)
    if uploaded:
        d = d[d['Uploaded']=='TRUE']
    return d


def set_status(psample, status):
    service = get_g_service()
    range_name = 'List!A:G'
    table = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=range_name).execute()
    colnames = table['values'][0]
    proj_cn = None
    sample_cn = None
    status_cn = None
    target_row = None
    for i, cn in enumerate(colnames):
        if cn == PROJECT_HEADER:
            proj_cn = i
        elif cn == SAMPLE_HEADER:
            sample_cn = i
        elif cn == STATUS_HEADER:
            status_cn = i
    assert not(proj_cn is None and sample_cn is None and status_cn is None)
    for i, col in enumerate(table['values']):
        if col[proj_cn] == psample[0] and col[sample_cn] == psample[1]:
            target_row = i
            break
    assert target_row is not None
    range = f'List!{LETTERS[status_cn]}{target_row+1}'

    service = get_g_service()
    body = {
        'range': range,
        'values': [[status]],
        'majorDimension': 'ROWS',
    }
    request = service.spreadsheets().values().update(spreadsheetId=spreadsheetId, range=range,
                                                     valueInputOption='RAW', body=body)
    response = request.execute()


def read_list(filename, lockname = None):
    result = []
    mgr = ILock if lockname else contextlib.suppress  # Kinda null manager, nullcontext for 3.7
    with mgr(lockname):
        if not os.path.exists(filename):
            return result
        with open(filename, "r") as f:
            for l in f.readlines():
                if l:
                    sp = tuple(map(lambda x: x.strip(), l.split('\t')))
                    result.append(sp)
    return result


def append_list(filename, pslist, lockname=None):
    mgr = ILock if lockname else contextlib.suppress  # Kinda null manager, nullcontext for 3.7
    with mgr(lockname):
        mode = "a" if os.path.exists(filename) else "w"
        with open(filename, mode) as f:
            for project, sample in pslist:
                f.writelines(f"{project}\t{sample}\n")


def get_proj_root(project):
    return os.path.join(DATA_ROOT, project)


def get_proj_raw_root(project):
    return os.path.join(RAW_ROOT, project)


def log(project, str):
    now = datetime.now().strftime("[%d/%m/%Y  %H:%M:%S]\t")
    root = get_proj_root(project)
    fname = os.path.join(root, LOGNAME)
    mode = "a" if os.path.exists(fname) else "w"
    with open(fname, mode) as f:
        f.writelines(now+str)
        f.writelines('\n')


def get_sample_raw_path(psample):
    return os.path.join(get_proj_raw_root(psample[0]), psample[1]+".raw")


def get_sample_mgf_path(psample):
    return os.path.join(get_proj_root(psample[0]), psample[1]+".mgf")


def get_sample_tandem_path(psample):
    return os.path.join(get_proj_root(psample[0]), psample[1]+".tandem.xml")


def get_sample_mascot_path(psample):
    return os.path.join(get_proj_root(psample[0]), psample[1]+".dat")




def remove_first_line(file_path):
    with open(file_path, 'r') as f_in:
        with NamedTemporaryFile(mode='w', delete=False) as f_out:
            temp_path = f_out.name
            next(f_in)
            for line in f_in:
                f_out.write(line)
    os.remove(file_path)
    move(temp_path, file_path)


@locked(LOCK_IMPORT)
def run_gimport(args):
    gdata = get_current_table()

    old_samples = read_list(DB_IMPORTED_FILE, DB_IMPORTED_LOCK)
    samples = []
    for k, row in gdata.iterrows():
        project = row[PROJECT_HEADER]
        sample = row[SAMPLE_HEADER]

        if os.path.exists(get_sample_raw_path((project, sample))):
            samples.append((project, sample))

    # remove  already imported samples
    samples = list(filter(lambda x: x not in old_samples, samples))
    append_list(DB_IMPORTED_FILE, samples, DB_IMPORTED_LOCK)

    conv_queue = []
    conv_old = read_list(DB_CONV_FILE, DB_CONV_LOCK)

    for project, sample in samples:
        root = get_proj_root(project)
        if not os.path.exists(root):
            os.mkdir(root)
            log(project, f"Created root for project {project}")
        if (project, sample) not in conv_old:
            conv_queue.append((project, sample))
            set_status((project, sample), "Waiting for the analysis")
            log(project, f"Sample ID {sample} is waiting for the analysis")

    with ILock(DB_CONV_LOCK):
        with open(DB_CONV_FILE, "a") as f:
            for project, sample in conv_queue:
                f.writelines(f"{project}\t{sample}\n")

    # os.remove(LOCK_IMPORT)


@locked(LOCK_CONVERT)
def run_conversions(args):
    l = None
    with ILock(DB_CONV_LOCK):
        if os.path.exists(DB_CONV_FILE):
            with open(DB_CONV_FILE, "r") as f:
                l = f.readline()
            if l:
                remove_first_line(DB_CONV_FILE)
    if l:
        project, sample = map(lambda x: x.strip(), l.split('\t'))
        ps = (project, sample)
        rawfile = get_sample_raw_path(ps)
        log(project, f"Started converting {rawfile}")
        set_status(ps, 'Converting')
        process = subprocess.Popen(CONVERSION_CMD.format(infile = rawfile, outdir = get_proj_root(project)),
                                                         shell=True, stdout=subprocess.PIPE)
        process.wait()
        log(project, f'Converted {rawfile}')
        set_status(ps, 'Converted')
        append_list(DB_TANDEM_FILE, [(project, sample)], DB_TANDEM_LOCK)
        append_list(DB_MASCOT_FILE, [(project, sample)], DB_MASCOT_LOCK)


@locked(LOCK_TANDEM)
def run_tandem(args):
    l = None
    with ILock(DB_TANDEM_LOCK):
        if os.path.exists(DB_TANDEM_FILE):
            with open(DB_TANDEM_FILE, "r") as f:
                l = f.readline()
            if l:
                remove_first_line(DB_TANDEM_FILE)
    if l:
        project, sample = map(lambda x: x.strip(), l.split('\t'))
        psample = (project, sample)
        confpath = os.path.join(get_proj_root(project), sample+".tconf.xml")
        mgfpath = get_sample_mgf_path(psample)
        tandemconf = tandem_stub.format(defaults_path=TANDEM_DEFAULTS,
                                        taxonomy_path=TANDEM_TAXONOMY,
                                        mgf_file=mgfpath,
                                        output_path=get_sample_tandem_path(psample),
                                        taxon='human')
        with open(confpath, "w") as f:
            f.writelines(tandemconf)
        set_status(psample, "Identification running")
        log(project, "Starting X!Tandem: "+TANDEM_CMD.format(infile=confpath))
        process = subprocess.Popen(TANDEM_CMD.format(infile=confpath),
                               shell=True, stdout=subprocess.PIPE)
        process.wait()
        log(project, f"X!Tandem finished with {process.returncode}, {process.stdout}")
        set_status(psample, "Identification finished")


def get_default_mascot_pars(args):
    filename = MASCOT_DEFAULTS
    pars = {}
    with open(filename, "r") as f:
        for l in f.readlines():
            name, par = map(lambda x: x.strip(), l.split("="))
            pars[name] = par
    pars['FORMVER'] = '1.01'
    return pars


def mascot_login(mascot_cgi, user, password):
    postdict={}
    postdict['username'] = user
    postdict['password'] = password
    postdict['action'] = 'login'
    postdict['savecookie'] = '1'

    session = requests.Session()
    response = session.post(MASCOT_CGI+'/login.pl', data=postdict)

    return session


@locked(LOCK_MASCOT)
def run_mascot(args):
    l = None
    with ILock(DB_MASCOT_LOCK):
        if os.path.exists(DB_MASCOT_FILE):
            with open(DB_MASCOT_FILE, "r") as f:
                l = f.readline()
            if l:
                remove_first_line(DB_MASCOT_FILE)
    if not l:
        return

    project, sample = map(lambda x: x.strip(), l.split('\t'))
    psample = (project, sample)
    mgfpath = get_sample_mgf_path(psample)
    datpath = get_sample_mascot_path(psample)
    set_status(psample, "Identification running (m)")
    pars = get_default_mascot_pars(psample)
    pars['DB'] = 'UniProtKB-HS_TnD_17'
    #pars['USERNAME'] = 'admin'
    #pars['PASSWORD'] = 'Chieftec64'

    session = mascot_login(MASCOT_CGI, 'admin', 'Chieftec64')
    if session:
        log(project, f"Logged in {MASCOT_CGI}")

    pars1 = {}
    # pars1['MASCOT_SESSION'] = cookies['MASCOT_SESSION']
    # pars1['MASCOT_USERID'] = cookies['MASCOT_USERID']
    # pars1['MASCOT_USERNAME'] = cookies['MASCOT_USERNAME']
    sendurl = MASCOT_CGI + '/nph-mascot.exe?1'
    with open(mgfpath, 'rb') as f:
        response = session.post(sendurl, files={'FILE':f}, data=pars)
    log(project, "Mascot response was: " + response.content.decode())
    if response.ok:
        error_result = re.match('Sorry, your search could not be performed', response.content.decode())
        if error_result:
            log('Search failed')
        match = re.search(r'master_results\.pl\?file=.*data/(?P<date>\d+)/(?P<file>F\d+\.dat)',
                          response.content.decode())
        date, file = match.group('date'), match.group('file')

        mascot_xcgi = MASCOT_CGI.replace('cgi', 'x-cgi')
        get_url = mascot_xcgi + f'/ms-status.exe?Autorefresh=false&Show=RESULTFILE&DateDir={date}&ResJob={file}'
        log(project, f'Downloading file {get_url}')

        with session.get(get_url, stream=True) as r:
            r.raise_for_status()
            with open(datpath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        log(project, 'Downloaded')
        set_status(psample, 'Identification finished')

    else:
        log(project, "Bad response")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=lambda args: parser.print_help())
    subparsers = parser.add_subparsers(dest='subparser')
    gimport_parser = subparsers.add_parser('import')
    gimport_parser.set_defaults(func=run_gimport)

    convert_parser = subparsers.add_parser('convert')
    convert_parser.set_defaults(func=run_conversions)

    tandem_parser = subparsers.add_parser('tandem')
    tandem_parser.set_defaults(func=run_tandem)

    tandem_parser = subparsers.add_parser('mascot')
    tandem_parser.set_defaults(func=run_mascot)


    args = parser.parse_args()
    args.func(args)




    # https://docs.google.com/spreadsheets/d/1cjj6LeOC1WjvFuguSZsiu7rhUq8IUWjFD4arkK1g0-Q/edit?usp=sharing