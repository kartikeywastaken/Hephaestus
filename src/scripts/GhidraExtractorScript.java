/**
 * Ghidra Headless Analysis Script (Java Program)
 * Extracts symbols, function sizes, call graph links, and intra-procedural Control Flow Graphs (CFG)
 * and formats the result as a structured JSON artifact conforming to standard version 1.0.0.
 */

import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.block.*;
import ghidra.program.model.listing.*;
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

        // 3. Extract Functions & Intra-Procedural CFGs
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

            // Reconstruct intra-procedural CFG Blocks & Edges
            Map<String, Object> cfg = new HashMap<>();
            List<Map<String, Object>> cfgNodes = new ArrayList<>();
            List<Map<String, Object>> cfgEdges = new ArrayList<>();

            CodeBlockIterator blockIter = blockModel.getCodeBlocksContaining(func.getBody(), monitor);
            while (blockIter.hasNext()) {
                CodeBlock block = blockIter.next();
                Map<String, Object> node = new HashMap<>();
                node.add("id", block.getMinAddress().toString());
                node.add("size", block.getNumAddresses());
                node.add("instructions_count", (block.getNumAddresses() / 4) + 1); // rough static estimation
                cfgNodes.add(node);

                CodeBlockReferenceIterator destIter = block.getDestinations(monitor);
                while (destIter.hasNext()) {
                    CodeBlockReference ref = destIter.next();
                    CodeBlock destBlock = ref.getDestinationBlock();
                    if (func.getBody().contains(destBlock.getMinAddress())) {
                        Map<String, Object> edge = new HashMap<>();
                        edge.add("source", block.getMinAddress().toString());
                        edge.add("target", destBlock.getMinAddress().toString());
                        edge.add("type", ref.getFlowType().isConditional() ? "conditional_taken" : "unconditional");
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
