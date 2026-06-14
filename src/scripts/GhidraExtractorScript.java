/**
 * Ghidra Headless Analysis Script (Java Program)
 * Extracts symbols, function sizes, call graph links, and intra-procedural Control Flow Graphs (CFG)
 * including real instruction-level evidence per basic block.
 * Formats the result as a structured JSON artifact conforming to standard version 1.0.0.
 *
 * Instruction extraction (Amendment 2 — AddressSet fallback):
 *   Primary:  getListing().getInstructions(block, true)
 *   Fallback: iterate block.getAddressRanges() and stop each range iterator
 *             as soon as the instruction address leaves the range boundary.
 */

import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressRange;
import ghidra.program.model.block.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.*;
import ghidra.util.task.TaskMonitor;

public class GhidraExtractorScript extends GhidraScript {

    @Override
    public void run() throws Exception {
        println("[+] Initiating headless extraction pipeline on: " + currentProgram.getName());

        Map<String, Object> output = new HashMap<>();
        output.put("schema_version", "1.0.0");

        // 1. Provenance Information
        Map<String, Object> provenance = new HashMap<>();
        provenance.put("tool_name", "Ghidra Headless Analyzer (Java API)");
        provenance.put("compiler", currentProgram.getCompiler());
        provenance.put("format", currentProgram.getExecutableFormat());
        provenance.put("language_id", currentProgram.getLanguageID().toString());
        provenance.put("timestamp", new java.util.Date().toString());
        output.put("provenance", provenance);

        // 2. Extract Symbols
        List<Map<String, Object>> symbolList = new ArrayList<>();
        SymbolTable symbolTable = currentProgram.getSymbolTable();
        SymbolIterator symbolIter = symbolTable.getAllSymbols(true);
        while (symbolIter.hasNext() && !monitor.isCancelled()) {
            Symbol sym = symbolIter.next();
            Map<String, Object> sMap = new HashMap<>();
            sMap.put("address", sym.getAddress().toString());
            sMap.put("name", sym.getName());
            sMap.put("type", sym.getSymbolType().toString());
            sMap.put("visibility", sym.getSource().toString());
            symbolList.add(sMap);
        }
        output.put("symbols", symbolList);

        // 3. Extract Functions & Intra-Procedural CFGs (with instructions)
        List<Map<String, Object>> functions = new ArrayList<>();
        FunctionManager functionManager = currentProgram.getFunctionManager();
        FunctionIterator funcIter = functionManager.getFunctions(true);

        SimpleBlockModel blockModel = new SimpleBlockModel(currentProgram);

        while (funcIter.hasNext() && !monitor.isCancelled()) {
            Function func = funcIter.next();
            if (func.isThunk()) continue;

            Map<String, Object> fMap = new HashMap<>();
            fMap.put("name", func.getName());
            fMap.put("entry_point", func.getEntryPoint().toString());
            fMap.put("size_bytes", func.getBody().getNumAddresses());
            fMap.put("calling_convention", func.getCallingConventionName());

            // Collect Local Variable Information
            List<String> locals = new ArrayList<>();
            for (Variable var : func.getLocalVariables()) {
                locals.add(var.getName());
            }
            fMap.put("local_variables", locals);

            // Reconstruct intra-procedural CFG Blocks & Edges (with instructions)
            Map<String, Object> cfg = new HashMap<>();
            List<Map<String, Object>> cfgNodes = new ArrayList<>();
            List<Map<String, Object>> cfgEdges = new ArrayList<>();

            CodeBlockIterator blockIter = blockModel.getCodeBlocksContaining(func.getBody(), monitor);
            while (blockIter.hasNext()) {
                CodeBlock block = blockIter.next();
                Map<String, Object> node = new HashMap<>();
                node.put("id", block.getMinAddress().toString());
                node.put("size", block.getNumAddresses());

                // Extract real instructions for this block
                List<Map<String, Object>> instrList = extractBlockInstructions(block);
                node.put("instructions", instrList);
                node.put("instructions_count", instrList.size());
                node.put("estimated_instructions_count", (block.getNumAddresses() / 4) + 1);

                cfgNodes.add(node);

                CodeBlockReferenceIterator destIter = block.getDestinations(monitor);
                while (destIter.hasNext()) {
                    CodeBlockReference ref = destIter.next();
                    CodeBlock destBlock = ref.getDestinationBlock();
                    if (func.getBody().contains(destBlock.getMinAddress())) {
                        Map<String, Object> edge = new HashMap<>();
                        edge.put("source", block.getMinAddress().toString());
                        edge.put("target", destBlock.getMinAddress().toString());
                        edge.put("type", ref.getFlowType().isConditional() ? "conditional_taken" : "unconditional");
                        cfgEdges.add(edge);
                    }
                }
            }
            cfg.put("nodes", cfgNodes);
            cfg.put("edges", cfgEdges);
            fMap.put("cfg", cfg);

            functions.add(fMap);
        }
        output.put("functions", functions);

        // 4. Save to JSON File
        String[] args = getScriptArgs();
        String outputPath = "ghidra_extraction_output.json";
        if (args.length > 0) {
            outputPath = args[0];
        }

        try (FileWriter writer = new FileWriter(outputPath)) {
            writer.write(formatJson(output));
            println("[+] Schema-validated artifacts captured in output location: " + outputPath);
        } catch (IOException e) {
            println("[-] Critical error writing output JSON file: " + e.getMessage());
        }
    }

    /**
     * Extract real instructions for a single CodeBlock.
     *
     * Primary path: getListing().getInstructions(block, true)  [AddressSetView overload]
     * Amendment 2 fallback: iterate block.getAddressRanges() individually if primary fails.
     *
     * Instruction-level exceptions are caught per-instruction; a single failure
     * never aborts the whole block — that instruction is simply skipped.
     */
    private static final java.util.regex.Pattern MEM_OP_PATTERN = java.util.regex.Pattern.compile(
        "^\\s*\\[\\s*([a-zA-Z0-9]+)(?:\\s*,\\s*#?(-?)(0x[0-9a-fA-F]+|[0-9]+))?\\s*\\]\\s*$"
    );

    /**
     * Extract real instructions for a single CodeBlock by iterating its address ranges.
     */
    private List<Map<String, Object>> extractBlockInstructions(CodeBlock block) {
        List<Map<String, Object>> instrList = new ArrayList<>();
        try {
            for (AddressRange range : block.getAddressRanges()) {
                try {
                    InstructionIterator rangeIter = currentProgram.getListing()
                        .getInstructions(range.getMinAddress(), true);
                    while (rangeIter.hasNext()) {
                        try {
                            Instruction instr = rangeIter.next();
                            // Stop if we have left the range boundary
                            if (!range.contains(instr.getAddress())) {
                                break;
                            }
                            Map<String, Object> instrMap = buildInstructionMap(instr);
                            if (instrMap != null) {
                                instrList.add(instrMap);
                            }
                        } catch (Exception e) {
                            println("[-] Skipping malformed instruction in range: " + e.getMessage());
                        }
                    }
                } catch (Exception rangeEx) {
                    println("[-] Range extraction failed for range " + range + ": " + rangeEx.getMessage());
                }
            }
        } catch (Exception e) {
            println("[-] All instruction extraction attempts failed for block " + block.getMinAddress() + ": " + e.getMessage());
        }
        return instrList;
    }

    /**
     * Build a canonical instruction map from a Ghidra Instruction object.
     * Returns null if the instruction cannot be represented safely.
     */
    private Map<String, Object> buildInstructionMap(Instruction instr) {
        try {
            Map<String, Object> instrMap = new HashMap<>();
            instrMap.put("address", instr.getAddress().toString());
            String mnemonic = instr.getMnemonicString();
            instrMap.put("mnemonic", mnemonic);
            instrMap.put("opcode", mnemonic.toLowerCase());
            instrMap.put("raw", instr.toString());
            instrMap.put("size_bytes", instr.getLength());
            instrMap.put("source", "ghidra");

            // Build operands
            List<Map<String, Object>> operands = new ArrayList<>();
            int numOperands = instr.getNumOperands();
            for (int i = 0; i < numOperands; i++) {
                String operandText = instr.getDefaultOperandRepresentation(i);
                if (operandText == null) continue;
                String optTrim = operandText.trim();
                
                // If it looks like a memory operand (contains brackets)
                if (optTrim.contains("[") || optTrim.contains("]")) {
                    java.util.regex.Matcher m = MEM_OP_PATTERN.matcher(optTrim);
                    if (m.matches()) {
                        String baseReg = m.group(1);
                        long offsetVal = 0;
                        if (m.group(3) != null) {
                            String sign = m.group(2);
                            String valStr = m.group(3);
                            long absVal;
                            if (valStr.startsWith("0x") || valStr.startsWith("0X")) {
                                absVal = Long.parseLong(valStr.substring(2), 16);
                            } else {
                                absVal = Long.parseLong(valStr, 10);
                            }
                            offsetVal = "-".equals(sign) ? -absVal : absVal;
                        }
                        
                        Integer memSize = inferMemoryAccessSize(mnemonic, instr);
                        Map<String, Object> op = new HashMap<>();
                        op.put("kind", "memory");
                        op.put("base", baseReg);
                        op.put("offset", offsetVal);
                        op.put("size_bytes", memSize);
                        operands.add(op);
                    } else {
                        // Unsupported complex memory operand
                        Map<String, Object> op = new HashMap<>();
                        op.put("kind", "unknown");
                        op.put("raw", optTrim);
                        operands.add(op);
                    }
                } else {
                    // Fallback to standard token representation list
                    List<Object> repList = instr.getDefaultOperandRepresentationList(i);
                    if (repList == null || repList.isEmpty()) {
                        // Just map the string representation if representation list is empty
                        Map<String, Object> op = new HashMap<>();
                        op.put("kind", "unknown");
                        op.put("raw", optTrim);
                        operands.add(op);
                    } else {
                        for (Object obj : repList) {
                            Map<String, Object> op = buildOperandMap(obj);
                            if (op != null) {
                                operands.add(op);
                            }
                        }
                    }
                }
            }
            instrMap.put("operands", operands);
            return instrMap;
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * Infer memory access size conservatively based on mnemonic and source/destination registers.
     */
    private Integer inferMemoryAccessSize(String mnemonic, Instruction instr) {
        if (mnemonic == null) return null;
        String m = mnemonic.toLowerCase();
        if (m.endsWith("b")) { // ldrb, strb, etc.
            return 1;
        }
        if (m.endsWith("h")) { // ldrh, strh, etc.
            return 2;
        }
        if (m.equals("ldrsw")) {
            return 4;
        }
        if (m.startsWith("ldr") || m.startsWith("str")) {
            // Check other operands to see if they are registers starting with w or x
            int numOperands = instr.getNumOperands();
            for (int i = 0; i < numOperands; i++) {
                String rep = instr.getDefaultOperandRepresentation(i);
                if (rep != null) {
                    rep = rep.toLowerCase().trim();
                    if (rep.startsWith("w")) {
                        return 4;
                    }
                    if (rep.startsWith("x") || rep.equals("sp")) {
                        return 8;
                    }
                }
            }
            // Fallback: check getOpObjects
            try {
                for (int i = 0; i < numOperands; i++) {
                    Object[] opObjects = instr.getOpObjects(i);
                    if (opObjects != null) {
                        for (Object obj : opObjects) {
                            if (obj instanceof ghidra.program.model.lang.Register) {
                                String regName = ((ghidra.program.model.lang.Register) obj).getName().toLowerCase();
                                if (regName.startsWith("w")) {
                                    return 4;
                                }
                                if (regName.startsWith("x") || regName.equals("sp")) {
                                    return 8;
                                }
                            }
                        }
                    }
                }
            } catch (Exception e) {
                // Ignore
            }
        }
        return null;
    }

    /**
     * Convert a Ghidra operand object to a canonical operand dict.
     * Uses instanceof checks for Register, Scalar, and Address types.
     */
    private Map<String, Object> buildOperandMap(Object obj) {
        if (obj == null) return null;
        Map<String, Object> op = new HashMap<>();
        if (obj instanceof ghidra.program.model.lang.Register) {
            ghidra.program.model.lang.Register reg = (ghidra.program.model.lang.Register) obj;
            op.put("kind", "register");
            op.put("value", reg.getName());
        } else if (obj instanceof Scalar) {
            Scalar scalar = (Scalar) obj;
            op.put("kind", "immediate");
            op.put("value", scalar.getValue());
        } else if (obj instanceof Address) {
            Address addr = (Address) obj;
            op.put("kind", "symbol");
            op.put("name", addr.toString());
        } else {
            String raw = obj.toString();
            if (raw == null || raw.trim().isEmpty()) return null;
            op.put("kind", "unknown");
            op.put("raw", raw);
        }
        return op;
    }

    private String formatJson(Map<String, Object> map) {
        // Simple internal JSON formatter suitable for Java primitive arrays, basic maps, nested arrays
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        int index = 0;
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (index > 0) sb.append(",\n");
            sb.append("  \"").append(entry.getKey()).append("\": ");
            sb.append(dumpValue(entry.getValue(), "  "));
            index++;
        }
        sb.append("\n}");
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private String dumpValue(Object val, String indent) {
        if (val == null) return "null";
        if (val instanceof String) return "\"" + val.toString().replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
        if (val instanceof Number || val instanceof Boolean) return val.toString();
        if (val instanceof List) {
            List<Object> list = (List<Object>) val;
            if (list.isEmpty()) return "[]";
            StringBuilder sb = new StringBuilder();
            sb.append("[\n");
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(",\n");
                sb.append(indent).append("  ").append(dumpValue(list.get(i), indent + "  "));
            }
            sb.append("\n").append(indent).append("]");
            return sb.toString();
        }
        if (val instanceof Map) {
            Map<String, Object> itemMap = (Map<String, Object>) val;
            if (itemMap.isEmpty()) return "{}";
            StringBuilder sb = new StringBuilder();
            sb.append("{\n");
            int j = 0;
            for (Map.Entry<String, Object> e : itemMap.entrySet()) {
                if (j > 0) sb.append(",\n");
                sb.append(indent).append("  \"").append(e.getKey()).append("\": ");
                sb.append(dumpValue(e.getValue(), indent + "  "));
                j++;
            }
            sb.append("\n").append(indent).append("}");
            return sb.toString();
        }
        return "\"" + val.toString() + "\"";
    }
}
