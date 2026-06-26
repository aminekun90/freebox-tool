import QtQuick 2.5
import fbx.application 1.0

Application {
    id: app
    property string log: ""
    function p(s) { console.log(s); log = (log + s + "\n").split("\n").slice(-28).join("\n"); }

    Rectangle {
        anchors.fill: parent; color: "#101018"
        Text {
            anchors.fill: parent; anchors.margins: 24
            color: "#33ff66"; font.pixelSize: 18; font.family: "monospace"
            text: app.log; wrapMode: Text.WrapAnywhere
        }
    }

    Component.onCompleted: {
        p("===== FBX-PROBE v3 (fbx.application) =====");
        try { p("Qt.platform.os=" + Qt.platform.os); } catch(e){ p("os ERR "+e); }
        try { p("app.name=" + Qt.application.name + " v=" + Qt.application.version); } catch(e){}

        // Introspection de l'objet Application (API fbx exposée ?)
        try {
            var keys = [];
            for (var k in app) keys.push(k);
            p("app props (" + keys.length + "):");
            p(keys.join(" "));
        } catch(e){ p("introspect ERR " + e); }

        // XHR relatif (fichier de notre app) — autorisé ?
        try {
            var x = new XMLHttpRequest();
            x.open("GET", "manifest.json", false); x.send(null);
            p("XHR rel manifest.json status=" + x.status + " len=" + (x.responseText||"").length);
        } catch(e){ p("XHR rel ERR " + e); }

        // XHR file:// app absolu (via resolvedUrl)
        try {
            var base = Qt.resolvedUrl("manifest.json");
            p("resolvedUrl=" + base);
            var y = new XMLHttpRequest();
            y.open("GET", base, false); y.send(null);
            p("XHR abs status=" + y.status + " len=" + (y.responseText||"").length);
        } catch(e){ p("XHR abs ERR " + e); }

        p("===== END v3 =====");
    }
}
