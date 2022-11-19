

document.getElementById("runButton").onclick = () => {
    sendPost(JSON.stringify({
        editor: document.getElementById("editor").value
    }), "/run");
};


function sendPost(postData, dest) {
    var options = {
        hostname: '',
        path: dest,
        method: 'POST',
        headers: {
             'Content-Type': 'application/json',
             'Content-Length': postData.length
           }
      };

    var req = https.request(options, (res) => {
        console.log('statusCode:', res.statusCode);        
    });

    req.on('error', console.error);

    req.write(postData);
    req.end();
}
