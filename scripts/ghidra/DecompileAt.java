// Décompile la fonction contenant une adresse donnée (arg: hex, ex 0x3b904).
//@category FreeboxTool
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;

public class DecompileAt extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) { println("usage: DecompileAt <hexaddr>[,<hexaddr>...]"); return; }
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        for (String s : args[0].split(",")) {
            long off = Long.parseLong(s.replace("0x", ""), 16);
            Address a = currentProgram.getMinAddress().getNewAddress(off);
            Function func = fm.getFunctionContaining(a);
            if (func == null) { println("=== pas de fonction @ " + s + " ==="); continue; }
            println("\n===== " + func.getName() + " @ " + func.getEntryPoint() + " =====");
            DecompileResults res = ifc.decompileFunction(func, 60, monitor);
            if (res != null && res.decompileCompleted())
                println(res.getDecompiledFunction().getC());
            else println("(decompile echec)");
        }
        println("=== DONE ===");
    }
}
