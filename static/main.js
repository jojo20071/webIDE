



document.getElementById("runButton").onclick = run;

document.addEventListener("keypress", (e) => {
    if (e.ctrlKey && e.key == "Enter") run();
    
});


function run() {
    sendPost({
        'editor': document.getElementById("editor").value
    }, "/run");
}


function sendPost(data, dest) {
    var http = new XMLHttpRequest();

    http.open('POST', dest);
    http.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
    http.send(JSON.stringify(data));

}
