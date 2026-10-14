from django.shortcuts import render

from django.contrib import messages
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
import pandas as pd
try:
    import matplotlib
    # Use a non-GUI backend to avoid tkinter/thread issues under Django's reloader.
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None

import numpy as np
import time

from .models import Register as RegisterModel

global username, unique_df

def _project_path(*parts):
    if os.environ.get('VERCEL'):
        import shutil
        target = os.path.join('/tmp', *parts)
        orig = os.path.join(settings.BASE_DIR, *parts)
        if not os.path.exists(target) and os.path.exists(orig):
            shutil.copy2(orig, target)
        return target
    return os.path.join(settings.BASE_DIR, *parts)

def ViewVotersAction(request):
    if request.method == 'POST':
        voter_id = str(request.POST.get('t1', '')).strip()
        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
        voter_series = dataset['VoterId'].astype(str).str.strip().str.upper()
        search_data = dataset.loc[voter_series == voter_id.upper()]
        output = f"Voter ID '{voter_id}' doesn't exist"
        if len(search_data) > 0:
            output = '<table border=1 align=center width=100%><tr><th><font size="3" color="black">Name</th><th><font size="3" color="black">Father/Husband</th><th><font size="3" color="black">Age</th><th><font size="3" color="black">Gender</th><th><font size="3" color="black">Voter ID</th><th><font size="3" color="black">Aadhar No</th></tr>'
            search_data = search_data.values
            for i in range(len(search_data)):
                output += '<tr>'
                output += '<td><font size="3" color="black">' + str(search_data[i, 0]) + '</td>'
                output += '<td><font size="3" color="black">' + str(search_data[i, 1]) + '</td>'
                output += '<td><font size="3" color="black">' + str(search_data[i, 2]) + '</td>'
                output += '<td><font size="3" color="black">' + str(search_data[i, 3]) + '</td>'
                output += '<td><font size="3" color="black">' + str(search_data[i, 4]) + '</td>'
                output += '<td><font size="3" color="black">' + str(search_data[i, 5]) + '</td></tr>'
            output += '</table>'
        context = {'data': output}
        return render(request, 'ViewResult.html', context)
    return render(request, 'ViewVoters.html', {})
            
def Download(request):
    name = "unique.xlsx"
    with open(_project_path(name), mode="rb") as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=' + name
    return response 

def RemoveDuplicate(request):
    global unique_df
    dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
    total_records = dataset.shape[0]

    # Resolve column names dynamically
    father_col = 'Father_Husband' if 'Father_Husband' in dataset.columns else ('Father/Husband' if 'Father/Husband' in dataset.columns else '')
    voter_col = 'VoterId' if 'VoterId' in dataset.columns else ('Voter ID' if 'Voter ID' in dataset.columns else '')
    aadhar_col = 'Aadhar no' if 'Aadhar no' in dataset.columns else ('Aadhar' if 'Aadhar' in dataset.columns else '')

    # Normalized fields for duplicate detection
    voter_norm = dataset[voter_col].fillna('').astype(str).str.strip().str.upper() if voter_col else pd.Series([''] * total_records)
    voter_norm = voter_norm.replace({'NAN': '', 'NONE': ''})

    aadhar_norm = dataset[aadhar_col].fillna('').astype(str).str.strip().str.replace('-', '').str.replace(' ', '') if aadhar_col else pd.Series([''] * total_records)
    aadhar_norm = aadhar_norm.replace({'NAN': '', 'NONE': ''})

    name_norm = dataset['Name'].fillna('').astype(str).str.strip().str.upper() if 'Name' in dataset.columns else pd.Series([''] * total_records)
    father_norm = dataset[father_col].fillna('').astype(str).str.strip().str.upper() if father_col else pd.Series([''] * total_records)

    seen_voters = set()
    seen_aadhars = set()
    seen_persons = set()

    indices_to_keep = []
    duplicate_indices = []

    for idx in range(total_records):
        v = voter_norm.iloc[idx]
        a = aadhar_norm.iloc[idx]
        n = name_norm.iloc[idx]
        f = father_norm.iloc[idx]
        p = f"{n}___{f}" if (n and f) else ''

        is_dup = False
        if v and v in seen_voters:
            is_dup = True
        elif a and a in seen_aadhars:
            is_dup = True
        elif p and p in seen_persons:
            is_dup = True

        if is_dup:
            duplicate_indices.append(dataset.index[idx])
        else:
            indices_to_keep.append(dataset.index[idx])
            if v:
                seen_voters.add(v)
            if a:
                seen_aadhars.add(a)
            if p:
                seen_persons.add(p)

    unique_df = dataset.loc[indices_to_keep].copy()
    unique_records = unique_df.shape[0]
    duplicate_count = len(duplicate_indices)

    # Save to BOTH DataVoter.xlsx and unique.xlsx
    unique_df.to_excel(_project_path("DataVoter.xlsx"), index=False)
    unique_df.to_excel(_project_path("unique.xlsx"), index=False)

    output = (
        f"<b>De-Duplication Analysis Result</b><br/><br/>"
        f"Total records before Deduplication : {total_records}<br/>"
        f"Duplicate votes removed (matching Voter ID or Aadhar) : {duplicate_count}<br/>"
        f"Total records after Deduplication : {unique_records}<br/><br/>"
        f"<font color='green'><b>Saved cleaned voter records to DataVoter.xlsx and unique.xlsx successfully!</b></font>"
    )
    context = {'data': output}
    return render(request, 'UserScreen.html', context)

def AddNewVoter(request):
    return render(request, 'AddNewVoter.html', {})

def AddNewVoterAction(request):
    if request.method == 'POST':
        name = request.POST.get('t1', False)
        father = request.POST.get('t2', False)
        age = request.POST.get('t3', False)
        gender = request.POST.get('t4', False)
        voter = request.POST.get('t5', False)
        aadhar = request.POST.get('t6', False)
        print("==========="+father);
        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
        new_rec = {'Name': name, 'Father_Husband': father, 'Age': age, 'Gender': gender, 'VoterId': voter, 'Aadhar no': aadhar}
        dataset = pd.concat([dataset, pd.DataFrame([new_rec])], ignore_index=True)
        dataset.to_excel(_project_path('DataVoter.xlsx'), index=False)
        context= {'data':'New record added to existing DataVoter.xlsx<br/>You can open & verify that xlsx file'}
        return render(request, 'AddNewVoter.html', context)
    return render(request, 'AddNewVoter.html', {})

def ViewVoters(request):
    return render(request, 'ViewVoters.html', {})

def index(request):
    return render(request, 'index.html', {})

def Login(request):
    return render(request, 'Login.html', {})

def Register(request):
    return render(request, 'Register.html', {})   

def Signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        contact = request.POST.get('contact', False)
        email = request.POST.get('email', False)
        address = request.POST.get('address', False)
        if RegisterModel.objects.filter(username=username).exists():
            context = {'data':'Username already exists'}
            return render(request, 'Register.html', context)
        else:
            RegisterModel.objects.create(username=username, password=password, contact=contact, email=email, address=address)
            context = {'data':'Signup Process Completed'}
            return render(request, 'Register.html', context)
    return render(request, 'Register.html') 
        
def UserLogin(request):
    if request.method == 'POST':
        global username
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if username and password and RegisterModel.objects.filter(username=username, password=password).exists():
            context = {'data':'welcome '+str(username)}
            return render(request, 'UserScreen.html', context)
        else:
            context = {'data':'Invalid login details'}
            return render(request, 'Login.html', context)
    return render(request, 'Login.html')        
        
        
