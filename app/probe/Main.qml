import QtQuick 2.5
import fbx.application 1.0

Application {
    id: app
    property string log: ""
    function p(s) { console.log(s); log = (log + s + "\n").split("\n").slice(-30).join("\n"); }

    Rectangle {
        anchors.fill: parent; color: "#101018"
        Text { anchors.fill: parent; anchors.margins: 18
            color: "#33ff66"; font.pixelSize: 16; font.family: "monospace"
            text: app.log; wrapMode: Text.WrapAnywhere }
    }

    function test(label, url) {
        var x = new XMLHttpRequest();
        x.onreadystatechange = function() {
            if (x.readyState === XMLHttpRequest.DONE)
                p(label + " -> status=" + x.status + " len=" + (x.responseText||"").length);
        };
        try { x.open("GET", url); x.timeout = 3000; x.send(); }
        catch(e){ p(label + " EXC " + e); }
    }

    Component.onCompleted: {
        p("===== XHR POLICY TEST =====");
        // (a) notre serveur = origine de l'app
        test("[origin-ourserver]", Qt.resolvedUrl("manifest.json"));
        // (b) IP LAN du Player, nginx :80 connu ouvert
        test("[player-LAN :80]", "http://192.168.1.174/pub/devel");
        // (c) loopback :80
        test("[loopback :80]", "http://127.0.0.1/pub/devel");
        // (d) host public
        test("[public]", "http://example.com/");
    }
}
