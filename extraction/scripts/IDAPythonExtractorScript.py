# -*- coding: utf-8 -*-
"""
IDAPython Dynamic Disassembly Extraction Script
Utilizes the official IDAPython SDK to perform high-fidelity static recovery.
"""

import sys
import json
import time

try:
    import ida_pro
    import ida_funcs
    import ida_gdl
    import ida_segment
    import ida_name
    import idautils
    import idc
    IDA_AVAILABLE = True
except ImportError:
    IDA_AVAILABLE = False


def run_ida_native_extraction(output_path):
    """
    Main disassembly routine called when executed inside IDA (headless or GUI context).
    Recovers symbols, structural CFGs, call sites, and registers of active binaries.
    """
    if not IDA_AVAILABLE:
        print("[-] IDA SDK modules unavailable. Simulating analytical runtime database structure.")
        return False

    print("[+] IDAPython extractor successfully attached. Processing modules...")

    # Wait for auto-analysis to finish to ensure consistency
    idc.auto_wait()

    manifest = {
        "schema_version": "1.0.0",
        "provenance": {
            "tool_name": "IDA Pro / IDAPython Script",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
            "database_file": idc.get_idb_path(),
        },
        "data": {
            "functions": [],
            "symbols": [],
            "call_graph": {
                "nodes": [],
                "edges": []
            }
        }
    }

    # Extract all symbols
    for addr, name in idautils.Names():
        manifest["data"]["symbols"].append({
            "address": hex(addr),
            "name": name,
            "type": "function" if ida_funcs.get_func(addr) else "data",
            "visibility": "global" if ida_segment.getseg(addr) else "static"
        })

    # Record Function Blocks, instruction registers, and CFGs
    call_nodes = set()
    call_edges = []

    for func_ea in idautils.Functions():
        func = ida_funcs.get_func(func_ea)
        if not func:
            continue

        func_name = idc.get_func_name(func_ea)
        call_nodes.add(func_name)

        f_data = {
            "name": func_name,
            "entry_point": hex(func_ea),
            "size_bytes": func.size(),
            "calling_convention": idc.get_type(func_ea) or "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [],
                "edges": []
            }
        }

        # Handle local variables
        for frame_member in idautils.FrameMembers(func_ea):
            f_data["local_variables"].append(frame_member[1])

        # Generate intra-procedural CFG
        flowchart = ida_gdl.FlowChart(func)
        for block in flowchart:
            f_data["cfg"]["nodes"].append({
                "id": hex(block.start_ea),
                "size": block.end_ea - block.start_ea,
                "instructions_count": len(list(idautils.Heads(block.start_ea, block.end_ea)))
            })

            for successor in block.succs():
                f_data["cfg"]["edges"].append({
                    "source": hex(block.start_ea),
                    "target": hex(successor.start_ea),
                    "type": "unconditional" if len(list(block.succs())) == 1 else "conditional"
                })

        # Process function call-graph linkages
        for head in idautils.Heads(func.start_ea, func.end_ea):
            if idc.print_insn_mnem(head) == "call":
                op_val = idc.get_operand_value(head, 0)
                callee_name = idc.get_func_name(op_val) or hex(op_val)
                if callee_name:
                    call_edges.append({
                        "caller": func_name,
                        "callee": callee_name,
                        "site_address": hex(head)
                    })

        manifest["data"]["functions"].append(f_data)

    manifest["data"]["call_graph"]["nodes"] = list(call_nodes)
    manifest["data"]["call_graph"]["edges"] = call_edges

    # Save artifact out
    try:
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print("[+] Artifact compiled successfully to path: " + str(output_path))
        return True
    except IOError as e:
        print("[-] Critical error saving file: " + str(e))
        return False


if __name__ == "__main__":
    out_file = "ida_extraction_output.json"
    if len(sys.argv) > 1:
        out_file = sys.argv[1]
    run_ida_native_extraction(out_file)
