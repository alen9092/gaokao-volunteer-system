"""Quick test: find and inspect source files."""
import os

DESKTOP = 'c:/Users/22430/Desktop/高考河北数据'
D_DRIVE = 'd:/高考数据'

print("=== Desktop files ===")
for f in sorted(os.listdir(DESKTOP)):
    if f.endswith('.xlsx'):
        print(f"  {f}")

print("\n=== D: drive files ===")
for f in sorted(os.listdir(D_DRIVE)):
    if f.endswith('.xlsx'):
        print(f"  {f}")

# Test: find 2023 school file
print("\n=== Testing file matching ===")
matches_2023_school = [f for f in os.listdir(DESKTOP) if '2023-' in f and '院校' in f and f.endswith('.xlsx')]
print(f"2023 school file: {matches_2023_school}")

matches_2023_major = [f for f in os.listdir(DESKTOP) if '2023' in f and '专业' in f and f.endswith('.xlsx')]
print(f"2023 major file: {matches_2023_major}")

matches_2024_ug = [f for f in os.listdir(DESKTOP) if '专业录取数据-本科' in f]
print(f"2024 undergrad: {matches_2024_ug}")

matches_2024_voc = [f for f in os.listdir(DESKTOP) if '专业录取数据-专科' in f]
print(f"2024 vocational: {matches_2024_voc}")

matches_2025 = [f for f in os.listdir(D_DRIVE) if '2025' in f and ('物理' in f or '历史' in f)]
print(f"2025 vocational: {matches_2025}")
