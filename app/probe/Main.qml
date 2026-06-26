import QtQuick 2.0

Item {
    width: 1280; height: 720

    function readFile(path) {
        var x = new XMLHttpRequest();
        try {
            x.open("GET", "file://" + path, false);
            x.send(null);
            var body = x.responseText || "";
            return "status=" + x.status + " len=" + body.length + "\n" + body.substring(0, 600);
        } catch (e) {
            return "EXCEPTION " + e;
        }
    }

    Component.onCompleted: {
        console.log("===== FBX-PROBE START =====");
        console.log("Qt runtime probe via QML/JS");
        var files = [
            "/proc/version",
            "/proc/self/status",
            "/proc/cmdline",
            "/proc/mounts",
            "/etc/passwd",
            "/proc/cpuinfo",
            "/proc/self/maps",
            "/etc/os-release",
            "/proc/self/cgroup"
        ];
        for (var i = 0; i < files.length; i++) {
            console.log("----- " + files[i] + " -----");
            console.log(readFile(files[i]));
        }
        console.log("===== FBX-PROBE END =====");
    }
}
