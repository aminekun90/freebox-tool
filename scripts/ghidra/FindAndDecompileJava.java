// Trouve une string, ses xrefs, et décompile les fonctions qui la référencent.
// Arg: la string à chercher (défaut: is_unlocked).
//@category FreeboxTool
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import java.util.*;

public class FindAndDecompileJava extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String needle = args.length > 0 ? args[0] : "is_unlocked";
        println("=== FIND: " + needle + " ===");
        Memory mem = currentProgram.getMemory();
        byte[] nb = needle.getBytes("US-ASCII");
        List<Address> hits = new ArrayList<>();
        Address start = currentProgram.getMinAddress();
        while (start != null) {
            Address a = mem.findBytes(start, nb, null, true, monitor);
            if (a == null) break;
            hits.add(a);
            start = a.add(1);
            if (hits.size() > 30) break;
        }
        println("occurrences: " + hits);

        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        Set<String> seen = new HashSet<>();
        for (Address h : hits) {
            Reference[] refs = getReferencesTo(h);
            for (Reference r : refs) {
                Address frm = r.getFromAddress();
                Function func = fm.getFunctionContaining(frm);
                if (func == null) { println("ref @ " + frm + " (hors fonction)"); continue; }
                String key = func.getEntryPoint().toString();
                if (!seen.add(key)) continue;
                println("\n===== FONCTION " + func.getName() + " @ " + key + " (ref " + frm + ") =====");
                DecompileResults res = ifc.decompileFunction(func, 60, monitor);
                if (res != null && res.decompileCompleted())
                    println(res.getDecompiledFunction().getC());
                else
                    println("(decompile echec)");
            }
        }
        if (seen.isEmpty()) println("Aucune xref vers la string (ADR non resolu ?).");
        println("=== DONE ===");
    }
}
