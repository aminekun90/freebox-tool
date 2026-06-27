import QtQuick 2.5
import fbx.application 1.0

Application {
    id: app
    property string log: ""
    function p(s) { console.log(s); log = (log + s + "\n").split("\n").slice(-30).join("\n"); }

    Rectangle {
        anchors.fill: parent; color: "#101018"
        Text { anchors.fill: parent; anchors.margins: 16
            color: "#33ff66"; font.pixelSize: 14; font.family: "monospace"
            text: app.log; wrapMode: Text.WrapAnywhere }
    }

    Component.onCompleted: {
        p("===== LED / ASSOC / SYSTEM PROBE =====");
        // toutes les clés de Application filtrées sur mots-clés intéressants
        var kw = ["led","light","power","standby","sleep","assoc","pair","provision",
                  "server","fbx","system","reboot","shutdown","state","gpio","brightness",
                  "register","activate","console","device","mode","status"];
        var all = []; for (var k in app) all.push(k);
        var hits = all.filter(function(k){
            var lk = k.toLowerCase();
            return kw.some(function(w){ return lk.indexOf(w) >= 0; });
        });
        p("Application props/méthodes pertinentes (" + hits.length + "):");
        p(hits.join(" "));

        // typeof de chaque hit (méthode vs propriété)
        for (var i = 0; i < hits.length; i++) {
            try { p("  " + hits[i] + " : " + (typeof app[hits[i]]) + " = " +
                    String(app[hits[i]]).slice(0,40)); } catch(e){}
        }
        p("===== END =====");
    }
}
