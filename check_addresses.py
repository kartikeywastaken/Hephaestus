import os
import json
import re

ADDRESS_KEYS = {
    "entry_point", "address", "id", "source", "target", "caller", "callee", 
    "function_entry", "block_id", "instr_address", "base_id", "source_instrs"
}

HEX_PATTERN = re.compile(r'^[0-9a-fA-F]+$')

def scan_value(val, key, path):
    issues = []
    if isinstance(val, str):
        # Check for corrupted address format
        if "0x5f5e" in val:
            issues.append(f"Corrupted address 0x5f5e found at {path} ({key}: {val})")
        
        # Check if the key indicates it should be a normalized address
        is_address_key = any(k in key for k in ADDRESS_KEYS) if key else False
        if is_address_key:
            # If it consists only of hex chars and length >= 6 but no 0x prefix
            if HEX_PATTERN.match(val) and len(val) >= 6:
                issues.append(f"Bare long hex-like address found at {path} ({key}: {val})")
    elif isinstance(val, dict):
        for k, v in val.items():
            issues.extend(scan_value(v, k, f"{path}.{k}"))
    elif isinstance(val, list):
        for idx, item in enumerate(val):
            issues.extend(scan_value(item, key, f"{path}[{idx}]"))
    return issues

def main():
    artifacts_dir = "artifacts"
    all_issues = []
    
    if not os.path.exists(artifacts_dir):
        print(f"Error: {artifacts_dir} directory does not exist.")
        return
        
    for filename in os.listdir(artifacts_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(artifacts_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                issues = scan_value(data, None, filename)
                all_issues.extend(issues)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    if all_issues:
        print(f"Found {len(all_issues)} address normalization issues:")
        for issue in all_issues:
            print(f"  - {issue}")
    else:
        print("Success: Zero bare or corrupted address-like structured fields found across all artifacts!")

if __name__ == "__main__":
    main()
