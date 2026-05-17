"""Debug: test build_schools step by step."""
import os, time, openpyxl

DESKTOP = 'c:/Users/22430/Desktop/高考河北数据'

# Test 1: find files
print("=== Finding files ===")
for fname in os.listdir(DESKTOP):
    if '专业录取数据-本科' in fname or '25年全国' in fname or '2023-河北-院校' in fname:
        if fname.endswith('.xlsx'):
            path = os.path.join(DESKTOP, fname)
            sz = os.path.getsize(path)
            print(f"  {fname} ({sz/1024:.0f}KB)")

# Test 2: open a 2024 undergrad file and count rows
print("\n=== Testing 2024 undergrad physics file ===")
fname = [f for f in os.listdir(DESKTOP) if '专业录取数据-本科' in f and '物理' in f][0]
path = os.path.join(DESKTOP, fname)
print(f"Opening: {fname}")
t0 = time.time()
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
print(f"  Opened in {time.time()-t0:.1f}s")
ws = wb[wb.sheetnames[0]]
print(f"  Sheet: {ws.max_row} rows x {ws.max_column} cols")

# Read headers from row 2
cols = {}
for col in range(1, ws.max_column + 1):
    h = str(ws.cell(row=2, column=col).value or '').strip()
    print(f"  Col{col}: '{h}'")
    if '学校' in h: cols['name'] = col

if 'name' not in cols:
    print("  ERROR: '学校' column not found in row 2!")
    # Check row 1
    for col in range(1, 5):
        print(f"  Row1 Col{col}: '{ws.cell(row=1, column=col).value}'")

# Test reading first 100 rows
t0 = time.time()
count = 0
for r in range(3, min(ws.max_row + 1, 103)):
    v = ws.cell(row=r, column=cols.get('name', 1)).value
    if v: count += 1
print(f"  Read {count} names from first 100 rows in {time.time()-t0:.1f}s")
wb.close()

# Test 3: the 2025 major file
print("\n=== Testing 2025 major file ===")
fname_2025 = [f for f in os.listdir(DESKTOP) if '25年全国' in f][0]
path = os.path.join(DESKTOP, fname_2025)
print(f"Opening: {fname_2025} ({os.path.getsize(path)/1024:.0f}KB)")
t0 = time.time()
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
print(f"  Opened in {time.time()-t0:.1f}s")
ws = wb[wb.sheetnames[0]]
print(f"  Sheet: {ws.max_row} rows x {ws.max_column} cols")
for col in range(1, min(ws.max_column + 1, 16)):
    h = str(ws.cell(row=1, column=col).value or '')[:50]
    print(f"  Col{col}: '{h}'")
wb.close()

print("\n=== All good! ===")
