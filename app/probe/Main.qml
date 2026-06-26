import QtQuick 2.5
import fbx.application 1.0

Application {
    id: app
    property string log: ""
    function p(s) { console.log(s); log = (log + s + "\n").split("\n").slice(-28).join("\n"); }

    // Hook framework : que nous envoie le système ?
    function handleUrl(url) { p("handleUrl() RECU: " + url); return true; }

    Rectangle {
        anchors.fill: parent; color: "#101018"
        Text { anchors.fill: parent; anchors.margins: 18
            color: "#33ff66"; font.pixelSize: 16; font.family: "monospace"
            text: app.log; wrapMode: Text.WrapAnywhere }
    }

    Component.onCompleted: {
        p("===== openUrlExternally PROBE =====");
        var base = Qt.resolvedUrl("manifest.json").replace("manifest.json", "");
        // Si un navigateur/handler système s'ouvre, notre serveur HTTP verra ces GET :
        var tests = [
            base + "OPENURL_HTTP",                 // http vers nous (observable)
            "file:///etc/passwd",
            "fbx://app/OPENURL_FBX",
            "fbxapp://OPENURL_SCHEME",
            "http://127.0.0.1/OPENURL_LOOPBACK"
        ];
        for (var i = 0; i < tests.length; i++) {
            try {
                var r = Qt.openUrlExternally(tests[i]);
                p("openUrlExternally(" + tests[i].substring(0,40) + ") = " + r);
            } catch(e) { p("ERR " + e); }
        }
        p("===== END (watch HTTP log for OPENURL_*) =====");
    }
}
