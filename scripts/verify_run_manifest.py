import subprocess
import sys
import os

def run_cmd(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        return output.decode('utf-8').strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(e.output.decode('utf-8'))
        sys.exit(1)

def main():
    base = "origin/master"
    head = "HEAD"
    for i, arg in enumerate(sys.argv):
        if arg == '--base':
            base = sys.argv[i+1]
        elif arg == '--head':
            head = sys.argv[i+1]
            
    changed_files = run_cmd(f"git diff --name-only {base}...{head}")
    changed_files = [f.strip() for f in changed_files if f.strip()]
    
    # 1. Check if ledger is updated
    ledger_file = "v92_MULTIPLE_COMPARISONS_LEDGER.md"
    if ledger_file not in changed_files:
        print(f"❌ FAIL: {ledger_file} was not updated in this PR.")
        sys.exit(1)
        
    print(f"✅ SUCCESS: {ledger_file} was updated.")
    
    # 2. Find research directories updated
    research_dirs = set()
    for f in changed_files:
        if f.startswith("research/") and "/" in f[9:]:
            # extract research/hyp_id/agent_name
            parts = f.split('/')
            if len(parts) >= 3:
                r_dir = "/".join(parts[:3])
                research_dirs.add(r_dir)
                
    if not research_dirs:
        print("❌ FAIL: No research output directory found in the PR diff.")
        sys.exit(1)
        
    # 3. Check for run_manifest.json and CSVs in the research dirs
    missing_manifests = []
    missing_csvs = []
    
    for r_dir in research_dirs:
        manifest_path = os.path.join(r_dir, "run_manifest.json")
        if not os.path.exists(manifest_path):
            missing_manifests.append(manifest_path)
            
        has_csv = False
        if os.path.exists(r_dir) and os.path.isdir(r_dir):
            for filename in os.listdir(r_dir):
                if filename.endswith(".csv"):
                    has_csv = True
                    break
        
        if not has_csv:
            missing_csvs.append(r_dir)
            
    if missing_manifests:
        print(f"❌ FAIL: Missing run_manifest.json in directories: {', '.join(missing_manifests)}")
        sys.exit(1)
        
    if missing_csvs:
        print(f"❌ FAIL: Missing CSV outputs in directories: {', '.join(missing_csvs)}")
        sys.exit(1)
        
    print("✅ SUCCESS: All required manifest files and CSVs are present.")
    sys.exit(0)

if __name__ == "__main__":
    main()
