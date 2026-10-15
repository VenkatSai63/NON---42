from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
import os
import shutil
import pandas as pd
import numpy as np

from .models import Register as RegisterModel

global username, unique_df

def _project_path(*parts):
    if os.environ.get('VERCEL'):
        target = os.path.join('/tmp', *parts)
        orig = os.path.join(settings.BASE_DIR, *parts)
        if not os.path.exists(target) and os.path.exists(orig):
            shutil.copy2(orig, target)
        return target
    return os.path.join(settings.BASE_DIR, *parts)

def _find_duplicates(dataset):
    total = dataset.shape[0]
    father_col = 'Father_Husband' if 'Father_Husband' in dataset.columns else ('Father/Husband' if 'Father/Husband' in dataset.columns else '')
    voter_col = 'VoterId' if 'VoterId' in dataset.columns else ('Voter ID' if 'Voter ID' in dataset.columns else '')
    aadhar_col = 'Aadhar no' if 'Aadhar no' in dataset.columns else ('Aadhar' if 'Aadhar' in dataset.columns else '')

    seen_voters = set()
    seen_aadhars = set()
    seen_persons = set()

    indices_to_keep = []
    duplicate_indices = []

    for idx in range(total):
        row = dataset.iloc[idx]
        v = str(row.get(voter_col, '')).strip().upper() if voter_col else ''
        if v in ['NAN', 'NONE', 'NULL']:
            v = ''

        raw_a = str(row.get(aadhar_col, '')).strip().replace('-', '').replace(' ', '') if aadhar_col else ''
        if raw_a in ['NAN', 'NONE', 'NULL']:
            raw_a = ''

        n = str(row.get('Name', '')).strip().upper()
        f = str(row.get(father_col, '')).strip().upper() if father_col else ''
        p = f"{n}___{f}" if (n and f) else ''

        is_dup = False
        if v and v in seen_voters:
            is_dup = True
        elif raw_a and raw_a in seen_aadhars:
            is_dup = True
        elif p and p in seen_persons:
            is_dup = True

        if is_dup:
            duplicate_indices.append(idx)
        else:
            indices_to_keep.append(idx)
            if v: seen_voters.add(v)
            if raw_a: seen_aadhars.add(raw_a)
            if p: seen_persons.add(p)

    return indices_to_keep, duplicate_indices

def ViewVotersAction(request):
    if request.method == 'POST':
        voter_id = str(request.POST.get('t1', '')).strip().upper()
        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")

        voter_col = 'VoterId' if 'VoterId' in dataset.columns else ('Voter ID' if 'Voter ID' in dataset.columns else '')
        father_col = 'Father_Husband' if 'Father_Husband' in dataset.columns else ('Father/Husband' if 'Father/Husband' in dataset.columns else '')
        aadhar_col = 'Aadhar no' if 'Aadhar no' in dataset.columns else ('Aadhar' if 'Aadhar' in dataset.columns else '')

        voter_series = dataset[voter_col].fillna('').astype(str).str.strip().str.upper()
        search_data = dataset.loc[voter_series == voter_id]
        output = f"<font color='red'><b>Voter ID '{voter_id}' doesn't exist in records.</b></font>"
        if len(search_data) > 0:
            output = '<table border=1 align=center width=100%>'
            output += '<tr><th><font size="3" color="black">Name</th><th><font size="3" color="black">Father/Husband</th><th><font size="3" color="black">Age</th><th><font size="3" color="black">Gender</th><th><font size="3" color="black">Voter ID</th><th><font size="3" color="black">Aadhar No</th></tr>'
            for idx, row in search_data.iterrows():
                output += '<tr>'
                output += f'<td><font size="3" color="black">{row["Name"]}</td>'
                output += f'<td><font size="3" color="black">{row[father_col]}</td>'
                output += f'<td><font size="3" color="black">{row["Age"]}</td>'
                output += f'<td><font size="3" color="black">{row["Gender"]}</td>'
                output += f'<td><font size="3" color="black">{row[voter_col]}</td>'
                output += f'<td><font size="3" color="black">{row[aadhar_col]}</td></tr>'
            output += '</table>'
        context = {'data': output}
        return render(request, 'ViewResult.html', context)
    return render(request, 'ViewVoters.html', {})

def Download(request):
    name = "unique.xlsx"
    file_path = _project_path(name)
    if not os.path.exists(file_path):
        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
        keeps, _ = _find_duplicates(dataset)
        dataset.iloc[keeps].to_excel(file_path, index=False)
    with open(file_path, mode="rb") as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response 

def RemoveDuplicate(request):
    global unique_df
    dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
    total_records = dataset.shape[0]

    indices_to_keep, duplicate_indices = _find_duplicates(dataset)
    duplicate_count = len(duplicate_indices)

    unique_df = dataset.iloc[indices_to_keep].copy()
    unique_records = unique_df.shape[0]

    # Save cleaned data to DataVoter.xlsx & unique.xlsx
    unique_df.to_excel(_project_path("DataVoter.xlsx"), index=False)
    unique_df.to_excel(_project_path("unique.xlsx"), index=False)

    output = f"""
    <br/>
    <center>
    <h3><b>De-Duplication Analysis Result</b></h3><br/>
    <table align="center" width="70%" style="font-size: 15px; font-family: Georgia, serif; line-height: 2.2em;">
        <tr><td><b>Total Votes :</b></td><td><font color="blue"><b>{total_records}</b></font></td></tr>
        <tr><td><b>Duplicate Votes Found & Removed :</b></td><td><font color="red"><b>{duplicate_count}</b></font></td></tr>
        <tr><td><b>Remaining Duplicates :</b></td><td><font color="green"><b>0</b></font></td></tr>
        <tr><td><b>Total Clean Unique Votes :</b></td><td><font color="green"><b>{unique_records}</b></font></td></tr>
    </table>
    <br/>
    <font size="3" color="green"><b>✓ Duplicates removed successfully! Remaining duplicates: 0</b></font><br/><br/>
    <font size="2" color="black">Cleaned valid voter records saved to <b>DataVoter.xlsx</b> and <b>unique.xlsx</b>.</font><br/>
    <font size="2" color="black">Click <b>'Download Unique Data'</b> in the menu to download the clean Excel file.</font>
    </center>
    """
    context = {'data': output}
    return render(request, 'UserScreen.html', context)

def AddNewVoter(request):
    return render(request, 'AddNewVoter.html', {})

def AddNewVoterAction(request):
    if request.method == 'POST':
        name = str(request.POST.get('t1', '')).strip()
        father = str(request.POST.get('t2', '')).strip()
        age = str(request.POST.get('t3', '')).strip()
        gender = str(request.POST.get('t4', '')).strip()
        voter = str(request.POST.get('t5', '')).strip()
        aadhar = str(request.POST.get('t6', '')).strip()

        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
        father_col = 'Father_Husband' if 'Father_Husband' in dataset.columns else ('Father/Husband' if 'Father/Husband' in dataset.columns else 'Father_Husband')
        voter_col = 'VoterId' if 'VoterId' in dataset.columns else ('Voter ID' if 'Voter ID' in dataset.columns else 'VoterId')
        aadhar_col = 'Aadhar no' if 'Aadhar no' in dataset.columns else ('Aadhar' if 'Aadhar' in dataset.columns else 'Aadhar no')

        new_rec = {
            'Name': name,
            father_col: father,
            'Age': age,
            'Gender': gender,
            voter_col: voter,
            aadhar_col: aadhar
        }

        # Append EXACTLY ONCE to DataVoter.xlsx
        dataset = pd.concat([dataset, pd.DataFrame([new_rec])], ignore_index=True)
        try:
            dataset.to_excel(_project_path('DataVoter.xlsx'), index=False)
        except Exception:
            pass

        # Calculate duplicate count across the dataset
        _, duplicate_indices = _find_duplicates(dataset)
        dup_count = len(duplicate_indices)

        details_table = f"""
        <table border="1" align="center" style="margin:10px auto; border-collapse:collapse; font-size:14px; font-family:Georgia, serif; text-align:center;">
            <tr style="background:#f2f2f2;">
                <th style="padding:4px 8px;">Name</th>
                <th style="padding:4px 8px;">Father/Husband</th>
                <th style="padding:4px 8px;">Age</th>
                <th style="padding:4px 8px;">Gender</th>
                <th style="padding:4px 8px;">Voter ID</th>
                <th style="padding:4px 8px;">Aadhar No</th>
            </tr>
            <tr>
                <td style="padding:4px 8px;">{name}</td>
                <td style="padding:4px 8px;">{father}</td>
                <td style="padding:4px 8px;">{age}</td>
                <td style="padding:4px 8px;">{gender}</td>
                <td style="padding:4px 8px;"><b>{voter}</b></td>
                <td style="padding:4px 8px;"><b>{aadhar}</b></td>
            </tr>
        </table>
        """

        if dup_count > 0:
            msg = f"""
            <br/>
            <font size="" color="blue"><center>New record added to existing DataVoter.xlsx</center></font>
            {details_table}
            <font size="4" color="red"><center><b>Duplicate found : {dup_count}</b></center></font><br/>
            <font size="3" color="black"><center>Matching Voter ID ({voter}) or Aadhar ({aadhar}) already exists in records!</center></font><br/>
            <font size="2" color="black"><center>Click <b>'Remove Duplicate Data'</b> in the menu above to remove duplicates and return as 0.</center></font>
            """
        else:
            msg = f"""
            <br/>
            <font size="" color="blue"><center>New record added to existing DataVoter.xlsx</center></font>
            {details_table}
            <font size="3" color="green"><center><b>Duplicate found : 0 (Valid Unique Record)</b></center></font>
            """

        context = {'data': msg}
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
