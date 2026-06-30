import os
import filecmp
import difflib

dir1 = r'c:\Users\HP\Desktop\CTRL_Arcadee\CTRL_Arcadee-main'
dir2 = r'c:\Users\HP\Desktop\CTRL_Arcadee'
ignore_list = ['CTRL_Arcadee-main', '.git', '.gemini', '__pycache__', 'compare_script.py', 'changelog.txt', 'logbook.txt']

def compare_dirs(d1, d2, path=''):
    dc = filecmp.dircmp(d1, d2, ignore=ignore_list)
    res = {'left_only': [os.path.join(path, f) for f in dc.left_only],
           'right_only': [os.path.join(path, f) for f in dc.right_only],
           'diff_files': [os.path.join(path, f) for f in dc.diff_files]}
    for sd in dc.common_dirs:
        if sd in ignore_list: continue
        sub_res = compare_dirs(os.path.join(d1, sd), os.path.join(d2, sd), os.path.join(path, sd))
        res['left_only'].extend(sub_res['left_only'])
        res['right_only'].extend(sub_res['right_only'])
        res['diff_files'].extend(sub_res['diff_files'])
    return res

results = compare_dirs(dir1, dir2)

with open(r'c:\Users\HP\Desktop\CTRL_Arcadee\logbook.txt', 'w', encoding='utf-8') as f:
    f.write("LOG BOOK OF CHANGES (Past 2 Weeks)\n")
    f.write("==================================\n\n")
    
    f.write("1. DELETED FILES (Existed in old version, removed in new version)\n")
    f.write("---------------------------------------------------------------\n")
    if not results['left_only']:
        f.write("None\n")
    for file in sorted(results['left_only']):
        f.write(f"- {file}\n")
    f.write("\n")
    
    f.write("2. NEW FILES (Added in new version)\n")
    f.write("-----------------------------------\n")
    if not results['right_only']:
        f.write("None\n")
    for file in sorted(results['right_only']):
        f.write(f"- {file}\n")
    f.write("\n")
    
    f.write("3. MODIFIED FILES (Changed between versions)\n")
    f.write("--------------------------------------------\n")
    if not results['diff_files']:
        f.write("None\n")
    for file in sorted(results['diff_files']):
        f.write(f"\n--- {file} ---\n")
        
        path1 = os.path.join(dir1, file)
        path2 = os.path.join(dir2, file)
        
        try:
            with open(path1, 'r', encoding='utf-8') as f1, open(path2, 'r', encoding='utf-8') as f2:
                lines1 = f1.readlines()
                lines2 = f2.readlines()
                
                diff = difflib.unified_diff(lines1, lines2, fromfile=f"OLD/{file}", tofile=f"NEW/{file}")
                f.writelines(diff)
        except Exception as e:
            f.write(f"Could not read diff for {file}: {str(e)}\n")
