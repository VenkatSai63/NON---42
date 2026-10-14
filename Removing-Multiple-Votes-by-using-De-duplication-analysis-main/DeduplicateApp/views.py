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
        voter_id = str(request.POST.get('t1', '')).strip().upper()
        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
        added_voters = request.session.get('added_voters', [])
        if added_voters:
            dataset = pd.concat([dataset, pd.DataFrame(added_voters)], ignore_index=True)

        voter_col = 'VoterId' if 'VoterId' in dataset.columns else ('Voter ID' if 'Voter ID' in dataset.columns else '')
        father_col = 'Father_Husband' if 'Father_Husband' in dataset.columns else ('Father/Husband' if 'Father/Husband' in dataset.columns else '')
        aadhar_col = 'Aadhar no' if 'Aadhar no' in dataset.columns else ('Aadhar' if 'Aadhar' in dataset.columns else '')

        voter_series = dataset[voter_col].fillna('').astype(str).str.strip().str.upper()
        search_data = dataset.loc[voter_series == voter_id]
        output = f"<font color='red'><b>Voter ID '{voter_id}' doesn't exist in records.</b></font>"
        if len(search_data) > 0:
            output = '<table border=1 align=center width=100% style="border-collapse:collapse; font-family:Arial, sans-serif; font-size:14px;">'
            output += '<tr style="background:#2c3e50; color:white; padding:8px;"><th>Name</th><th>Father/Husband</th><th>Age</th><th>Gender</th><th>Voter ID</th><th>Aadhar No</th></tr>'
            for idx, row in search_data.iterrows():
                output += '<tr>'
                output += f'<td style="padding:6px; border:1px solid #ccc;">{row["Name"]}</td>'
                output += f'<td style="padding:6px; border:1px solid #ccc;">{row[father_col]}</td>'
                output += f'<td style="padding:6px; border:1px solid #ccc; text-align:center;">{row["Age"]}</td>'
                output += f'<td style="padding:6px; border:1px solid #ccc; text-align:center;">{row["Gender"]}</td>'
                output += f'<td style="padding:6px; border:1px solid #ccc; font-weight:bold; color:#b30000; text-align:center;">{row[voter_col]}</td>'
                output += f'<td style="padding:6px; border:1px solid #ccc; font-weight:bold; text-align:center;">{row[aadhar_col]}</td></tr>'
            output += '</table>'
        context = {'data': output}
        return render(request, 'ViewResult.html', context)
    return render(request, 'ViewVoters.html', {})
            
def Download(request):
    name = "unique.xlsx"
    file_path = _project_path(name)
    if not os.path.exists(file_path):
        dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
        voter_col = 'VoterId' if 'VoterId' in dataset.columns else ('Voter ID' if 'Voter ID' in dataset.columns else '')
        dataset.drop_duplicates(subset=[voter_col]).to_excel(file_path, index=False)
    with open(file_path, mode="rb") as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response 

def RemoveDuplicate(request):
    global unique_df
    dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")

    # Include newly added voters from session for serverless persistence
    added_voters = request.session.get('added_voters', [])
    if added_voters:
        added_df = pd.DataFrame(added_voters)
        dataset = pd.concat([dataset, added_df], ignore_index=True)

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

    seen_voters = {}
    seen_aadhars = {}
    seen_persons = {}

    indices_to_keep = []
    duplicate_records_list = []

    for idx in range(total_records):
        v = voter_norm.iloc[idx]
        a = aadhar_norm.iloc[idx]
        n = name_norm.iloc[idx]
        f = father_norm.iloc[idx]
        p = f"{n}___{f}" if (n and f) else ''

        is_dup = False
        reasons = []

        if v and v in seen_voters:
            is_dup = True
            reasons.append(f"Matching Voter ID: {v} (Duplicate of Record #{seen_voters[v]+1})")
        if a and a in seen_aadhars:
            is_dup = True
            reasons.append(f"Matching Aadhar No: {dataset.iloc[idx][aadhar_col]} (Duplicate of Record #{seen_aadhars[a]+1})")
        if not is_dup and p and p in seen_persons:
            is_dup = True
            reasons.append(f"Matching Person Name & Father: {n} (Duplicate of Record #{seen_persons[p]+1})")

        if is_dup:
            rec = {
                'Name': dataset.iloc[idx].get('Name', ''),
                'Father': dataset.iloc[idx].get(father_col, ''),
                'Age': dataset.iloc[idx].get('Age', ''),
                'Gender': dataset.iloc[idx].get('Gender', ''),
                'VoterId': dataset.iloc[idx].get(voter_col, ''),
                'Aadhar': dataset.iloc[idx].get(aadhar_col, ''),
                'Reason': ', '.join(reasons)
            }
            duplicate_records_list.append(rec)
        else:
            indices_to_keep.append(dataset.index[idx])
            if v:
                seen_voters[v] = idx
            if a:
                seen_aadhars[a] = idx
            if p:
                seen_persons[p] = idx

    unique_df = dataset.loc[indices_to_keep].copy()
    unique_records = unique_df.shape[0]
    duplicate_count = len(duplicate_records_list)

    # Save to BOTH DataVoter.xlsx and unique.xlsx in writable storage
    unique_df.to_excel(_project_path("DataVoter.xlsx"), index=False)
    unique_df.to_excel(_project_path("unique.xlsx"), index=False)

    # Reset session added_voters since they've now been processed
    request.session['added_voters'] = []
    request.session.modified = True

    # Build Duplicate Votes Table HTML
    table_rows = ""
    display_dups = duplicate_records_list[:60]
    for i, d in enumerate(display_dups, 1):
        bg = "#ffffff" if i % 2 == 0 else "#f9fafb"
        table_rows += f"""<tr style="background:{bg};">
            <td style="padding:6px; border:1px solid #d1d5db; text-align:center;">{i}</td>
            <td style="padding:6px; border:1px solid #d1d5db;">{d['Name']}</td>
            <td style="padding:6px; border:1px solid #d1d5db;">{d['Father']}</td>
            <td style="padding:6px; border:1px solid #d1d5db; text-align:center;">{d['Age']}</td>
            <td style="padding:6px; border:1px solid #d1d5db; text-align:center;">{d['Gender']}</td>
            <td style="padding:6px; border:1px solid #d1d5db; font-weight:bold; color:#b91c1c; text-align:center;">{d['VoterId']}</td>
            <td style="padding:6px; border:1px solid #d1d5db; font-weight:bold; color:#b91c1c; text-align:center;">{d['Aadhar']}</td>
            <td style="padding:6px; border:1px solid #d1d5db; color:#991b1b; font-size:12px;">{d['Reason']}</td>
        </tr>"""

    dup_section_html = ""
    if duplicate_count > 0:
        more_note = f"<p style='color:#6b7280; font-size:12px; margin-top:6px;'>Showing first {len(display_dups)} of {duplicate_count} duplicate records removed.</p>" if duplicate_count > len(display_dups) else ""
        dup_section_html = f"""
        <div style="margin-top:20px; text-align:left;">
            <h3 style="color:#b91c1c; margin-bottom:10px; font-size:16px;">❌ Removed Duplicate Voter Records ({duplicate_count} duplicates found):</h3>
            <div style="max-height: 420px; overflow-y: auto; border: 1px solid #d1d5db; border-radius: 6px;">
            <table style="width:100%; border-collapse:collapse; font-size:13px; font-family:Arial, sans-serif;">
                <thead>
                    <tr style="background:#b91c1c; color:white; position:sticky; top:0;">
                        <th style="padding:8px; border:1px solid #991b1b;">#</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Voter Name</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Father/Husband</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Age</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Gender</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Duplicate Voter ID</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Duplicate Aadhar No</th>
                        <th style="padding:8px; border:1px solid #991b1b;">Reason for Removal</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            </div>
            {more_note}
        </div>
        """
    else:
        dup_section_html = "<div style='margin:20px 0; padding:15px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; color:#1d4ed8; font-weight:bold;'>✓ All voters in the current dataset are unique! No duplicates detected.</div>"

    output = f"""
    <div style="font-family: Arial, sans-serif; max-width: 950px; margin: 0 auto; padding: 20px; background:#ffffff; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.08);">
        <h2 style="color:#1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-top:0;">De-Duplication Analysis Result</h2>
        <div style="display:flex; justify-content:space-around; background:#f1f5f9; padding:16px; border-radius:8px; margin:16px 0; font-size:14px;">
            <div><b>Total Records Before:</b> <span style="color:#2563eb; font-size:18px; font-weight:bold;">{total_records}</span></div>
            <div><b>Duplicate Votes Removed:</b> <span style="color:#dc2626; font-size:18px; font-weight:bold;">{duplicate_count}</span></div>
            <div><b>Clean Unique Records:</b> <span style="color:#16a34a; font-size:18px; font-weight:bold;">{unique_records}</span></div>
        </div>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:10px; color:#166534; font-weight:bold; font-size:14px;">
            ✓ Cleaned dataset saved successfully to DataVoter.xlsx & unique.xlsx!
        </div>
        {dup_section_html}
        <div style="margin-top:20px;">
            <a href="/Download" style="display:inline-block; padding:10px 22px; background:#16a34a; color:#ffffff; text-decoration:none; border-radius:5px; font-weight:bold; font-size:14px; margin-right:10px;">📥 Download Cleaned Unique Data (.xlsx)</a>
            <a href="/ResetDataset" style="display:inline-block; padding:10px 18px; background:#64748b; color:#ffffff; text-decoration:none; border-radius:5px; font-weight:bold; font-size:14px;">🔄 Reset Original Dataset</a>
        </div>
    </div>
    """
    context = {'data': output}
    return render(request, 'UserScreen.html', context)

def ResetDataset(request):
    orig = os.path.join(settings.BASE_DIR, 'DataVoter.xlsx')
    target = _project_path('DataVoter.xlsx')
    if os.environ.get('VERCEL'):
        import shutil
        if os.path.exists(orig):
            shutil.copy2(orig, target)
        unique_file = _project_path('unique.xlsx')
        if os.path.exists(unique_file):
            try:
                os.remove(unique_file)
            except Exception:
                pass
    request.session['added_voters'] = []
    request.session.modified = True
    context = {'data': "<div style='font-family:Arial; padding:15px; background:#eff6ff; border:1px solid #93c5fd; border-radius:6px; color:#1e40af; font-size:15px;'><b>🔄 Dataset has been successfully reset to original state with duplicate records!</b><br/><br/>Click <b>'Remove Duplicate Data'</b> in the menu above to run the de-duplication analysis.</div>"}
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

        new_rec = {
            'Name': name,
            'Father_Husband': father,
            'Age': age,
            'Gender': gender,
            'VoterId': voter,
            'Aadhar no': aadhar
        }

        # Persist in signed cookie session so it survives across serverless requests
        added_voters = request.session.get('added_voters', [])
        added_voters.append(new_rec)
        request.session['added_voters'] = added_voters
        request.session.modified = True

        # Also append to DataVoter.xlsx in writable storage
        try:
            dataset = pd.read_excel(_project_path('DataVoter.xlsx'), engine="openpyxl")
            dataset = pd.concat([dataset, pd.DataFrame([new_rec])], ignore_index=True)
            dataset.to_excel(_project_path('DataVoter.xlsx'), index=False)
        except Exception:
            pass

        context = {
            'data': f"""<div style='font-family:Arial; padding:15px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; color:#166534;'>
                <b style='font-size:16px;'>✓ New Voter Record Added Successfully!</b><br/><br/>
                <b>Name:</b> {name} | <b>Father/Husband:</b> {father}<br/>
                <b>Voter ID:</b> <span style='color:#dc2626; font-weight:bold;'>{voter}</span> | <b>Aadhar No:</b> <span style='color:#dc2626; font-weight:bold;'>{aadhar}</span><br/><br/>
                👉 Now click <a href='/RemoveDuplicate' style='color:#2563eb; font-weight:bold;'>'Remove Duplicate Data'</a> to see it detected and removed if it matches an existing voter!
            </div>"""
        }
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
        
        
