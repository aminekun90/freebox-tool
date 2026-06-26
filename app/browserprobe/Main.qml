import QtQuick 2.5
import fbx.application 1.0

Application {
    id: app
    property string log: ""
    function p(s) { console.log(s); log = (log + s + "\n").split("\n").slice(-26).join("\n"); }

    Rectangle {
        anchors.fill: parent; color: "#101018"
        Text { anchors.fill: parent; anchors.margins: 20
            color: "#33ff66"; font.pixelSize: 18; font.family: "monospace"
            text: app.log; wrapMode: Text.WrapAnywhere }
    }

    Component.onCompleted: {
        var base = Qt.resolvedUrl("probe.html");
        p("Ouverture page de test dans le composant systeme :");
        p(base);
        p("→ choisis 'navigateur' sur la TV.");
        var r = Qt.openUrlExternally(base);
        p("openUrlExternally = " + r);
    }
}
