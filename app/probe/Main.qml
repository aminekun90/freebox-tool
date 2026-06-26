import QtQuick 2.5
import fbx.application 1.0

Application {
    id: app
    property string log: ""
    function p(s) { console.log(s); log = (log + s + "\n").split("\n").slice(-30).join("\n"); }

    Rectangle {
        anchors.fill: parent; color: "#101018"
        Text { anchors.fill: parent; anchors.margins: 20
            color: "#33ff66"; font.pixelSize: 17; font.family: "monospace"
            text: app.log; wrapMode: Text.WrapAnywhere }
    }

    Component.onCompleted: {
        p("===== FBX DEVICE INFO =====");
        try {
            var o = Qt.createQmlObject(
                'import QtQuick 2.5; import fbx.system 1.0; QtObject{' +
                ' property string model: Device.model;' +
                ' property string fw: Device.firmwareVersion;' +
                ' property int hdcp: Device.hdcpVersion;' +
                ' property int hdr: Device.hdrModes;' +
                ' property bool is4k: Device.is4k }', app, "dev");
            p("model=" + o.model);
            p("firmwareVersion=" + o.fw);
            p("hdcpVersion=" + o.hdcp);
            p("hdrModes=" + o.hdr + " is4k=" + o.is4k);
            o.destroy();
        } catch(e) { p("Device ERR " + e); }
        p("===== END =====");
    }
}
